"""
Open Interest (ΔOI) Calculation Engine & F&O Universe Registry.
Calculates strike-by-strike open interest distributions, intraday ΔOI shifts,
Put/Call Ratios (PCR), support/resistance walls, and max pain levels.
"""

import math
import datetime
import logging
from typing import Optional, List, Dict, Tuple, Any

from api.models.options_models import (
    StrikeOIData,
    OpenInterestAnalysisResponse,
    FOUnderlyingItem,
    FOUnderlyingListResponse,
)
from services.options.greeks_engine import BlackScholesGreeks
from services.options.payoff_calculator import PayoffCalculator
from db.connection import get_db

logger = logging.getLogger(__name__)


class FOUniverseRegistry:
    """
    Registry of National Stock Exchange (NSE) F&O underlyings with standardized lot sizes,
    dynamic spot pricing via DuckDB read cursors, and strike step intervals.
    """

    INDEX_DEFINITIONS: Dict[str, Dict[str, Any]] = {
        "NIFTY": {"display_name": "NIFTY 50", "category": "INDEX", "lot_size": 25, "strike_step": 50.0, "default_spot": 25050.0},
        "NIFTY50": {"display_name": "NIFTY 50", "category": "INDEX", "lot_size": 25, "strike_step": 50.0, "default_spot": 25050.0},
        "BANKNIFTY": {"display_name": "NIFTY BANK", "category": "INDEX", "lot_size": 15, "strike_step": 100.0, "default_spot": 51200.0},
        "NIFTYBANK": {"display_name": "NIFTY BANK", "category": "INDEX", "lot_size": 15, "strike_step": 100.0, "default_spot": 51200.0},
        "FINNIFTY": {"display_name": "FIN NIFTY", "category": "INDEX", "lot_size": 25, "strike_step": 50.0, "default_spot": 23400.0},
        "MIDCPNIFTY": {"display_name": "MIDCAP NIFTY", "category": "INDEX", "lot_size": 50, "strike_step": 25.0, "default_spot": 13100.0},
    }

    # 180+ Active NSE F&O Equity Underlyings with accurate lot sizes
    EQUITY_LOT_SIZES: Dict[str, int] = {
        "AARTIIND": 1000, "ABB": 125, "ABBOTINDIA": 40, "ABCAPITAL": 3100, "ABFRL": 2600,
        "ACC": 300, "ADANIENT": 300, "ADANIPORTS": 400, "ALKEM": 100, "AMBUJACEM": 900,
        "APOLLOHOSP": 125, "APOLLOTYRE": 1700, "ASHOKLEY": 5000, "ASIANPAINT": 200, "ASTRAL": 275,
        "ATUL": 75, "AUBANK": 1000, "AUROPHARMA": 550, "AXISBANK": 625, "BAJAJ-AUTO": 75,
        "BAJAJFINSV": 500, "BAJFINANCE": 125, "BALKRISIND": 300, "BALRAMCHIN": 1600, "BANDHANBNK": 2500,
        "BANKBARODA": 2925, "BATAINDIA": 375, "BEL": 2700, "BERGEPAINT": 1100, "BHARATFORG": 500,
        "BHARTIARTL": 475, "BHEL": 2625, "BIOCON": 2500, "BOSCHLTD": 25, "BPCL": 1800,
        "BRITANNIA": 200, "BSOFT": 1000, "CANBK": 4500, "CANFINHOME": 975, "CHAMBLFERT": 1500,
        "CHOLAFIN": 625, "CIPLA": 650, "COALINDIA": 2100, "COFORGE": 150, "COLPAL": 200,
        "CONCOR": 1000, "COROMANDEL": 700, "CROMPTON": 1800, "CUB": 5000, "CUMMINSIND": 200,
        "DABUR": 1250, "DALBHARAT": 250, "DEEPAKNTR": 300, "DELHIVERY": 1375, "DIVISLAB": 150,
        "DIXON": 100, "DLF": 825, "DRREDDY": 125, "EICHERMOT": 150, "ESCORTS": 175,
        "EXIDEIND": 1200, "FEDERALBNK": 5000, "GAIL": 2350, "GLENMARK": 475, "GMRINFRA": 10000,
        "GNFC": 1300, "GODREJCP": 500, "GODREJPROP": 275, "GRANULES": 2000, "GRASIM": 250,
        "GUJGASLTD": 1250, "HAL": 150, "HAVELLS": 500, "HCLTECH": 350, "HDFCAMC": 150,
        "HDFCBANK": 550, "HDFCLIFE": 1100, "HEROMOTOCO": 150, "HINDALCO": 1400, "HINDCOPPER": 2650,
        "HINDPETRO": 1875, "HINDUNILVR": 300, "ICICIBANK": 700, "ICICIGI": 350, "ICICIPRULI": 1500,
        "IDEA": 80000, "IDFCFIRSTB": 7500, "IEX": 3750, "IGL": 1375, "INDHOTEL": 1000,
        "INDIACEM": 2900, "INDIAMART": 150, "INDIGO": 150, "INDUSINDBK": 500, "INDUSTOWER": 1700,
        "INFY": 400, "IOC": 4875, "IPCALAB": 650, "IRCTC": 875, "ITC": 1600,
        "JINDALSTEL": 625, "JIOFIN": 2000, "JKCEMENT": 125, "JSWSTEEL": 675, "JUBLFOOD": 1250,
        "KOTAKBANK": 400, "LALPATHLAB": 300, "LAURUSLABS": 1700, "LICHSGFIN": 1000, "LT": 150,
        "LTF": 4462, "LTIM": 150, "LTTS": 200, "LUPIN": 425, "M&M": 350,
        "M&MFIN": 2000, "MANAPPURAM": 3000, "MARICO": 1200, "MARUTI": 50, "MCX": 200,
        "METROPOLIS": 300, "MFSL": 800, "MGL": 400, "MOTHERSON": 6100, "MPHASIS": 275,
        "MRF": 10, "MUTHOOTFIN": 550, "NATIONALUM": 3750, "NAUKRI": 125, "NAVINFLUOR": 175,
        "NESTLEIND": 20, "NMDC": 4500, "NTPC": 1500, "OBEROIRLTY": 350, "OFSS": 125,
        "ONGC": 3850, "PAGEIND": 15, "PEL": 750, "PERSISTENT": 100, "PETRONET": 3000,
        "PFC": 1300, "PIDILITIND": 250, "PIIND": 250, "PNB": 8000, "POLYCAB": 125,
        "POONAWALLA": 1250, "POWERGRID": 1800, "PVRINOX": 400, "RAMCOCEM": 850, "RBLBANK": 2500,
        "RECLTD": 2000, "RELIANCE": 250, "SAIL": 4000, "SBICARD": 800, "SBILIFE": 750,
        "SBIN": 750, "SHREECEM": 25, "SHRIRAMFIN": 300, "SIEMENS": 125, "SRF": 375,
        "SUNPHARMA": 350, "SUNTV": 1500, "SYNGENE": 1000, "TATACHEM": 550, "TATACOMM": 250,
        "TATACONSUM": 900, "TATAMOTORS": 1425, "TATAPOWER": 2000, "TATASTEEL": 5500, "TCS": 175,
        "TECHM": 600, "TITAN": 175, "TORNTPHARM": 250, "TORNTPOWER": 750, "TRENT": 100,
        "TVSMOTOR": 350, "UBL": 400, "ULTRACEMCO": 100, "UNITDSPR": 700, "UPL": 1300,
        "VEDL": 1150, "VOLTAS": 600, "WIPRO": 1500, "ZOMATO": 2500, "ZYDUSLIFE": 900
    }

    INDEX_ALIASES = {
        "NIFTY": "NIFTY50",
        "NIFTY50": "NIFTY50",
        "BANKNIFTY": "NIFTYBANK",
        "NIFTYBANK": "NIFTYBANK",
        "FINNIFTY": "FINNIFTY",
        "MIDCPNIFTY": "MIDCPNIFTY",
        "MIDCAPNIFTY": "MIDCPNIFTY",
    }

    @classmethod
    def clean_symbol(cls, symbol: str) -> str:
        """Strips exchange prefixes and asset suffixes (e.g. NSE:RELIANCE-EQ -> RELIANCE)."""
        s = symbol.strip().upper()
        if ":" in s:
            s = s.split(":")[-1]
        for suffix in ["-EQ", "-INDEX", "-FUT"]:
            if s.endswith(suffix):
                s = s[:-len(suffix)]
        return s

    @classmethod
    def get_fyers_symbol(cls, symbol: str) -> str:
        """Ensures proper Fyers API symbol prefix and suffix (e.g. NSE:NIFTY50-INDEX or NSE:RELIANCE-EQ)."""
        s = symbol.strip().upper()
        if s.startswith("NSE:"):
            bare = s[4:]
            for suffix in ["-INDEX", "-EQ", "-FUT"]:
                if bare.endswith(suffix):
                    bare = bare[:-len(suffix)]
            if bare in cls.INDEX_ALIASES:
                return f"NSE:{cls.INDEX_ALIASES[bare]}-INDEX"
            return s
        clean = cls.clean_symbol(s)
        if clean in cls.INDEX_ALIASES:
            return f"NSE:{cls.INDEX_ALIASES[clean]}-INDEX"
        return f"NSE:{clean}-EQ"

    @classmethod
    def get_lot_size(cls, symbol: str) -> int:
        """Retrieves official lot size for the given underlying asset."""
        clean = cls.clean_symbol(symbol)
        clean = cls.INDEX_ALIASES.get(clean, clean)
        if clean in cls.INDEX_DEFINITIONS:
            return cls.INDEX_DEFINITIONS[clean]["lot_size"]
        if clean in cls.EQUITY_LOT_SIZES:
            return cls.EQUITY_LOT_SIZES[clean]
        # Heuristic fallback: Index default 25, Equities default 250
        if "NIFTY" in clean:
            return 25
        return 250

    @classmethod
    def get_strike_step(cls, symbol: str, spot: float) -> float:
        """Determines appropriate strike step based on underlying type and spot price."""
        clean = cls.clean_symbol(symbol)
        clean = cls.INDEX_ALIASES.get(clean, clean)
        if clean in cls.INDEX_DEFINITIONS:
            return cls.INDEX_DEFINITIONS[clean]["strike_step"]

        if spot > 30000:
            return 100.0
        elif spot > 10000:
            return 50.0
        elif spot > 2500:
            return 50.0
        elif spot > 1000:
            return 20.0
        elif spot > 500:
            return 10.0
        elif spot > 200:
            return 5.0
        return 2.5

    @classmethod
    def get_spot_price(cls, db, symbol: str) -> float:
        """
        Retrieves the latest spot price using a read-only DuckDB cursor,
        falling back to default spot estimates if unpopulated.
        """
        clean = cls.clean_symbol(symbol)
        canonical_idx = cls.INDEX_ALIASES.get(clean, clean)

        # Check index default spot
        if canonical_idx in cls.INDEX_DEFINITIONS:
            default_spot = cls.INDEX_DEFINITIONS[canonical_idx]["default_spot"]
        else:
            default_spots = {
                "RELIANCE": 2865.0, "TCS": 4120.0, "INFY": 1915.0, "HDFCBANK": 1660.0,
                "ICICIBANK": 1240.0, "SBIN": 810.0, "TATAMOTORS": 920.0, "BHARTIARTL": 1650.0,
                "ITC": 490.0, "KOTAKBANK": 1780.0, "LT": 3650.0, "AXISBANK": 1180.0
            }
            default_spot = default_spots.get(clean, 2500.0)

        if db is None:
            return default_spot

        try:
            cursor = db.get_read_cursor()
            try:
                # 1. Exact match on clean symbol
                row = cursor.execute(
                    "SELECT close FROM candles_1d_adjusted WHERE symbol = ? ORDER BY date DESC LIMIT 1",
                    [clean]
                ).fetchone()

                if not row:
                    # 2. Match with NSE: prefix
                    row = cursor.execute(
                        "SELECT close FROM candles_1d_adjusted WHERE symbol LIKE ? ORDER BY date DESC LIMIT 1",
                        [f"%{clean}%"]
                    ).fetchone()

                if not row:
                    # 3. Check candles_1d_raw
                    row = cursor.execute(
                        "SELECT close FROM candles_1d_raw WHERE symbol LIKE ? ORDER BY date DESC LIMIT 1",
                        [f"%{clean}%"]
                    ).fetchone()

                if row and row[0] is not None and float(row[0]) > 0:
                    return round(float(row[0]), 2)
            finally:
                cursor.close()
        except Exception as e:
            logger.debug("DB query for spot %s failed, using default: %s", symbol, e)

        return default_spot

    @classmethod
    def get_all_underlyings(cls, db=None) -> FOUnderlyingListResponse:
        """Compiles complete catalog of indices and equities for Options Lab UI dropdowns."""
        indices: List[FOUnderlyingItem] = []
        equities: List[FOUnderlyingItem] = []

        seen_indices = set()
        for key in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"]:
            data = cls.INDEX_DEFINITIONS[key]
            disp = data["display_name"]
            if disp in seen_indices:
                continue
            seen_indices.add(disp)
            spot = cls.get_spot_price(db, key)
            indices.append(FOUnderlyingItem(
                symbol=key,
                display_name=disp,
                category="INDEX",
                lot_size=data["lot_size"],
                spot_price=spot,
                strike_step=data["strike_step"]
            ))

        for sym, lot in sorted(cls.EQUITY_LOT_SIZES.items()):
            spot = cls.get_spot_price(db, sym)
            step = cls.get_strike_step(sym, spot)
            equities.append(FOUnderlyingItem(
                symbol=sym,
                display_name=sym,
                category="EQUITY",
                lot_size=lot,
                spot_price=spot,
                strike_step=step
            ))

        return FOUnderlyingListResponse(
            indices=indices,
            equities=equities,
            total_count=len(indices) + len(equities)
        )


