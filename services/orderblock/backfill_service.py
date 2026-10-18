"""OrderBlock Late-Start Hybrid Backfill Service.
Reconstructs intraday volume profiles from 1-minute historical candles upon mid-session launch
by uniformly spreading candle volume across overlapping price buckets with exact volume conservation.
"""

from datetime import datetime, date
import logging
from typing import Any, Dict, List, Optional, Tuple

from db.connection import DuckDBConnectionManager, get_db
from services.orderblock.profile_engine import VolumeProfileEngine, VolumeProfile

logger = logging.getLogger(__name__)


class VolumeProfileBackfillService:
    """Service to reconstruct intraday volume distribution from 1-minute candle history."""

    def __init__(self, profile_engine: Optional[VolumeProfileEngine] = None) -> None:
        self.profile_engine = profile_engine or VolumeProfileEngine(num_buckets=40)

    def backfill_from_1m_candles(
        self,
        symbol: str,
        trade_date: str,
        day_low: float,
        day_high: float,
        candles_1m: List[Dict[str, Any]],
        num_buckets: int = 40,
    ) -> Dict[int, int]:
        """Spreads 1-minute candle volumes uniformly across overlapping price buckets.
        
        Guarantees exact volume conservation:
        sum(returned_buckets.values()) == sum(candle["volume"] for candle in candles_1m)
        """
        bucket_volumes: Dict[int, int] = {i: 0 for i in range(num_buckets)}

        if not candles_1m:
            return bucket_volumes

        for candle in candles_1m:
            vol = int(candle.get("volume", 0))
            if vol <= 0:
                continue

            c_low = float(candle.get("low", 0.0))
            c_high = float(candle.get("high", c_low))

            # Determine overlapping bucket range. If c_high > c_low, use infinitesimal offset
            # so an exact boundary high (e.g. 115.0 on [114, 115]) belongs to the candle's span
            c_high_eval = max(c_low, c_high - 1e-9) if c_high > c_low else c_high
            start_idx = self.profile_engine.get_bucket_index(c_low, day_low, day_high, num_buckets)
            end_idx = self.profile_engine.get_bucket_index(c_high_eval, day_low, day_high, num_buckets)

            if start_idx > end_idx:
                start_idx, end_idx = end_idx, start_idx

            k = end_idx - start_idx + 1
            base_vol = vol // k
            remainder = vol % k

            for offset, b_idx in enumerate(range(start_idx, end_idx + 1)):
                allocated = base_vol + (1 if offset < remainder else 0)
                bucket_volumes[b_idx] += allocated

        return bucket_volumes

    def backfill_from_db_candles(
        self,
        symbol: str,
        trade_date: str,
        manager: Optional[DuckDBConnectionManager] = None,
        num_buckets: int = 40,
    ) -> Optional[VolumeProfile]:
        """Queries 1-minute candles for the symbol and trade date from DuckDB,
        computes the backfilled volume profile, and persists the buckets.
        """
        db = manager or get_db()
        cursor = db.get_read_cursor()
        try:
            # Query 1m candles for given symbol and date
            rows = cursor.execute(
                """
                SELECT open, high, low, close, volume, timestamp
                FROM candles_1m_raw
                WHERE symbol = ? AND CAST(timestamp AS DATE) = CAST(? AS DATE)
                ORDER BY timestamp ASC
                """,
                [symbol, trade_date],
            ).fetchall()

            if not rows:
                return None

            candles = [
                {
                    "open": float(r[0]),
                    "high": float(r[1]),
                    "low": float(r[2]),
                    "close": float(r[3]),
                    "volume": int(r[4]),
                }
                for r in rows
            ]

            day_low = min(c["low"] for c in candles)
            day_high = max(c["high"] for c in candles)
            current_price = candles[-1]["close"]

            bucket_vols = self.backfill_from_1m_candles(
                symbol=symbol,
                trade_date=trade_date,
                day_low=day_low,
                day_high=day_high,
                candles_1m=candles,
                num_buckets=num_buckets,
            )

            profile = self.profile_engine.build_profile(
                symbol=symbol,
                trade_date=trade_date,
                day_low=day_low,
                day_high=day_high,
                current_price=current_price,
                bucket_volumes=bucket_vols,
                num_buckets=num_buckets,
            )

            # Persist backfilled profile to DuckDB
            self.profile_engine.persist_profile_buckets(profile, manager=db)
            return profile

        except Exception as e:
            logger.error("Failed backfilling volume profile for %s on %s: %s", symbol, trade_date, e)
            return None
        finally:
            cursor.close()
