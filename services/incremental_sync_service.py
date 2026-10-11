import datetime
import logging
from typing import List, Optional

from config.settings import get_settings
from core.exceptions import AuthenticationExpiredError
from core.interfaces import IAuthService, ICandleWriter, ICheckpointRepository, IMarketDataProvider, ISymbolRepository
from core.rate_governor import LANE_SYNC
from db.repositories.duckdb_candle_repo import DuckDBCandleRepo
from db.repositories.duckdb_checkpoint_repo import DuckDBCheckpointRepo
from db.repositories.duckdb_symbol_repo import DuckDBSymbolRepo
from services.fyers_client import FyersMarketDataProvider

logger = logging.getLogger(__name__)

class IncrementalSyncService:
    """Incremental daily synchronization engine running over RateGovernor Lane 2."""
    
    def __init__(
        self,
        market_data_provider: Optional[IMarketDataProvider] = None,
        candle_writer: Optional[ICandleWriter] = None,
        checkpoint_repo: Optional[ICheckpointRepository] = None,
        symbol_repo: Optional[ISymbolRepository] = None,
    ):
        self.market_data_provider = market_data_provider or FyersMarketDataProvider()
        self.candle_writer = candle_writer or DuckDBCandleRepo()
        self.checkpoint_repo = checkpoint_repo or DuckDBCheckpointRepo()
        self.symbol_repo = symbol_repo or DuckDBSymbolRepo()
        
    def sync_daily_delta(self, symbols: List[str]) -> dict:
        """Executes batched transaction writes for daily incremental updates."""
        stats = {
            "symbols_processed": 0,
            "symbols_failed": 0,
            "total_candles_ingested": 0
        }
        
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        
        for symbol in symbols:
            success = True
            for timeframe in ["1D", "1m"]:
                try:
                    inserted = self._sync_symbol_timeframe(symbol, timeframe, today_str)
                    stats["total_candles_ingested"] += inserted
                except AuthenticationExpiredError:
                    # Bubble up immediately so scheduler can handle it
                    raise
                except Exception as e:
                    logger.error(f"Error syncing {symbol} {timeframe}: {e}")
                    success = False
            
            if success:
                stats["symbols_processed"] += 1
            else:
                stats["symbols_failed"] += 1
                
        return stats
        
    def _sync_symbol_timeframe(self, symbol: str, timeframe: str, today_str: str) -> int:
        cp = self.checkpoint_repo.get_checkpoint(symbol, timeframe)
        if not cp or cp.latest_ts is None:
            # If no history exists, skip incremental. Needs historical backfill.
            return 0
            
        latest = cp.latest_ts
        if isinstance(latest, datetime.datetime):
            range_from = latest.date().strftime("%Y-%m-%d")
        else:
            range_from = latest.strftime("%Y-%m-%d")
            
        candles = self.market_data_provider.fetch_candles(
            symbol=symbol,
            resolution=timeframe,
            range_from=range_from,
            range_to=today_str,
            priority_lane=LANE_SYNC
        )
        
        if not candles:
            return 0
            
        if timeframe == "1m":
            inserted = self.candle_writer.batch_insert_1m(candles)
            timestamps = [c["timestamp"] for c in candles]
            max_ts = datetime.datetime.fromtimestamp(max(timestamps), tz=datetime.timezone.utc)
            if cp.latest_ts is not None and isinstance(cp.latest_ts, datetime.date) and not isinstance(cp.latest_ts, datetime.datetime):
                cp.latest_ts = datetime.datetime.combine(cp.latest_ts, datetime.time.min, tzinfo=datetime.timezone.utc)
            elif cp.latest_ts is not None and getattr(cp.latest_ts, 'tzinfo', None) is None:
                cp.latest_ts = cp.latest_ts.replace(tzinfo=datetime.timezone.utc)

        else:
            inserted = self.candle_writer.batch_insert_1d(candles)
            dates = [datetime.date.fromisoformat(c["date"]) if isinstance(c["date"], str) else c["date"] for c in candles]
            max_ts = max(dates)
            
        if inserted > 0:
            if cp.latest_ts is None or max_ts > cp.latest_ts:
                cp.latest_ts = max_ts

                
            cp.total_candles += inserted
            cp.status = "COMPLETED"
            cp.last_attempt_at = datetime.datetime.utcnow()
            self.checkpoint_repo.update_checkpoint(cp)
            
        return inserted