class OpenInterestEngine:
    """
    Core engine for Open Interest (ΔOI) computation, Put/Call Ratio analysis,
    Support/Resistance wall detection, and Max Pain strike identification.
    """

    def __init__(self, db=None, fyers_client=None):
        self._db = db
        self.fyers = fyers_client
        self.greeks_engine = BlackScholesGreeks()
        self.payoff_calc = PayoffCalculator()

    @property
    def db(self):
        if self._db is not None:
            return self._db
        try:
            return get_db()
        except Exception as e:
            logger.debug("Could not acquire default DB connection: %s", e)
            return None

    def analyze_open_interest(
        self,
        symbol: str,
        expiry: Optional[str] = None,
        date: Optional[str] = None
    ) -> OpenInterestAnalysisResponse:
        """
        Executes end-to-end Open Interest and sentiment analysis for an underlying asset.
        Supports live broker feeds and historical DB snapshots with strict real data enforcement.
        """
        clean_sym = FOUniverseRegistry.clean_symbol(symbol)
        spot = FOUniverseRegistry.get_spot_price(self.db, clean_sym)

        # 1. Check historical snapshot if requested
        if date:
            snapshot_res = self._load_from_db_snapshot(clean_sym, date, expiry, spot)
            if snapshot_res:
                return snapshot_res

        # 2. Check live broker feed if available
        if self.fyers:
            try:
                live_res = self._load_from_live_fyers(symbol, expiry, spot)
                if live_res:
                    return live_res
            except Exception as e:
                logger.warning("Live option chain fetch failed for %s: %s", symbol, e)

        # 3. Check latest DB snapshot if date was not specified
        if not date:
            latest_res = self._load_latest_db_snapshot(clean_sym, expiry, spot)
            if latest_res:
                return latest_res

        # 4. Strict Zero-Fake Mode: Reject if real data is missing
        raise ValueError(
            f"No verified real option chain data available for '{symbol}'. "
            f"Live Fyers feed returned no data and no historical snapshot exists in DuckDB. "
            f"Please ensure Fyers is authenticated and symbol is an active F&O contract."
        )

    def _load_latest_db_snapshot(
        self,
        symbol: str,
        expiry: Optional[str],
        spot: float
    ) -> Optional[OpenInterestAnalysisResponse]:
        """Loads and computes OI analytics from latest option_chain_snapshots in DuckDB."""
        if self.db is None:
            return None
        try:
            cursor = self.db.get_read_cursor()
            try:
                latest_row = cursor.execute(
                    "SELECT MAX(snapshot_date) FROM option_chain_snapshots WHERE underlying_symbol = ? OR underlying_symbol LIKE ?",
                    [symbol, f"%{symbol}%"]
                ).fetchone()
                if not latest_row or not latest_row[0]:
                    return None
                latest_date = str(latest_row[0])
                return self._load_from_db_snapshot(symbol, latest_date, expiry, spot)
            finally:
                cursor.close()
        except Exception:
            return None

    def _load_from_db_snapshot(
        self,
        symbol: str,
        date: str,
        expiry: Optional[str],
        spot: float
    ) -> Optional[OpenInterestAnalysisResponse]:
        """Loads and computes OI analytics from option_chain_snapshots table."""
        if self.db is None:
            return None
        try:
            cursor = self.db.get_read_cursor()
            try:
                query = "SELECT * FROM option_chain_snapshots WHERE (underlying_symbol = ? OR underlying_symbol LIKE ?) AND snapshot_date = ?"
                params = [symbol, f"%{symbol}%", date]
                if expiry:
                    query += " AND expiry_date = ?"
                    params.append(expiry)

                rows = cursor.execute(query, params).fetchall()
                if not rows:
                    return None

                cols = ["snapshot_date", "underlying_symbol", "expiry_date", "strike_price", "option_type", 
                        "ltp", "oi", "volume", "iv", "delta", "gamma", "theta", "vega", "captured_at"]
                records = [dict(zip(cols, r)) for r in rows]
                resolved_expiry = expiry or (records[0]["expiry_date"] if records else "")
                return self._compile_analysis_from_records(symbol, spot, resolved_expiry, records)
            finally:
                cursor.close()
        except Exception as e:
            logger.error("Error reading option_chain_snapshots for %s: %s", symbol, e)
            return None

    def _load_from_live_fyers(
        self,
        symbol: str,
        expiry: Optional[str],
        spot: float
    ) -> Optional[OpenInterestAnalysisResponse]:
        """Enriches live Fyers option chain into OpenInterestAnalysisResponse."""
        fyers_sym = FOUniverseRegistry.get_fyers_symbol(symbol)
        res = self.fyers.fetch_option_chain(symbol=fyers_sym, strikes=50)
        if not isinstance(res, dict) or res.get("s") != "ok":
            return None

        raw_options = res.get("data", {}).get("optionsChain", [])
        if not raw_options:
            return None

        # Real spot extracted from underlying row if available
        real_spot = spot
        if raw_options and float(raw_options[0].get("strike_price", 0)) == -1:
            real_spot = float(raw_options[0].get("ltp") or spot)

        records = []
        expiry_data = res.get("data", {}).get("expiryData", [])
        resolved_expiry = expiry or (expiry_data[0].get("date", "") if expiry_data else raw_options[0].get("expiry_date", ""))

        for opt in raw_options:
            strike = float(opt.get("strike_price") or opt.get("strike") or 0.0)
            if strike <= 0:
                continue
            records.append({
                "strike_price": strike,
                "option_type": opt.get("option_type") or opt.get("type") or "CE",
                "oi": int(opt.get("oi") or opt.get("open_interest") or 0),
                "oi_change": int(opt.get("oich") or opt.get("oichange") or opt.get("oi_change") or 0),
                "volume": int(opt.get("volume") or 0),
                "ltp": float(opt.get("ltp") or 0.0),
                "iv": float(opt.get("iv") or 15.0),
            })

        if not records:
            return None

        return self._compile_analysis_from_records(symbol, real_spot, resolved_expiry, records)

    def _compile_analysis_from_records(
        self,
        symbol: str,
        spot: float,
        expiry_date: str,
        records: List[Dict[str, Any]]
    ) -> OpenInterestAnalysisResponse:
        """Aggregates raw call and put records into aligned strike structures with PCR and walls."""
        strikes_map: Dict[float, Dict[str, Any]] = {}

        for r in records:
            strike = float(r.get("strike_price", 0.0))
            if strike <= 0:
                continue
            if strike not in strikes_map:
                strikes_map[strike] = {
                    "call_oi": 0, "call_oi_change": 0, "call_vol": 0, "call_ltp": 0.0, "call_iv": 0.0,
                    "put_oi": 0, "put_oi_change": 0, "put_vol": 0, "put_ltp": 0.0, "put_iv": 0.0
                }

            opt_type = r.get("option_type", "CE")
            oi = int(r.get("oi", 0))
            oi_change = int(r.get("oi_change", 0))
            vol = int(r.get("volume", 0))
            ltp = float(r.get("ltp", 0.0))
            iv = float(r.get("iv", 0.0))

            if opt_type == "CE":
                strikes_map[strike]["call_oi"] = oi
                strikes_map[strike]["call_oi_change"] = oi_change
                strikes_map[strike]["call_vol"] = vol
                strikes_map[strike]["call_ltp"] = ltp
                strikes_map[strike]["call_iv"] = iv
            else:
                strikes_map[strike]["put_oi"] = oi
                strikes_map[strike]["put_oi_change"] = oi_change
                strikes_map[strike]["put_vol"] = vol
                strikes_map[strike]["put_ltp"] = ltp
                strikes_map[strike]["put_iv"] = iv

        sorted_strikes = sorted(strikes_map.keys())
        strikes_data: List[StrikeOIData] = []

        total_call_oi = 0
        total_put_oi = 0
        total_call_oi_change = 0
        total_put_oi_change = 0
        pos_call_change = 0
        pos_put_change = 0

        for s in sorted_strikes:
            item = strikes_map[s]
            c_oi = item["call_oi"]
            p_oi = item["put_oi"]
            c_chg = item["call_oi_change"]
            p_chg = item["put_oi_change"]

            total_call_oi += c_oi
            total_put_oi += p_oi
            total_call_oi_change += c_chg
            total_put_oi_change += p_chg

            if c_chg > 0:
                pos_call_change += c_chg
            if p_chg > 0:
                pos_put_change += p_chg

            strikes_data.append(StrikeOIData(
                strike=s,
                call_oi=c_oi,
                call_oi_change=c_chg,
                put_oi=p_oi,
                put_oi_change=p_chg,
                call_volume=item["call_vol"],
                put_volume=item["put_vol"],
                call_ltp=item["call_ltp"],
                put_ltp=item["put_ltp"],
                call_iv=item["call_iv"],
                put_iv=item["put_iv"]
            ))

        # Put/Call Ratios
        pcr_oi = round(total_put_oi / max(1, total_call_oi), 3)
        pcr_oi_change = round(pos_put_change / max(1, pos_call_change), 3)

        # Market Sentiment Classification
        if pcr_oi >= 1.25:
            sentiment = "BULLISH"
        elif pcr_oi <= 0.85:
            sentiment = "BEARISH"
        else:
            sentiment = "NEUTRAL"

        # Major Resistance, Major Support & Max Pain
        major_res = max(strikes_data, key=lambda x: x.call_oi).strike if strikes_data else spot
        major_sup = max(strikes_data, key=lambda x: x.put_oi).strike if strikes_data else spot

        max_pain = self.payoff_calc.max_pain(
            sorted_strikes,
            [s.call_oi for s in strikes_data],
            [s.put_oi for s in strikes_data]
        )

        active_call_battle = max(strikes_data, key=lambda x: abs(x.call_oi_change)).strike if strikes_data else spot
        active_put_battle = max(strikes_data, key=lambda x: abs(x.put_oi_change)).strike if strikes_data else spot

        return OpenInterestAnalysisResponse(
            symbol=symbol,
            spot=spot,
            expiry_date=expiry_date,
            total_call_oi=total_call_oi,
            total_put_oi=total_put_oi,
            total_call_oi_change=total_call_oi_change,
            total_put_oi_change=total_put_oi_change,
            pcr_oi=pcr_oi,
            pcr_oi_change=pcr_oi_change,
            sentiment=sentiment,
            major_resistance_strike=major_res,
            major_support_strike=major_sup,
            max_pain_strike=max_pain,
            active_call_battleground=active_call_battle,
            active_put_battleground=active_put_battle,
            strikes_data=strikes_data
        )

