"""
Portfolio Universe Service.
Provides predefined NSE index universes (NIFTY 50, NIFTY NEXT 50, NIFTY MIDCAP 150),
validates symbol availability, and fetches multi-symbol candle data concurrently
via non-blocking DuckDB read cursors.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np


class PortfolioUniverseService:
    """Manages predefined and custom equity universes for portfolio backtesting."""

    _CACHE: Optional[Dict[str, List[str]]] = None

    @classmethod
    def _load_indices_file(cls) -> Dict[str, List[str]]:
        if cls._CACHE is not None:
            return cls._CACHE

        indices_path = Path("config/indices/manual_override_indices.json")
        data = {}
        if indices_path.exists():
            try:
                with open(indices_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                    for key, items in raw_data.items():
                        norm_key = key.upper().replace("_", "").replace(" ", "")
                        symbols = []
                        for item in items:
                            sym = item.get("symbol") if isinstance(item, dict) else str(item)
                            if sym:
                                # Standardize to NSE ticker with EQ suffix
                                formatted = f"NSE:{sym}-EQ" if not sym.startswith("NSE:") else sym
                                symbols.append(formatted)
                        data[norm_key] = symbols
            except Exception:
                data = {}

        # Fallback defaults if file cannot be read
        if "NIFTY50" not in data or not data["NIFTY50"]:
            data["NIFTY50"] = [
                f"NSE:{s}-EQ"
                for s in [
                    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "BHARTIARTL",
                    "ITC", "SBIN", "LT", "HCLTECH", "BAJFINANCE", "SUNPHARMA",
                    "MARUTI", "KOTAKBANK", "TATAMOTORS", "AXISBANK", "NTPC", "ONGC",
                    "ADANIENT", "TITAN", "POWERGRID", "ULTRACEMCO", "COALINDIA",
                    "BAJAJFINSV", "ASIANPAINT", "WIPRO", "TATASTEEL", "M&M", "JSWSTEEL",
                    "ADANIPORTS", "HINDUNILVR", "SIEMENS", "IOC", "BPCL", "SBILIFE",
                    "GRASIM", "HDFCLIFE", "BRITANNIA", "TECHM", "CIPLA", "EICHERMOT",
                    "APOLLOHOSP", "HEROMOTOCO", "TATACONSUM", "INDUSINDBK", "DIVISLAB",
                    "DRREDDY", "NESTLEIND", "SHRIRAMFIN", "TRENT",
                ]
            ]

        if "NIFTYNEXT50" not in data or not data["NIFTYNEXT50"]:
            data["NIFTYNEXT50"] = [
                f"NSE:{s}-EQ"
                for s in [
                    "ABB", "ADANIENSOL", "ADANIGREEN", "ADANIPOWER", "AMBUJACEM", "DMART",
                    "BAJAJHLDNG", "BANKBARODA", "BPCL", "BOSCHLTD", "BRITANNIA", "CGPOWER",
                    "CANBK", "CHOLAFIN", "CUMMINSIND", "DLF", "DIVISLAB", "GAIL",
                    "GODREJCP", "HDFCAMC", "HAL", "HINDZINC", "IOC", "IRFC", "JINDALSTEL",
                    "MUTHOOTFIN", "PIDILITIND", "POLYCAB", "PFC", "PNB", "MOTHERSON",
                    "SIEMENS", "SOLARINDS", "TVSMOTOR", "TATAPOWER", "TORNTPHARM",
                    "UNIONBANK", "VBL", "VEDL", "WIPRO", "ZYDUSLIFE",
                ]
            ]

        if "NIFTYMIDCAP150" not in data or not data["NIFTYMIDCAP150"]:
            data["NIFTYMIDCAP150"] = [
                f"NSE:{s}-EQ"
                for s in [
                    "360ONE", "AIAENG", "APLAPOLLO", "AUBANK", "ABBOTINDIA", "ATGL",
                    "ABCAPITAL", "AJANTPHARM", "ALKEM", "ASHOKLEY", "ASTRAL", "AUROPHARMA",
                    "BALKRISIND", "BANDHANBNK", "BATAINDIA", "BHARATFORG", "BHEL",
                    "BIOCON", "COLPAL", "CONCOR", "COROMANDEL", "CROMPTON", "DEEPAKNTR",
                    "DELHIVERY", "DIXON", "ESCORTS", "EXIDEIND", "FEDERALBNK", "FORTIS",
                    "GLENMARK", "GMRINFRA", "GODREJPROP", "GUJGASLTD", "IDFCFIRSTB",
                    "IPCALAB", "JUBLFOOD", "KALYANKJIL", "KPITTECH", "LALPATHLAB",
                    "LICHSGFIN", "LUPIN", "MFSL", "MRF", "OBEROIRLTY", "PAGEIND",
                    "PERSISTENT", "PETRONET", "PHOENIXLTD", "PRESTIGE", "SAIL",
                ]
            ]

        cls._CACHE = data
        return cls._CACHE

    @classmethod
    def get_available_universes(cls) -> List[Dict[str, Any]]:
        """Returns list of selectable predefined universes with metadata."""
        indices = cls._load_indices_file()
        return [
            {
                "id": "NIFTY_50",
                "name": "NIFTY 50",
                "description": "Top 50 high-liquidity blue-chip equities listed on the NSE.",
                "count": len(indices.get("NIFTY50", [])),
                "tier": 1,
            },
            {
                "id": "NIFTY_NEXT_50",
                "name": "NIFTY NEXT 50",
                "description": "50 large-cap emerging blue-chips with strong institutional participation.",
                "count": len(indices.get("NIFTYNEXT50", [])),
                "tier": 1,
            },
            {
                "id": "NIFTY_MIDCAP_150",
                "name": "NIFTY MIDCAP 150",
                "description": "150 high-beta midcap equities capturing broader market momentum.",
                "count": len(indices.get("NIFTYMIDCAP150", [])),
                "tier": 2,
            },
        ]

    @classmethod
    def get_constituents(cls, universe_name: str) -> List[str]:
        """Resolves universe identifier to list of standardized symbols."""
        indices = cls._load_indices_file()
        norm_key = (universe_name or "NIFTY_50").upper().replace("_", "").replace(" ", "")

        if norm_key in indices:
            return indices[norm_key]
        elif "NIFTY50" in norm_key:
            return indices.get("NIFTY50", [])
        elif "NEXT" in norm_key:
            return indices.get("NIFTYNEXT50", [])
        elif "MIDCAP" in norm_key:
            return indices.get("NIFTYMIDCAP150", [])
        return indices.get("NIFTY50", [])

    @classmethod
    def normalize_symbol(cls, symbol: str) -> str:
        """Standardizes user input symbol to canonical NSE ticker (e.g. RELIANCE -> NSE:RELIANCE-EQ)."""
        s = symbol.strip().upper()
        if not s.startswith("NSE:"):
            s = f"NSE:{s}"
        if not s.endswith("-EQ") and not s.endswith("-INDEX"):
            s = f"{s}-EQ"
        return s

    @classmethod
    def load_universe_candles(
        cls,
        symbols: List[str],
        start_date: str,
        end_date: str,
        db=None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Loads verified real OHLCV candles for all specified symbols from DuckDB.
        Attempts JIT sync from Fyers API for missing symbols.
        Strictly zero synthetic or simulated data: symbols without real data are omitted.
        """
        results: Dict[str, pd.DataFrame] = {}
        symbols = [cls.normalize_symbol(s) for s in symbols]

        def _fetch_from_db(sym_list: List[str]):
            if not db or not sym_list:
                return
            try:
                cursor = db.get_read_cursor()
                placeholders = ",".join(["?"] * len(sym_list))
                query = f"""
                    SELECT symbol, date, open, high, low, close, volume
                    FROM candles_1d_adjusted
                    WHERE symbol IN ({placeholders})
                      AND date >= CAST(? AS DATE) AND date <= CAST(? AS DATE)
                    ORDER BY symbol, date ASC
                """
                params = list(sym_list) + [start_date, end_date]
                rows = cursor.execute(query, params).fetchall()

                # If no adjusted rows found, try raw candles
                if not rows:
                    query_raw = f"""
                        SELECT symbol, date, open, high, low, close, volume
                        FROM candles_1d_raw
                        WHERE symbol IN ({placeholders})
                          AND date >= CAST(? AS DATE) AND date <= CAST(? AS DATE)
                        ORDER BY symbol, date ASC
                    """
                    rows = cursor.execute(query_raw, params).fetchall()

                cursor.close()

                if rows:
                    df_all = pd.DataFrame(
                        rows,
                        columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"],
                    )
                    for sym, group in df_all.groupby("symbol"):
                        if len(group) >= 15:
                            clean_group = group.drop(columns=["symbol"]).sort_values("timestamp").reset_index(drop=True)
                            clean_group["timestamp"] = pd.to_datetime(clean_group["timestamp"])
                            results[sym] = clean_group
            except Exception:
                pass

        _fetch_from_db(symbols)

        # For any symbol missing from database, attempt JIT Fyers sync (if authenticated)
        missing_symbols = [s for s in symbols if s not in results]
        if missing_symbols and db is not None:
            try:
                from services.live_market_data_service import LiveMarketDataService
                s_date = datetime.strptime(start_date.split("T")[0], "%Y-%m-%d").date()
                e_date = datetime.strptime(end_date.split("T")[0], "%Y-%m-%d").date()
                live_service = LiveMarketDataService(db=db)
                synced_any = False
                for sym in missing_symbols:
                    ins = live_service.ensure_symbol_history(sym, "1D", s_date, e_date)
                    if ins > 0:
                        synced_any = True
                if synced_any:
                    _fetch_from_db(missing_symbols)
            except Exception:
                pass

        # Zero synthetic fallback: return only symbols with verified real DuckDB data
        return results

    @classmethod
    def load_benchmark_candles(
        cls,
        start_date: str,
        end_date: str,
        db=None,
    ) -> pd.DataFrame:
        """Loads verified real NIFTY 50 benchmark index daily candles from DuckDB.
        
        Strictly refuses any fake synthetic Geometric Brownian Motion data.
        """
        benchmark_sym = "NSE:NIFTY50-INDEX"
        if db is not None:
            try:
                cursor = db.get_read_cursor()
                rows = cursor.execute("""
                    SELECT date, open, high, low, close, volume
                    FROM candles_1d_raw
                    WHERE symbol = ? AND date >= CAST(? AS DATE) AND date <= CAST(? AS DATE)
                    ORDER BY date ASC
                """, [benchmark_sym, start_date, end_date]).fetchall()
                if not rows:
                    rows = cursor.execute("""
                        SELECT date, open, high, low, close, volume
                        FROM candles_1d_adjusted
                        WHERE symbol = ? AND date >= CAST(? AS DATE) AND date <= CAST(? AS DATE)
                        ORDER BY date ASC
                    """, [benchmark_sym, start_date, end_date]).fetchall()
                cursor.close()
                if rows and len(rows) >= 15:
                    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    return df
            except Exception:
                pass

            # Attempt auto-fetch Nifty index from Fyers if not in DuckDB
            try:
                from services.live_market_data_service import LiveMarketDataService
                s_date = datetime.strptime(start_date.split("T")[0], "%Y-%m-%d").date()
                e_date = datetime.strptime(end_date.split("T")[0], "%Y-%m-%d").date()
                live_service = LiveMarketDataService(db=db)
                ins = live_service.ensure_symbol_history(benchmark_sym, "1D", s_date, e_date)
                if ins > 0:
                    cursor = db.get_read_cursor()
                    rows = cursor.execute("""
                        SELECT date, open, high, low, close, volume
                        FROM candles_1d_raw
                        WHERE symbol = ? AND date >= CAST(? AS DATE) AND date <= CAST(? AS DATE)
                        ORDER BY date ASC
                    """, [benchmark_sym, start_date, end_date]).fetchall()
                    cursor.close()
                    if rows and len(rows) >= 15:
                        df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
                        df["timestamp"] = pd.to_datetime(df["timestamp"])
                        return df
            except Exception:
                pass

        # Zero synthetic fallback: return empty DataFrame if no real benchmark candles exist
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
