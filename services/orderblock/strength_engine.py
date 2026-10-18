"""Intraday One-Directional Strength Engine.
Calculates 50-day Average Daily Move (ADM), 2x one-sided boundary score, and event-risk suppression.
"""

from dataclasses import dataclass, field
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Sector classification for active NSE F&O equities
DEFAULT_SECTOR_MAP: Dict[str, str] = {
    # IT
    "NSE:TCS-EQ": "IT",
    "NSE:INFY-EQ": "IT",
    "NSE:WIPRO-EQ": "IT",
    "NSE:HCLTECH-EQ": "IT",
    "NSE:TECHM-EQ": "IT",
    "NSE:LTIM-EQ": "IT",
    "NSE:COFORGE-EQ": "IT",
    "NSE:PERSISTENT-EQ": "IT",
    "NSE:MPHASIS-EQ": "IT",
    # Banking
    "NSE:HDFCBANK-EQ": "Banking",
    "NSE:ICICIBANK-EQ": "Banking",
    "NSE:SBIN-EQ": "Banking",
    "NSE:KOTAKBANK-EQ": "Banking",
    "NSE:AXISBANK-EQ": "Banking",
    "NSE:INDUSINDBK-EQ": "Banking",
    "NSE:BANKBARODA-EQ": "Banking",
    "NSE:PNB-EQ": "Banking",
    "NSE:FEDERALBNK-EQ": "Banking",
    "NSE:AUBANK-EQ": "Banking",
    # Financial Services
    "NSE:BAJFINANCE-EQ": "Finance",
    "NSE:BAJAJFINSV-EQ": "Finance",
    "NSE:CHOLAFIN-EQ": "Finance",
    "NSE:SHRIRAMFIN-EQ": "Finance",
    "NSE:MUTHOOTFIN-EQ": "Finance",
    "NSE:HDFCLIFE-EQ": "Finance",
    "NSE:SBILIFE-EQ": "Finance",
    "NSE:ICICIPRULI-EQ": "Finance",
    # Energy & Utilities
    "NSE:RELIANCE-EQ": "Energy",
    "NSE:NTPC-EQ": "Utilities",
    "NSE:POWERGRID-EQ": "Utilities",
    "NSE:ONGC-EQ": "Energy",
    "NSE:BPCL-EQ": "Energy",
    "NSE:IOC-EQ": "Energy",
    "NSE:COALINDIA-EQ": "Energy",
    "NSE:TATAPOWER-EQ": "Utilities",
    "NSE:ADANIPOWER-EQ": "Utilities",
    "NSE:ADANIENSOL-EQ": "Utilities",
    # Auto
    "NSE:TATAMOTORS-EQ": "Auto",
    "NSE:MARUTI-EQ": "Auto",
    "NSE:M&M-EQ": "Auto",
    "NSE:BAJAJ-AUTO-EQ": "Auto",
    "NSE:HEROMOTOCO-EQ": "Auto",
    "NSE:EICHERMOT-EQ": "Auto",
    "NSE:TVSMOTOR-EQ": "Auto",
    "NSE:BHARATFORG-EQ": "Auto",
    # FMCG & Consumption
    "NSE:HINDUNILVR-EQ": "FMCG",
    "NSE:ITC-EQ": "FMCG",
    "NSE:NESTLEIND-EQ": "FMCG",
    "NSE:BRITANNIA-EQ": "FMCG",
    "NSE:TATACONSUM-EQ": "FMCG",
    "NSE:DABUR-EQ": "FMCG",
    "NSE:GODREJCP-EQ": "FMCG",
    "NSE:MARICO-EQ": "FMCG",
    "NSE:COLPAL-EQ": "FMCG",
    "NSE:TITAN-EQ": "Consumer",
    "NSE:ASIANPAINT-EQ": "Consumer",
    "NSE:PIDILITIND-EQ": "Consumer",
    "NSE:TRENT-EQ": "Consumer",
    # Pharma & Healthcare
    "NSE:SUNPHARMA-EQ": "Pharma",
    "NSE:CIPLA-EQ": "Pharma",
    "NSE:DRREDDY-EQ": "Pharma",
    "NSE:DIVISLAB-EQ": "Pharma",
    "NSE:APOLLOHOSP-EQ": "Healthcare",
    "NSE:LUPIN-EQ": "Pharma",
    "NSE:AUROPHARMA-EQ": "Pharma",
    "NSE:TORNTPHARM-EQ": "Pharma",
    "NSE:MANKIND-EQ": "Pharma",
    # Metals & Mining
    "NSE:TATASTEEL-EQ": "Metals",
    "NSE:JSWSTEEL-EQ": "Metals",
    "NSE:HINDALCO-EQ": "Metals",
    "NSE:VEDL-EQ": "Metals",
    "NSE:JINDALSTEL-EQ": "Metals",
    "NSE:NMDC-EQ": "Metals",
    "NSE:NATIONALUM-EQ": "Metals",
    # Capital Goods & Infra
    "NSE:LT-EQ": "Infra",
    "NSE:SIEMENS-EQ": "Capital Goods",
    "NSE:ABB-EQ": "Capital Goods",
    "NSE:HAL-EQ": "Defense",
    "NSE:BEL-EQ": "Defense",
    "NSE:BHEL-EQ": "Capital Goods",
}


