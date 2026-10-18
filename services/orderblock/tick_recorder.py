"""Fyers WebSocket Tick Recorder Daemon.
Continuous background service inside FastAPI lifespan accumulating live tick-delta
volume into in-memory profiles and flushing to DuckDB every 10 seconds.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, date
import logging
import threading
from typing import Any, Dict, List, Optional

import pytz

from config.settings import Settings, get_settings
from db.connection import DuckDBConnectionManager, get_db
from services.orderblock.profile_engine import VolumeProfileEngine, VolumeProfile, ProfileBucket

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")


@dataclass
class StockProfileBuffer:
    """Thread-safe in-memory buffer accumulating volume profile for an active symbol."""
    symbol: str
    trade_date: str
    day_low: float
    day_high: float
    current_price: float
    prev_total_volume: int = 0
    bucket_volumes: Dict[int, int] = field(default_factory=lambda: {i: 0 for i in range(40)})
    is_dirty: bool = False
    last_tick_time: Optional[datetime] = None


class FyersTickRecorder:
    """Live WebSocket tick recorder daemon and in-memory volume profile accumulator."""

    def __init__(
        self,
        db_manager: Optional[DuckDBConnectionManager] = None,
        flush_interval_sec: float = 10.0,
        profile_engine: Optional[VolumeProfileEngine] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.db = db_manager or get_db()
        self.flush_interval_sec = flush_interval_sec
        self.profile_engine = profile_engine or VolumeProfileEngine(num_buckets=40)
        self.settings = settings or get_settings()

        self._lock = threading.RLock()
        self._profiles: Dict[str, StockProfileBuffer] = {}
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None
        self._socket = None

    def get_buffer(self, symbol: str) -> Optional[StockProfileBuffer]:
        """Accesses in-memory buffer for a symbol."""
        with self._lock:
            return self._profiles.get(symbol)

    def handle_tick(
        self,
        symbol: str,
        ltp: float,
        total_volume_traded: int,
        day_low: Optional[float] = None,
        day_high: Optional[float] = None,
    ) -> None:
        """Processes an incoming tick update and increments corresponding price bucket.
        
        Calculates cumulative delta:
        delta_v = max(0, total_volume_traded - prev_total_volume)
        """
        now = datetime.now(IST)
        today_str = now.strftime("%Y-%m-%d")

        with self._lock:
            buf = self._profiles.get(symbol)
            if buf is None:
                # Initialize new symbol profile buffer
                d_low = day_low if day_low is not None else ltp
                d_high = day_high if day_high is not None else ltp
                buf = StockProfileBuffer(
                    symbol=symbol,
                    trade_date=today_str,
                    day_low=d_low,
                    day_high=d_high,
                    current_price=ltp,
                    prev_total_volume=total_volume_traded,
                    bucket_volumes={i: 0 for i in range(40)},
                    is_dirty=False,
                    last_tick_time=now,
                )
                self._profiles[symbol] = buf
                return

            # Update day extremes and live price
            if day_low is not None:
                buf.day_low = min(buf.day_low, day_low, ltp)
            else:
                buf.day_low = min(buf.day_low, ltp)

            if day_high is not None:
                buf.day_high = max(buf.day_high, day_high, ltp)
            else:
                buf.day_high = max(buf.day_high, ltp)

            buf.current_price = ltp
            buf.last_tick_time = now

            # Volume delta calculation
            if buf.prev_total_volume > 0 and total_volume_traded > buf.prev_total_volume:
                delta_v = total_volume_traded - buf.prev_total_volume
                b_idx = self.profile_engine.get_bucket_index(
                    ltp, buf.day_low, buf.day_high, num_buckets=40
                )
                buf.bucket_volumes[b_idx] += delta_v
                buf.is_dirty = True

            buf.prev_total_volume = total_volume_traded

    def _on_message(self, message: Any) -> None:
        """Callback for Fyers WebSocket incoming tick messages."""
        if not isinstance(message, dict):
            return

        symbol = message.get("symbol")
        ltp = message.get("ltp")
        if not symbol or ltp is None:
            return

        vol = message.get("vol_traded_today") or message.get("vtt") or message.get("volume") or 0
        h = message.get("high_price") or message.get("high")
        l = message.get("low_price") or message.get("low")

        self.handle_tick(
            symbol=symbol,
            ltp=float(ltp),
            total_volume_traded=int(vol),
            day_low=float(l) if l is not None else None,
            day_high=float(h) if h is not None else None,
        )

    def _on_error(self, message: Any) -> None:
        logger.warning("Fyers WebSocket error: %s", message)

    def _on_close(self, message: Any) -> None:
        logger.info("Fyers WebSocket closed: %s", message)

    def on_reconnect(self) -> None:
        """Preserves in-memory state during socket reconnection."""
        logger.info("Fyers WebSocket reconnected. Retaining %d in-memory symbol profiles.", len(self._profiles))

    async def flush_dirty_profiles(self) -> None:
        """Flushes all dirty in-memory symbol profiles to DuckDB volume_profile_buckets table."""
        dirty_profiles: List[VolumeProfile] = []
        with self._lock:
            for buf in self._profiles.values():
                if buf.is_dirty:
                    p = self.profile_engine.build_profile(
                        symbol=buf.symbol,
                        trade_date=buf.trade_date,
                        day_low=buf.day_low,
                        day_high=buf.day_high,
                        current_price=buf.current_price,
                        bucket_volumes=buf.bucket_volumes,
                        num_buckets=40,
                    )
                    dirty_profiles.append(p)
                    buf.is_dirty = False

        if not dirty_profiles:
            return

        # Perform batched write to DuckDB
        for profile in dirty_profiles:
            try:
                self.profile_engine.persist_profile_buckets(profile, manager=self.db)
            except Exception as e:
                logger.error("Failed persisting volume profile for %s: %s", profile.symbol, e)

    async def _flush_loop(self) -> None:
        """Periodic background flush loop running every flush_interval_sec."""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval_sec)
                await self.flush_dirty_profiles()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Exception in tick recorder flush loop: %s", e)

    def get_profile(self, symbol: str, trade_date: Optional[str] = None) -> Optional[VolumeProfile]:
        """Retrieves volume profile for a symbol.
        Checks in-memory accumulator first, then falls back to DuckDB table.
        """
        today_str = trade_date or datetime.now(IST).strftime("%Y-%m-%d")

        with self._lock:
            buf = self._profiles.get(symbol)
            if buf is not None and buf.trade_date == today_str:
                return self.profile_engine.build_profile(
                    symbol=buf.symbol,
                    trade_date=buf.trade_date,
                    day_low=buf.day_low,
                    day_high=buf.day_high,
                    current_price=buf.current_price,
                    bucket_volumes=buf.bucket_volumes,
                    num_buckets=40,
                )

        # Fallback to DuckDB
        db_buckets = self.profile_engine.load_profile_buckets(symbol, today_str, manager=self.db)
        if not db_buckets:
            return None

        # Reconstruct bounds from DuckDB table
        cursor = self.db.get_read_cursor()
        try:
            row = cursor.execute(
                """
                SELECT MIN(price_low), MAX(price_high)
                FROM volume_profile_buckets
                WHERE symbol = ? AND trade_date = ?
                """,
                [symbol, today_str],
            ).fetchone()
            d_low = float(row[0]) if row and row[0] is not None else 0.0
            d_high = float(row[1]) if row and row[1] is not None else d_low
            return self.profile_engine.build_profile(
                symbol=symbol,
                trade_date=today_str,
                day_low=d_low,
                day_high=d_high,
                current_price=d_high,
                bucket_volumes=db_buckets,
                num_buckets=40,
            )
        except Exception as e:
            logger.debug("Error reconstructing profile bounds from volume_profile_buckets: %s", e)
            return None
        finally:
            cursor.close()

    def get_mini_profile(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Provides compact 40-element width array and POC for dashboard contender cards."""
        profile = self.get_profile(symbol)
        if profile is None or not profile.buckets:
            return None

        curr_bucket_idx = self.profile_engine.get_bucket_index(
            profile.current_price, profile.day_low, profile.day_high, num_buckets=40
        )

        return {
            "poc_price": profile.poc_price,
            "poc_width_pct": 100.0 if profile.poc_volume > 0 else 0.0,
            "current_bucket_idx": curr_bucket_idx,
            "mini_buckets": [b.width_pct for b in profile.buckets],
        }

    async def start(self) -> None:
        """Starts the background flush loop and initializes live Fyers WebSocket if configured."""
        if self._running:
            return
        self._running = True

        # Launch periodic flush worker
        loop = asyncio.get_running_loop()
        self._flush_task = loop.create_task(self._flush_loop())
        logger.info("FyersTickRecorder flush loop started (interval=%0.1fs).", self.flush_interval_sec)

        # Connect WebSocket if credentials are valid
        try:
            from services.auth_service import AuthService
            auth_service = AuthService(settings=self.settings)
            token = auth_service.get_valid_token()
            app_id = self.settings.FYERS_APP_ID

            if token and app_id:
                access_token = f"{app_id}:{token}"
                try:
                    from fyers_apiv3.FyersWebsocket.data_ws import FyersDataSocket
                except ImportError:
                    from fyers_apiv3.FyersDataSocket import FyersDataSocket

                self._socket = FyersDataSocket(
                    access_token=access_token,
                    write_to_file=False,
                    litemode=False,
                    reconnect=True,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                logger.info("FyersDataSocket initialized for tick recording.")
        except Exception as exc:
            logger.info("Fyers live socket not active (offline/unauthenticated mode): %s", exc)

    async def stop(self) -> None:
        """Gracefully halts recorder, disconnects socket, and commits remaining buffer state."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        if self._socket:
            try:
                self._socket.close_connection()
            except Exception as e:
                logger.debug("Error closing FyersDataSocket: %s", e)
            self._socket = None

        # Final flush to persist remaining dirty records
        await self.flush_dirty_profiles()
        logger.info("FyersTickRecorder stopped cleanly.")


_GLOBAL_TICK_RECORDER: Optional[FyersTickRecorder] = None
_RECORDER_LOCK = threading.Lock()


def get_tick_recorder(db_manager: Optional[DuckDBConnectionManager] = None) -> FyersTickRecorder:
    """Access the global singleton FyersTickRecorder instance."""
    global _GLOBAL_TICK_RECORDER
    with _RECORDER_LOCK:
        if _GLOBAL_TICK_RECORDER is None:
            _GLOBAL_TICK_RECORDER = FyersTickRecorder(db_manager=db_manager)
        return _GLOBAL_TICK_RECORDER
