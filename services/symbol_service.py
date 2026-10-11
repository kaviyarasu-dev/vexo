"""Symbol Service, Universe Management, and Trading Calendar.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md and plan/03_SYMBOL_MASTER_AND_UNIVERSE_MANAGER.md.
"""

from datetime import date, datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import duckdb
import requests

from core.interfaces import ISymbolRepository, SymbolEntity
from db.connection import DuckDBConnectionManager, get_db
from db.repositories.duckdb_symbol_repo import DuckDBSymbolRepo

logger = logging.getLogger(__name__)

HOLIDAY_UPSTOX_URL = "https://api.upstox.com/v2/market/holidays"
HOLIDAY_NSE_URL = "https://www.nseindia.com/api/holiday-master?type=trading"
HOLIDAYS_CACHE_FILE = Path("data/holidays_cache.json")


class SymbolService(ISymbolRepository):
    """High-level Symbol Master, Universe Classifier, and Market Calendar Service.
    
    Implements ISymbolRepository contract via composition with DuckDBSymbolRepo.
    Provides mathematically exact Universe Tier Arithmetic:
      - Tier 1: Nifty 50 (50) + Nifty Next 50 (50) = 100 stocks
      - Tier 2: Nifty Midcap 150 = 150 stocks
      - Tier 3: Nifty Smallcap 250 = 250 stocks
      - Total Tiers 1-3: Exactly 500 stocks (Exact Nifty 500)
      - Tier 4: Remaining NSE Equities
    """

    def __init__(self, db: Optional[DuckDBConnectionManager] = None) -> None:
        self.db = db or get_db()
        self.repo = DuckDBSymbolRepo(self.db)

    # -------------------------------------------------------------------------
    # ISymbolRepository Contract Implementation
    # -------------------------------------------------------------------------

    def upsert_symbols(self, symbols: List[SymbolEntity]) -> int:
        """Upsert master instrument definitions into symbols table."""
        return self.repo.upsert_symbols(symbols)

    def search_symbols(
        self, query: str, category: Optional[str] = None, limit: int = 20
    ) -> List[SymbolEntity]:
        """Prefix search by ticker or name with sub-5ms latency."""
        return self.repo.search_symbols(query, category=category, limit=limit)

    def get_by_symbol(self, symbol: str) -> Optional[SymbolEntity]:
        """Retrieves single symbol entity."""
        return self.repo.get_by_symbol(symbol)

    def list_active_symbols(self, tier: Optional[int] = None) -> List[SymbolEntity]:
        """Returns active symbols filtered optionally by tier (1 to 4)."""
        return self.repo.list_active_symbols(tier=tier)

    # -------------------------------------------------------------------------
    # Universe Classification & Tier Arithmetic
    # -------------------------------------------------------------------------

    def classify_and_apply_tiers(
        self,
        symbols: List[SymbolEntity],
        constituents: Dict[str, List[Dict[str, str]]],
    ) -> List[SymbolEntity]:
        """Classifies parsed symbols into Tiers 1-4 with exact arithmetic.
        
        Rules:
        - Tier 1 = Nifty 50 (50) + Nifty Next 50 (50) = 100 stocks
        - Tier 2 = Nifty Midcap 150 = 150 stocks
        - Tier 3 = Nifty Smallcap 250 = 250 stocks
        - Total Tiers 1-3 = 500 stocks
        - Tier 4 = Remaining active equities
        """
        # Map raw symbols by ticker and ISIN for fast index matching
        ticker_map: Dict[str, SymbolEntity] = {}
        isin_map: Dict[str, SymbolEntity] = {}
        canonical_map: Dict[str, SymbolEntity] = {}

        for s in symbols:
            ticker = s.symbol.split(":")[-1].split("-")[0].upper()
            ticker_map[ticker] = s
            canonical_map[s.symbol.upper()] = s
            if s.isin:
                isin_map[s.isin.upper()] = s

        allocated_symbols: Set[str] = set()

        def _allocate_index(
            cat_name: str, target_count: int, target_tier: int, start_rank: int
        ) -> List[SymbolEntity]:
            items = constituents.get(cat_name, [])
            matched: List[SymbolEntity] = []

            for item in items:
                sym_code = item.get("symbol", "").strip().upper()
                isin_code = item.get("isin", "").strip().upper()

                # Find candidate
                candidate = None
                if sym_code in ticker_map and ticker_map[sym_code].symbol not in allocated_symbols:
                    candidate = ticker_map[sym_code]
                elif isin_code and isin_code in isin_map and isin_map[isin_code].symbol not in allocated_symbols:
                    candidate = isin_map[isin_code]
                elif f"NSE:{sym_code}-EQ" in canonical_map and canonical_map[f"NSE:{sym_code}-EQ"].symbol not in allocated_symbols:
                    candidate = canonical_map[f"NSE:{sym_code}-EQ"]

                if candidate:
                    candidate.category = cat_name
                    candidate.tier = target_tier
                    candidate.priority_rank = start_rank + len(matched)
                    allocated_symbols.add(candidate.symbol)
                    matched.append(candidate)
                    if len(matched) == target_count:
                        break

            # If matching yielded fewer than target_count (rare edge case), backfill from unallocated
            if len(matched) < target_count:
                logger.warning(
                    "Index %s matched %d stocks (target %d). Backfilling from unallocated pool.",
                    cat_name, len(matched), target_count,
                )
                for s in symbols:
                    if s.symbol not in allocated_symbols and s.series == "EQ":
                        s.category = cat_name
                        s.tier = target_tier
                        s.priority_rank = start_rank + len(matched)
                        allocated_symbols.add(s.symbol)
                        matched.append(s)
                        if len(matched) == target_count:
                            break

            return matched

        # 1. Nifty 50 -> Tier 1 (rank 1 to 50)
        n50 = _allocate_index("NIFTY50", 50, 1, 1)

        # 2. Nifty Next 50 -> Tier 1 (rank 51 to 100)
        nn50 = _allocate_index("NIFTYNEXT50", 50, 1, 51)

        # 3. Nifty Midcap 150 -> Tier 2 (rank 101 to 250)
        m150 = _allocate_index("NIFTYMIDCAP150", 150, 2, 101)

        # 4. Nifty Smallcap 250 -> Tier 3 (rank 251 to 500)
        s250 = _allocate_index("NIFTYSMALLCAP250", 250, 3, 251)

        # 5. Remaining equities -> Tier 4 (rank 9999)
        for s in symbols:
            if s.symbol not in allocated_symbols:
                s.category = "OTHERS"
                s.tier = 4
                s.priority_rank = 9999

        t1_count = len(n50) + len(nn50)
        t2_count = len(m150)
        t3_count = len(s250)
        logger.info(
            "Tier Classification complete: Tier 1 = %d (50+50), Tier 2 = %d, Tier 3 = %d (Total = %d)",
            t1_count, t2_count, t3_count, t1_count + t2_count + t3_count,
        )
        return symbols

    # -------------------------------------------------------------------------
    # Checkpoint Seeding
    # -------------------------------------------------------------------------

    def seed_download_checkpoints(self) -> Tuple[int, int]:
        """Seeds download_checkpoints table for 1m and 1D data ingestion scopes.
        - 1m Intraday scope: Tiers 1, 2, 3 (500 stocks)
        - 1D Daily scope: Tiers 1 through 4 (All active equities)
        
        Returns:
            Tuple of (seeded_1m_count, seeded_1d_count)
        """
        conn = self.db.get_write_connection()

        # Seed 1m for Tiers 1, 2, 3
        sql_1m = """
            INSERT INTO download_checkpoints (symbol, timeframe, status)
            SELECT symbol, '1m', 'PENDING'
            FROM symbols
            WHERE is_active = TRUE AND tier IN (1, 2, 3)
            ON CONFLICT (symbol, timeframe) DO NOTHING;
        """
        conn.execute(sql_1m)

        # Seed 1D for all active equities (Tiers 1-4)
        sql_1d = """
            INSERT INTO download_checkpoints (symbol, timeframe, status)
            SELECT symbol, '1D', 'PENDING'
            FROM symbols
            WHERE is_active = TRUE
            ON CONFLICT (symbol, timeframe) DO NOTHING;
        """
        conn.execute(sql_1d)

        cursor = self.db.get_read_cursor()
        try:
            count_1m = cursor.execute(
                "SELECT count(*) FROM download_checkpoints WHERE timeframe = '1m';"
            ).fetchone()[0]
            count_1d = cursor.execute(
                "SELECT count(*) FROM download_checkpoints WHERE timeframe = '1D';"
            ).fetchone()[0]
            logger.info("Checkpoints seeded: %d for 1m, %d for 1D.", count_1m, count_1d)
            return count_1m, count_1d
        finally:
            cursor.close()

    # -------------------------------------------------------------------------
    # Market Trading Calendar & Holidays
    # -------------------------------------------------------------------------

    def fetch_market_holidays_online(self) -> List[Dict[str, Any]]:
        """Fetches trading holidays from upstream API (NSE or Upstox fallback)."""
        # Try Upstox public holidays endpoint first (clean, reliable JSON without cookie session requirements)
        try:
            logger.info("Fetching market holidays from %s", HOLIDAY_UPSTOX_URL)
            resp = requests.get(HOLIDAY_UPSTOX_URL, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                holidays: List[Dict[str, Any]] = []
                for item in data:
                    closed = item.get("closed_exchanges", [])
                    holiday_type = item.get("holiday_type", "")
                    # Consider NSE closed or special timing (Muhurat / Budget day)
                    if "NSE" in closed or holiday_type in ("TRADING_HOLIDAY", "SPECIAL_TIMING"):
                        is_special = (holiday_type == "SPECIAL_TIMING")
                        start_time = "18:15:00" if is_special else "09:15:00"
                        end_time = "19:15:00" if is_special else "15:30:00"
                        holidays.append({
                            "holiday_date": item.get("date"),
                            "description": item.get("description", "Market Holiday"),
                            "is_special_session": is_special,
                            "trading_start": start_time,
                            "trading_end": end_time,
                        })
                if holidays:
                    logger.info("Successfully fetched %d market holidays from Upstox.", len(holidays))
                    return holidays
        except Exception as e:
            logger.warning("Upstox holiday API failed: %s", e)

        # Try NSE official holiday master with browser session
        try:
            logger.info("Fetching market holidays from NSE: %s", HOLIDAY_NSE_URL)
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.nseindia.com/resources/exchange-communication-holidays",
            })
            session.get("https://www.nseindia.com", timeout=10)
            resp = session.get(HOLIDAY_NSE_URL, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                cm_holidays = data.get("CM", [])
                holidays = []
                for item in cm_holidays:
                    # tradingDate format: '26-Jan-2026'
                    raw_dt = item.get("tradingDate")
                    parsed_dt = datetime.strptime(raw_dt, "%d-%b-%Y").strftime("%Y-%m-%d")
                    desc = item.get("description", "NSE Holiday")
                    is_special = "muhurat" in desc.lower() or "special" in desc.lower()
                    holidays.append({
                        "holiday_date": parsed_dt,
                        "description": desc,
                        "is_special_session": is_special,
                        "trading_start": "18:15:00" if is_special else "09:15:00",
                        "trading_end": "19:15:00" if is_special else "15:30:00",
                    })
                if holidays:
                    return holidays
        except Exception as e:
            logger.warning("NSE holiday API failed: %s", e)

        # Fallback to local cache if present
        if HOLIDAYS_CACHE_FILE.exists():
            try:
                logger.info("Loading holidays from local cache: %s", HOLIDAYS_CACHE_FILE)
                return json.loads(HOLIDAYS_CACHE_FILE.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed loading holidays cache: %s", e)

        return []

    def sync_market_holidays(self) -> int:
        """Fetches live holidays and syncs them into market_holidays table.
        Returns count of synced holidays.
        """
        holidays = self.fetch_market_holidays_online()
        if not holidays:
            logger.warning("No market holidays retrieved from upstream or cache.")
            return 0

        # Update cache file
        try:
            HOLIDAYS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            HOLIDAYS_CACHE_FILE.write_text(json.dumps(holidays, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug("Failed saving holiday cache: %s", e)

        conn = self.db.get_write_connection()
        sql = """
            INSERT INTO market_holidays (
                holiday_date, description, is_special_session, trading_start, trading_end
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (holiday_date) DO UPDATE SET
                description = EXCLUDED.description,
                is_special_session = EXCLUDED.is_special_session,
                trading_start = EXCLUDED.trading_start,
                trading_end = EXCLUDED.trading_end;
        """
        for h in holidays:
            conn.execute(sql, [
                h["holiday_date"],
                h["description"],
                h.get("is_special_session", False),
                h.get("trading_start", "09:15:00"),
                h.get("trading_end", "15:30:00"),
            ])

        logger.info("Persisted %d market holidays into market_holidays table.", len(holidays))
        return len(holidays)

    def is_trading_holiday(self, check_date: Union[date, str]) -> bool:
        """Determines if a given date is a market trading holiday."""
        d_str = check_date if isinstance(check_date, str) else check_date.strftime("%Y-%m-%d")
        cursor = self.db.get_read_cursor()
        try:
            row = cursor.execute(
                "SELECT is_special_session FROM market_holidays WHERE holiday_date = ?;",
                [d_str],
            ).fetchone()
            if row is None:
                return False
            # If special session (e.g. Muhurat trading), market is NOT closed
            is_special = row[0]
            return not is_special
        finally:
            cursor.close()

    def get_market_holidays(
        self, start_date: Optional[Union[date, str]] = None, end_date: Optional[Union[date, str]] = None
    ) -> List[Dict[str, Any]]:
        """Query stored market holidays within date range."""
        cursor = self.db.get_read_cursor()
        try:
            if start_date and end_date:
                s_str = start_date if isinstance(start_date, str) else start_date.strftime("%Y-%m-%d")
                e_str = end_date if isinstance(end_date, str) else end_date.strftime("%Y-%m-%d")
                rows = cursor.execute(
                    """
                    SELECT holiday_date, description, is_special_session, trading_start, trading_end
                    FROM market_holidays
                    WHERE holiday_date BETWEEN ? AND ?
                    ORDER BY holiday_date ASC;
                    """,
                    [s_str, e_str],
                ).fetchall()
            else:
                rows = cursor.execute(
                    """
                    SELECT holiday_date, description, is_special_session, trading_start, trading_end
                    FROM market_holidays
                    ORDER BY holiday_date ASC;
                    """
                ).fetchall()

            return [
                {
                    "holiday_date": str(r[0]),
                    "description": r[1],
                    "is_special_session": bool(r[2]),
                    "trading_start": str(r[3]),
                    "trading_end": str(r[4]),
                }
                for r in rows
            ]
        finally:
            cursor.close()
