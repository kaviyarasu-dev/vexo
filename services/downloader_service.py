"""Historical Downloader Service, Checkpointing State Machine & Resumption Walk.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md and plan/04_HISTORICAL_DOWNLOADER_ENGINE.md.
"""

from datetime import date, datetime, timedelta
import logging
import signal
import threading
import time
from typing import Any, Dict, List, Optional, Sequence, Union

from config.settings import Settings, get_settings
from core.exceptions import AuthenticationExpiredError, FyersAPIError
from core.interfaces import (
    Checkpoint,
    ICandleWriter,
    ICheckpointRepository,
    IMarketDataProvider,
    ISymbolRepository,
    SymbolEntity,
)
from db.connection import DuckDBConnectionManager, get_db
from db.repositories.duckdb_candle_repo import DuckDBCandleRepo
from db.repositories.duckdb_checkpoint_repo import DuckDBCheckpointRepo
from db.repositories.duckdb_symbol_repo import DuckDBSymbolRepo
from services.chunk_generator import CalendarChunker, DateChunk
from services.fyers_client import FyersMarketDataProvider

logger = logging.getLogger(__name__)

# Fallback boundary when listing date is absent
FALLBACK_LISTING_DATE = date(2017, 1, 1)


class HistoricalDownloader:
    """Orchestrates multi-year historical ingestion with resilient checkpointing.
    
    Guarantees:
    - Zero RateGovernor bypass: all broker calls go through RateGovernor.
    - Calendar-day chunking: 100 days for 1m, 366 days for 1D.
    - End-of-history condition: ONLY when (>= 3 consecutive empty chunks) AND (chunk_start < listing_date).
    - Error -300 transient recovery without premature abort.
    - Resumable walk: Interrupted downloads resume from exact uncompleted date with zero duplicate rows.
    - Thread-safe control: start(), pause(), resume(), cancel().
    """

    def __init__(
        self,
        market_data_provider: Optional[IMarketDataProvider] = None,
        candle_writer: Optional[ICandleWriter] = None,
        checkpoint_repo: Optional[ICheckpointRepository] = None,
        symbol_repo: Optional[ISymbolRepository] = None,
        db: Optional[DuckDBConnectionManager] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.db = db or get_db()
        self.market_data_provider = market_data_provider or FyersMarketDataProvider(settings=self.settings)
        self.candle_writer = candle_writer or DuckDBCandleRepo(self.db)
        self.checkpoint_repo = checkpoint_repo or DuckDBCheckpointRepo(self.db)
        self.symbol_repo = symbol_repo or DuckDBSymbolRepo(self.db)

        # Thread controls
        self._lock = threading.RLock()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused by default
        self._stop_requested = False
        self._is_running = False

        # Live telemetry
        self._current_symbol: Optional[str] = None
        self._current_timeframe: Optional[str] = None
        self._total_candles_ingested = 0
        self._symbols_completed = 0
        self._symbols_failed = 0
        self._start_time: Optional[float] = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def is_paused(self) -> bool:
        return not self._pause_event.is_set()

    def pause(self) -> None:
        """Pauses the download loop safely before the next chunk."""
        with self._lock:
            self._pause_event.clear()
            logger.info("HistoricalDownloader: PAUSE requested.")

    def resume(self) -> None:
        """Resumes a paused download loop."""
        with self._lock:
            self._pause_event.set()
            logger.info("HistoricalDownloader: RESUME requested.")

    def cancel(self) -> None:
        """Signals graceful cancellation. Commits current in-flight chunk before halting."""
        with self._lock:
            self._stop_requested = True
            self._pause_event.set()  # Unblock if currently paused
            logger.info("HistoricalDownloader: CANCEL requested. Halting gracefully.")

    def stop(self) -> None:
        """Alias for cancel()."""
        self.cancel()

    def register_signal_handlers(self) -> None:
        """Registers SIGINT / SIGTERM handlers to cleanly flush checkpoints."""
        def _handler(signum: int, frame: Any) -> None:
            logger.warning("HistoricalDownloader: Caught signal %d. Shutting down gracefully...", signum)
            self.cancel()

        try:
            signal.signal(signal.SIGINT, _handler)
            signal.signal(signal.SIGTERM, _handler)
        except (ValueError, AttributeError):
            # Happens in non-main threads or specific environments
            pass

    def get_status(self) -> Dict[str, Any]:
        """Returns live downloader telemetry for CLI and UI monitoring."""
        with self._lock:
            elapsed = time.time() - self._start_time if self._start_time else 0.0
            speed = (self._total_candles_ingested / elapsed) if elapsed > 0 else 0.0
            return {
                "is_running": self._is_running,
                "is_paused": self.is_paused,
                "current_symbol": self._current_symbol,
                "current_timeframe": self._current_timeframe,
                "symbols_completed": self._symbols_completed,
                "symbols_failed": self._symbols_failed,
                "total_candles_ingested": self._total_candles_ingested,
                "speed_candles_per_sec": round(speed, 1),
                "elapsed_seconds": round(elapsed, 1),
            }

    def _get_symbol_listing_date(self, symbol: str) -> date:
        """Retrieves instrument listing date from symbol repo or defaults to 2017-01-01."""
        entity = self.symbol_repo.get_by_symbol(symbol)
        if entity and entity.listing_date:
            if isinstance(entity.listing_date, datetime):
                return entity.listing_date.date()
            if isinstance(entity.listing_date, date):
                return entity.listing_date
            if isinstance(entity.listing_date, str):
                try:
                    return datetime.strptime(entity.listing_date.strip(), "%Y-%m-%d").date()
                except ValueError:
                    pass
        return FALLBACK_LISTING_DATE

    def download_symbol(
        self,
        symbol: str,
        timeframe: str,
        target_years: Optional[int] = None,
        end_date: Optional[date] = None,
        force: bool = False,
    ) -> int:
        """Downloads historical data for a single symbol walking backward with state checkpointing.
        
        Args:
            symbol: Canonical ticker string.
            timeframe: '1m' or '1D'.
            target_years: Backfill depth in years (defaults to settings: 5 for 1m, 15 for 1D).
            end_date: Upper boundary date (defaults to today).
            force: Force redownload even if marked COMPLETED.
            
        Returns:
            Total new candles inserted for this symbol.
        """
        if target_years is None:
            target_years = (
                self.settings.DEFAULT_1M_HISTORY_YEARS
                if timeframe == "1m"
                else self.settings.DEFAULT_1D_HISTORY_YEARS
            )

        end_boundary = end_date or date.today()
        target_start = end_boundary - timedelta(days=int(target_years * 365.25))

        # Check existing checkpoint
        cp = self.checkpoint_repo.get_checkpoint(symbol, timeframe)
        if cp is None:
            cp = Checkpoint(
                symbol=symbol,
                timeframe=timeframe,
                status="PENDING",
                consecutive_empty_count=0,
                total_candles=0,
            )

        if force:
            logger.info("HistoricalDownloader: Force redownload requested for %s (%s). Resetting checkpoint.", symbol, timeframe)
            cp.status = "PENDING"
            cp.error_message = None
            cp.consecutive_empty_count = 0
            cp.earliest_ts = None
            self.checkpoint_repo.update_checkpoint(cp)
        elif cp.status == "COMPLETED":
            # If previously marked COMPLETED with 0 candles and an error, auto-reset to retry
            if cp.total_candles == 0 and cp.error_message:
                logger.warning(
                    "HistoricalDownloader: %s (%s) was marked COMPLETED with error '%s' and 0 candles. Resetting to PENDING.",
                    symbol, timeframe, cp.error_message,
                )
                cp.status = "PENDING"
                cp.error_message = None
                cp.consecutive_empty_count = 0
                cp.earliest_ts = None
                self.checkpoint_repo.update_checkpoint(cp)
            else:
                logger.info("HistoricalDownloader: %s (%s) already COMPLETED. Skipping.", symbol, timeframe)
                return 0

        listing_date = self._get_symbol_listing_date(symbol)
        total_new_candles = 0

        # Resumption logic: If already in progress, start backward from earliest_ts
        current_walk_to = end_boundary
        if cp.status == "IN_PROGRESS" and cp.earliest_ts is not None:
            resume_dt = cp.earliest_ts.date() if isinstance(cp.earliest_ts, datetime) else cp.earliest_ts
            current_walk_to = resume_dt - timedelta(days=1)
            logger.info(
                "HistoricalDownloader: Resuming %s (%s) from %s backward.",
                symbol, timeframe, current_walk_to
            )

        # Generate chunks walking backward
        chunks = CalendarChunker.generate_backward_chunks(
            symbol=symbol,
            timeframe=timeframe,
            start_date=target_start,
            end_date=current_walk_to,
        )

        if not chunks:
            # Reached boundary
            cp.status = "COMPLETED"
            cp.last_attempt_at = datetime.utcnow()
            self.checkpoint_repo.update_checkpoint(cp)
            return 0

        # Mark checkpoint IN_PROGRESS
        cp.status = "IN_PROGRESS"
        cp.last_attempt_at = datetime.utcnow()
        self.checkpoint_repo.update_checkpoint(cp)

        for chunk in chunks:
            # Respect pause / stop toggles
            self._pause_event.wait()
            if self._stop_requested:
                logger.info("HistoricalDownloader: Halting on stop request for %s", symbol)
                break

            logger.debug(
                "Downloading chunk for %s (%s): %s to %s (calendar days: %d)",
                symbol, timeframe, chunk.range_from_str, chunk.range_to_str, chunk.calendar_days
            )

            try:
                candles = self.market_data_provider.fetch_candles(
                    symbol=symbol,
                    resolution=timeframe,
                    range_from=chunk.range_from_str,
                    range_to=chunk.range_to_str,
                )
            except AuthenticationExpiredError:
                cp.status = "FAILED"
                cp.error_message = "Authentication expired during backfill"
                cp.last_attempt_at = datetime.utcnow()
                self.checkpoint_repo.update_checkpoint(cp)
                raise
            except Exception as exc:
                logger.error("Error fetching candles for %s chunk %s-%s: %s", symbol, chunk.range_from_str, chunk.range_to_str, exc)
                cp.last_attempt_at = datetime.utcnow()
                cp.error_message = str(exc)
                self.checkpoint_repo.update_checkpoint(cp)
                continue

            if candles and len(candles) > 0:
                # Reset consecutive empty counter
                cp.consecutive_empty_count = 0

                # Batch insert with staging + anti-join deduplication
                if timeframe == "1m":
                    inserted = self.candle_writer.batch_insert_1m(candles)
                    timestamps = [c["timestamp"] for c in candles]
                    min_ts = min(timestamps)
                    max_ts = max(timestamps)
                else:
                    inserted = self.candle_writer.batch_insert_1d(candles)
                    dates = [c["date"] for c in candles]
                    min_ts = datetime.combine(min(dates), datetime.min.time())
                    max_ts = datetime.combine(max(dates), datetime.min.time())

                total_new_candles += inserted
                self._total_candles_ingested += inserted

                # Update checkpoint timestamps
                if cp.earliest_ts is None or min_ts < cp.earliest_ts:
                    cp.earliest_ts = min_ts
                if cp.latest_ts is None or max_ts > cp.latest_ts:
                    cp.latest_ts = max_ts

                cp.total_candles += inserted
                cp.last_attempt_at = datetime.utcnow()
                self.checkpoint_repo.update_checkpoint(cp)

            else:
                # Empty response
                cp.consecutive_empty_count += 1
                cp.last_attempt_at = datetime.utcnow()
                self.checkpoint_repo.update_checkpoint(cp)

                # End-of-history check: ONLY when (>= 3 consecutive empty chunks) AND (chunk_start < listing_date)
                if cp.consecutive_empty_count >= 3 and chunk.range_from < listing_date:
                    logger.info(
                        "HistoricalDownloader: End-of-history reached for %s (%s). "
                        "Consecutive empty: %d, chunk_from: %s < listing_date: %s. Marking COMPLETED.",
                        symbol, timeframe, cp.consecutive_empty_count, chunk.range_from_str, listing_date
                    )
                    cp.status = "COMPLETED"
                    self.checkpoint_repo.update_checkpoint(cp)
                    break
                else:
                    logger.debug(
                        "Empty chunk for %s (%s to %s). Consecutive empty: %d (listing_date: %s). Continuing.",
                        symbol, chunk.range_from_str, chunk.range_to_str, cp.consecutive_empty_count, listing_date
                    )

        # Mark COMPLETED if all chunks finished without interrupt
        if not self._stop_requested and cp.status != "COMPLETED":
            if cp.error_message and cp.total_candles == 0:
                cp.status = "FAILED"
            else:
                cp.status = "COMPLETED"
            cp.last_attempt_at = datetime.utcnow()
            self.checkpoint_repo.update_checkpoint(cp)

        return total_new_candles

    def run_backfill(
        self,
        timeframe: str,
        tiers: Optional[Sequence[int]] = None,
        symbols: Optional[Sequence[str]] = None,
        target_years: Optional[int] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Runs the historical backfill process across all targeted instruments.
        
        Args:
            timeframe: '1m' or '1D'.
            tiers: List of tiers to backfill (e.g. [1, 2, 3] for Nifty 500 in 1m).
            symbols: Optional explicit list of symbols.
            target_years: Target history depth in years.
            force: Force redownload even if marked COMPLETED.
            
        Returns:
            Summary report dictionary.
        """
        with self._lock:
            self._is_running = True
            self._stop_requested = False
            self._start_time = time.time()
            self._total_candles_ingested = 0
            self._symbols_completed = 0
            self._symbols_failed = 0
            self._current_timeframe = timeframe

        try:
            # Determine symbols list
            target_symbol_list: List[str] = []
            if symbols:
                target_symbol_list = list(symbols)
            elif tiers:
                for t in tiers:
                    tier_symbols = self.checkpoint_repo.list_pending_symbols(timeframe=timeframe, tier=t)
                    target_symbol_list.extend(tier_symbols)
            else:
                # All pending symbols for this timeframe
                target_symbol_list = self.checkpoint_repo.list_pending_symbols(timeframe=timeframe)

            # Deduplicate preserving order
            seen = set()
            ordered_symbols = []
            for s in target_symbol_list:
                if s not in seen:
                    seen.add(s)
                    ordered_symbols.append(s)

            logger.info(
                "HistoricalDownloader: Starting %s backfill for %d symbols (force=%s).",
                timeframe, len(ordered_symbols), force
            )

            for sym in ordered_symbols:
                if self._stop_requested:
                    logger.info("HistoricalDownloader: Backfill interrupted by user request.")
                    break

                with self._lock:
                    self._current_symbol = sym

                try:
                    self.download_symbol(sym, timeframe=timeframe, target_years=target_years, force=force)
                    with self._lock:
                        self._symbols_completed += 1
                except AuthenticationExpiredError:
                    with self._lock:
                        self._symbols_failed += 1
                    logger.critical("HistoricalDownloader: Terminating backfill due to expired authentication.")
                    raise
                except Exception as exc:
                    with self._lock:
                        self._symbols_failed += 1
                    logger.error("HistoricalDownloader: Symbol %s failed: %s", sym, exc)
                    continue

        finally:
            with self._lock:
                self._is_running = False
                self._current_symbol = None

        return self.get_status()