@dataclass
class StockStrengthMetric:
    symbol: str
    sector: str
    score: float
    side: str  # "BULLISH", "BEARISH", "NEUTRAL"
    open_price: float
    high_price: float
    low_price: float
    current_price: float
    is_event_risk: bool = False
    event_risk_reason: str = ""
    delta_high: float = 0.0
    delta_low: float = 0.0
    day_move_pct: float = 0.0
    adm: float = 0.0


class IntradayStrengthEngine:
    """Calculates one-directional institutional strength and event-risk boundaries."""

    def __init__(self, db_manager: Any = None, sector_map: Optional[Dict[str, str]] = None) -> None:
        self.db = db_manager
        self.sector_map = sector_map or DEFAULT_SECTOR_MAP
        self._adm_cache: Dict[str, float] = {}
        self._open_0920_cache: Dict[str, float] = {}

    def get_sector(self, symbol: str) -> str:
        """Resolve sector classification for equity symbol."""
        if symbol in self.sector_map:
            return self.sector_map[symbol]
        clean_sym = symbol.replace("-EQ", "").split(":")[-1]
        for k, v in self.sector_map.items():
            if clean_sym in k:
                return v
        return "General"

    def compute_adm(self, symbol: str, lookback: int = 50) -> float:
        """Computes 50-session Average Daily Move (ADM) from candles_1d_adjusted."""
        if symbol in self._adm_cache:
            return self._adm_cache[symbol]

        if not self.db:
            return 0.0

        query = """
            SELECT high, low 
            FROM candles_1d_adjusted 
            WHERE symbol = ? 
            ORDER BY date DESC 
            LIMIT ?
        """
        cursor = self.db.get_read_cursor()
        try:
            rows = cursor.execute(query, (symbol, lookback)).fetchall()
            if not rows:
                rows = cursor.execute("""
                    SELECT high, low 
                    FROM candles_1d_raw 
                    WHERE symbol = ? 
                    ORDER BY date DESC 
                    LIMIT ?
                """, (symbol, lookback)).fetchall()
            if not rows:
                return 0.0
            total_range = sum(float(r[0]) - float(r[1]) for r in rows if r[0] is not None and r[1] is not None)
            adm = total_range / len(rows) if rows else 0.0
            self._adm_cache[symbol] = round(adm, 2)
            return round(adm, 2)
        except Exception as e:
            logger.error(f"Error computing ADM for {symbol}: {e}")
            return 0.0
        finally:
            cursor.close()

    def evaluate_strength(
        self,
        symbol: str,
        open_price: float,
        high_price: float,
        low_price: float,
        current_price: float,
        adm: Optional[float] = None,
        sector: Optional[str] = None
    ) -> StockStrengthMetric:
        """Evaluates clean expansion away from open with strict 2x one-sided boundary and event-risk check."""
        if adm is None or adm <= 0:
            adm = self.compute_adm(symbol, lookback=50)

        # Fallback ADM if historical lookback is missing or zero
        if adm <= 0:
            intraday_range = max(1.0, high_price - low_price)
            adm = round(max(intraday_range, current_price * 0.015), 2)

        eff_sector = sector or self.get_sector(symbol)
        
        delta_high = max(0.0, high_price - open_price)
        delta_low = max(0.0, open_price - low_price)
        day_move_pct = ((current_price - open_price) / open_price * 100.0) if open_price > 0 else 0.0

        # Event-Risk Detection (F4)
        is_event_risk = False
        event_risk_reason = ""
        
        # Rule 1: Intraday drop > 5.0% from open
        drop_from_open_pct = ((open_price - min(low_price, current_price)) / open_price * 100.0) if open_price > 0 else 0.0
        if drop_from_open_pct > 5.0:
            is_event_risk = True
            event_risk_reason = f"Intraday drop > 5.0% (-{drop_from_open_pct:.2f}%)"
            
        # Rule 2: Intraday drop > 2.5x ADM
        elif adm > 0 and (open_price - low_price) > (2.5 * adm):
            is_event_risk = True
            event_risk_reason = f"Intraday drop > 2.5x ADM ({(open_price - low_price):.1f} vs {2.5 * adm:.1f})"

        # Strength Scoring Formula (F1)
        score = 0.0
        side = "NEUTRAL"
        
        if delta_high > (2.0 * delta_low):
            side = "BULLISH"
            score = (delta_high / adm) if adm > 0 else 0.0
        elif delta_low > (2.0 * delta_high):
            side = "BEARISH"
            score = (delta_low / adm) if adm > 0 else 0.0

        return StockStrengthMetric(
            symbol=symbol,
            sector=eff_sector,
            score=round(score, 4),
            side=side,
            open_price=round(open_price, 2),
            high_price=round(high_price, 2),
            low_price=round(low_price, 2),
            current_price=round(current_price, 2),
            is_event_risk=is_event_risk,
            event_risk_reason=event_risk_reason,
            delta_high=round(delta_high, 2),
            delta_low=round(delta_low, 2),
            day_move_pct=round(day_move_pct, 2),
            adm=round(adm, 2)
        )
