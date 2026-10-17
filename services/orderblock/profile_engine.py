"""OrderBlock In-Tile Volume Profile Engine.
Implements 40-bucket dynamic range division, delta volume aggregation,
Point of Control (POC) detection, relative peak normalization, and DuckDB persistence.
"""

from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Dict, List, Optional, Sequence, Tuple

from db.connection import DuckDBConnectionManager, get_db

logger = logging.getLogger(__name__)


@dataclass
class ProfileBucket:
    """Represents a single price bucket within an intraday volume profile."""
    index: int
    price_low: float
    price_high: float
    volume: int
    width_pct: float
    is_poc: bool
    side: str  # 'SUPPORT' or 'RESISTANCE'


@dataclass
class VolumeProfile:
    """Represents the complete 40-bucket intraday volume profile for a symbol."""
    symbol: str
    trade_date: str
    day_low: float
    day_high: float
    current_price: float
    poc_price: float
    poc_volume: int
    buckets: List[ProfileBucket] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serializes the profile for JSON API responses."""
        return {
            "symbol": self.symbol,
            "trade_date": self.trade_date,
            "day_low": self.day_low,
            "day_high": self.day_high,
            "current_price": self.current_price,
            "poc_price": self.poc_price,
            "poc_volume": self.poc_volume,
            "buckets": [
                {
                    "index": b.index,
                    "price_low": b.price_low,
                    "price_high": b.price_high,
                    "volume": b.volume,
                    "width_pct": b.width_pct,
                    "is_poc": b.is_poc,
                    "side": b.side,
                }
                for b in self.buckets
            ],
        }


class VolumeProfileEngine:
    """Core mathematical engine for Volume Profile computation."""

    def __init__(self, num_buckets: int = 40) -> None:
        self.num_buckets = num_buckets

    def calculate_bucket_bounds(
        self, day_low: float, day_high: float, num_buckets: Optional[int] = None
    ) -> List[Tuple[float, float]]:
        """Divides [day_low, day_high] into uniform price buckets.
        
        Handles flat ranges (e.g., initial tick where day_low == day_high) gracefully.
        """
        n = num_buckets or self.num_buckets
        if day_high <= day_low:
            # Fallback to tick-size bands centered around day_low
            tick_size = 0.05
            base = day_low - (n / 2) * tick_size
            return [
                (round(base + i * tick_size, 4), round(base + (i + 1) * tick_size, 4))
                for i in range(n)
            ]

        width = (day_high - day_low) / n
        bounds: List[Tuple[float, float]] = []
        for i in range(n):
            b_low = day_low + i * width
            b_high = day_high if i == n - 1 else day_low + (i + 1) * width
            bounds.append((round(b_low, 4), round(b_high, 4)))
        return bounds

    def get_bucket_index(
        self, price: float, day_low: float, day_high: float, num_buckets: Optional[int] = None
    ) -> int:
        """Determines the zero-indexed bucket index corresponding to a price point."""
        n = num_buckets or self.num_buckets
        if day_high <= day_low:
            return 0
        if price <= day_low:
            return 0
        if price >= day_high:
            return n - 1

        width = (day_high - day_low) / n
        idx = int((price - day_low) / width)
        return min(max(0, idx), n - 1)

    def accumulate_tick(
        self,
        symbol: str,
        ltp: float,
        total_volume_traded: int,
        prev_total_volume: int,
        day_low: float,
        day_high: float,
        num_buckets: Optional[int] = None,
    ) -> Tuple[int, int]:
        """Calculates volume delta from live tick and identifies target bucket.
        
        Returns:
            Tuple[bucket_index, delta_volume]
        """
        delta_v = max(0, total_volume_traded - prev_total_volume)
        b_idx = self.get_bucket_index(ltp, day_low, day_high, num_buckets)
        return b_idx, delta_v

    def build_profile(
        self,
        symbol: str,
        trade_date: str,
        day_low: float,
        day_high: float,
        current_price: float,
        bucket_volumes: Dict[int, int],
        num_buckets: Optional[int] = None,
    ) -> VolumeProfile:
        """Constructs a normalized VolumeProfile with Point of Control (POC) and relative scaling."""
        n = num_buckets or self.num_buckets
        bounds = self.calculate_bucket_bounds(day_low, day_high, n)

        # Identify POC (highest volume bucket)
        max_vol = 0
        poc_idx = 0
        for i in range(n):
            vol = bucket_volumes.get(i, 0)
            if vol > max_vol:
                max_vol = vol
                poc_idx = i

        buckets: List[ProfileBucket] = []
        for i in range(n):
            b_low, b_high = bounds[i]
            vol = bucket_volumes.get(i, 0)
            is_poc = (i == poc_idx and max_vol > 0)
            width_pct = round((vol / max_vol) * 100.0, 2) if max_vol > 0 else 0.0
            
            # SUPPORT if bucket max price <= current_price, else RESISTANCE
            side = "SUPPORT" if b_high <= current_price else "RESISTANCE"

            buckets.append(
                ProfileBucket(
                    index=i,
                    price_low=b_low,
                    price_high=b_high,
                    volume=vol,
                    width_pct=width_pct,
                    is_poc=is_poc,
                    side=side,
                )
            )

        poc_bounds = bounds[poc_idx]
        poc_price = round((poc_bounds[0] + poc_bounds[1]) / 2.0, 4)

        return VolumeProfile(
            symbol=symbol,
            trade_date=trade_date,
            day_low=day_low,
            day_high=day_high,
            current_price=current_price,
            poc_price=poc_price,
            poc_volume=max_vol,
            buckets=buckets,
        )

    def persist_profile_buckets(
        self,
        profile: VolumeProfile,
        manager: Optional[DuckDBConnectionManager] = None,
    ) -> None:
        """Flushes volume profile buckets to DuckDB under single-writer lock."""
        db = manager or get_db()

        def _write_buckets(conn):
            # Batch upsert into volume_profile_buckets
            for b in profile.buckets:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO volume_profile_buckets (
                        symbol, trade_date, bucket_index, price_low, price_high, volume, last_updated
                    )
                    VALUES (?, ?, ?, ?, ?, ?, now())
                    """,
                    [
                        profile.symbol,
                        profile.trade_date,
                        b.index,
                        b.price_low,
                        b.price_high,
                        b.volume,
                    ],
                )

        db.execute_write_batch(_write_buckets)

    def load_profile_buckets(
        self,
        symbol: str,
        trade_date: str,
        manager: Optional[DuckDBConnectionManager] = None,
    ) -> Dict[int, int]:
        """Loads accumulated bucket volumes from DuckDB using a read-only cursor."""
        db = manager or get_db()
        cursor = db.get_read_cursor()
        try:
            rows = cursor.execute(
                """
                SELECT bucket_index, volume
                FROM volume_profile_buckets
                WHERE symbol = ? AND trade_date = ?
                ORDER BY bucket_index ASC
                """,
                [symbol, trade_date],
            ).fetchall()
            return {row[0]: int(row[1]) for row in rows}
        finally:
            cursor.close()
