"""5-Minute Institutional Order-Block Zone Engine.
Detects institutional order block zones on finished 5-minute bars and tracks mitigation/invalidation state.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging
import pytz

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")


@dataclass
class Candle5m:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0


@dataclass
class OrderBlockZone:
    symbol: str
    block_type: str  # "BULLISH" or "BEARISH"
    start_time: datetime
    top_price: float
    bottom_price: float
    invalidation_price: float
    end_time: Optional[datetime] = None
    is_mitigated: bool = False
    mitigation_timestamp: Optional[datetime] = None
    timeframe: str = "5m"


class OrderBlockZoneEngine:
    """Engine identifying 5-minute unmitigated and mitigated order blocks."""

    def __init__(self, db_manager: Any = None) -> None:
        self.db = db_manager

    def detect_zones(self, symbol: str, candles: List[Candle5m], swing_lookback: int = 5) -> List[OrderBlockZone]:
        """Detects order block zones and evaluates subsequent mitigation on 5-minute bars."""
        if len(candles) < 3:
            return []

        zones: List[OrderBlockZone] = []
        seen_keys = set()

        for i in range(1, len(candles)):
            curr = candles[i]
            window_start = max(0, i - swing_lookback)
            prev_window = candles[window_start:i]
            if not prev_window:
                continue

            prev_high = max(c.high for c in prev_window)
            prev_low = min(c.low for c in prev_window)

            # Bullish Order Block Check
            # Current candle expands upward and closes above prior swing high
            if curr.close > curr.open and curr.close > prev_high:
                # Find the last down-candle (bearish candle: close < open) before the impulse
                ob_candle: Optional[Candle5m] = None
                for j in range(i - 1, max(-1, i - 4), -1):
                    if candles[j].close < candles[j].open:
                        ob_candle = candles[j]
                        break

                if ob_candle:
                    key = ("BULLISH", ob_candle.timestamp)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        top = ob_candle.high
                        bottom = ob_candle.low
                        inval = bottom
                        
                        # Evaluate mitigation across subsequent bars after ob_candle
                        is_mitigated = False
                        mitigation_ts: Optional[datetime] = None
                        ob_idx = candles.index(ob_candle)
                        
                        for k in range(ob_idx + 1, len(candles)):
                            # Invalidation occurs when a 5-minute bar closes below S1 (inval)
                            if candles[k].close < inval:
                                is_mitigated = True
                                mitigation_ts = candles[k].timestamp
                                break

                        zones.append(OrderBlockZone(
                            symbol=symbol,
                            block_type="BULLISH",
                            start_time=ob_candle.timestamp,
                            top_price=round(top, 2),
                            bottom_price=round(bottom, 2),
                            invalidation_price=round(inval, 2),
                            is_mitigated=is_mitigated,
                            mitigation_timestamp=mitigation_ts
                        ))

            # Bearish Order Block Check
            # Current candle drops downward and closes below prior swing low
            elif curr.close < curr.open and curr.close < prev_low:
                # Find the last up-candle (bullish candle: close > open) before the impulse
                ob_candle: Optional[Candle5m] = None
                for j in range(i - 1, max(-1, i - 4), -1):
                    if candles[j].close > candles[j].open:
                        ob_candle = candles[j]
                        break

                if ob_candle:
                    key = ("BEARISH", ob_candle.timestamp)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        top = ob_candle.high
                        bottom = ob_candle.low
                        inval = top
                        
                        # Evaluate mitigation across subsequent bars
                        is_mitigated = False
                        mitigation_ts: Optional[datetime] = None
                        ob_idx = candles.index(ob_candle)
                        
                        for k in range(ob_idx + 1, len(candles)):
                            # Invalidation occurs when a 5-minute bar closes above R1 (inval)
                            if candles[k].close > inval:
                                is_mitigated = True
                                mitigation_ts = candles[k].timestamp
                                break

                        zones.append(OrderBlockZone(
                            symbol=symbol,
                            block_type="BEARISH",
                            start_time=ob_candle.timestamp,
                            top_price=round(top, 2),
                            bottom_price=round(bottom, 2),
                            invalidation_price=round(inval, 2),
                            is_mitigated=is_mitigated,
                            mitigation_timestamp=mitigation_ts
                        ))

        # Sort zones chronologically by start_time
        zones.sort(key=lambda z: z.start_time)
        return zones

    def detect_zones_from_df(self, symbol: str, df: Any) -> List[OrderBlockZone]:
        """Convert a pandas DataFrame of 5-minute candles into Candle5m and detect zones."""
        if df is None or len(df) == 0:
            return []

        candles: List[Candle5m] = []
        for _, row in df.iterrows():
            ts = row.get("timestamp")
            if hasattr(ts, "to_pydatetime"):
                ts = ts.to_pydatetime()
            if hasattr(ts, "tzinfo") and ts.tzinfo is None:
                ts = IST.localize(ts)
            candles.append(Candle5m(
                timestamp=ts,
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row.get("volume", 0))
            ))

        return self.detect_zones(symbol, candles)
