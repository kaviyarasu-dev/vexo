import datetime
import pytest
from core.interfaces import IMarketDataProvider, ICandleWriter, ICheckpointRepository, Checkpoint
from services.incremental_sync_service import IncrementalSyncService

class MockMarketData(IMarketDataProvider):
    def fetch_candles(self, symbol, resolution, range_from, range_to, priority_lane):
        return [{"timestamp": 1705973400, "date": datetime.date(2024, 1, 23), "open": 100, "high": 105, "low": 95, "close": 102, "volume": 1000}]
    def fetch_quotes(self, symbols, priority_lane):
        return {}
    def fetch_option_chain(self, symbol, expiry, priority_lane):
        return []
        
class MockWriter(ICandleWriter):
    def __init__(self):
        self.inserts_1m = 0
        self.inserts_1d = 0
    def batch_insert_1m(self, candles):
        self.inserts_1m += len(candles)
        return len(candles)
    def batch_insert_1d(self, candles):
        self.inserts_1d += len(candles)
        return len(candles)
    def stage_and_merge_1m(self, staging_table):
        return 0
        
class MockCheckpoint(ICheckpointRepository):
    def __init__(self):
        self.updates = 0
        self.cp = Checkpoint(symbol="NSE:RELIANCE-EQ", timeframe="1D")
        self.cp.earliest_ts = None
        self.cp.latest_ts = datetime.date(2024, 1, 22)
        self.cp.total_candles = 10
        self.cp.status = "COMPLETED"
        self.cp.last_attempt_at = None
    def get_checkpoint(self, symbol, timeframe):
        return self.cp
    def update_checkpoint(self, checkpoint):
        self.updates += 1
    def list_pending_symbols(self, timeframe, tier=None):
        return []
        
class MockSymbolRepo:
    pass

def test_sync_daily_delta_contract():
    md = MockMarketData()
    writer = MockWriter()
    cp_repo = MockCheckpoint()
    
    sync_service = IncrementalSyncService(
        market_data_provider=md,
        candle_writer=writer,
        checkpoint_repo=cp_repo,
        symbol_repo=MockSymbolRepo()
    )
    
    stats = sync_service.sync_daily_delta(["NSE:RELIANCE-EQ"])
    
    assert stats["symbols_processed"] == 1
    assert writer.inserts_1m == 1
    assert writer.inserts_1d == 1
    assert cp_repo.updates == 2
