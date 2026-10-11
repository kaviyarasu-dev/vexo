import asyncio
import datetime
import pytest
from db.connection import get_db
from db.migrations import init_db
from services.scheduler_service import SchedulerService

@pytest.fixture
def test_db():
    db = get_db(":memory:", reset=True)
    init_db(manager=db)
    
    # Insert a dummy symbol
    db.execute_write(
        "INSERT INTO symbols (symbol, name, tier, is_active) VALUES (?, ?, ?, ?)",
        ["NSE:RELIANCE-EQ", "Reliance", 1, True]
    )
    
    yield db
    db.close()

class MockAuthService:
    def validate_session(self): return True
    def refresh_token_if_needed(self): return True

class MockSyncService:
    def __init__(self):
        self.calls = 0
        
    def sync_daily_delta(self, symbols):
        self.calls += 1
        return {"symbols_processed": len(symbols), "symbols_failed": 0, "total_candles_ingested": 100}

@pytest.mark.asyncio
async def test_missed_run_catchup(test_db):
    auth = MockAuthService()
    sync = MockSyncService()
    scheduler = SchedulerService(auth_service=auth, sync_service=sync)
    
    # Fake that a job completed a few days ago
    past_date = datetime.datetime(2024, 1, 18, 12, 0, 0)
    test_db.execute_write(
        "INSERT INTO job_logs (job_id, job_type, started_at, completed_at, status) VALUES (?, ?, ?, ?, ?)",
        ["job_123", "DAILY_INCREMENTAL", past_date, past_date, "COMPLETED"]
    )
    
    from unittest.mock import patch
    import pytz
    
    # We will mock the datetime module inside scheduler_service
    class MockDatetime:
        @classmethod
        def now(cls, tz=None):
            return datetime.datetime(2024, 1, 23, 18, 0, 0, tzinfo=pytz.timezone('Asia/Kolkata'))
        @classmethod
        def utcnow(cls):
            return datetime.datetime(2024, 1, 23, 12, 30, 0)
            
    # Also patch calendar to always return True for trading day
    scheduler.calendar.is_trading_day = lambda d: True
    scheduler.calendar.get_previous_trading_day = lambda d: d - datetime.timedelta(days=1)
    
    with patch('services.scheduler_service.datetime') as mock_dt:
        mock_dt.datetime = MockDatetime
        mock_dt.date.today.return_value = datetime.date(2024, 1, 23)
        mock_dt.time = datetime.time
        mock_dt.timedelta = datetime.timedelta
        await scheduler.check_missed_runs()
        
    # Check if a new job log was created
    rows = test_db.execute_read("SELECT status, total_candles_ingested FROM job_logs WHERE job_type = 'DAILY_INCREMENTAL' ORDER BY started_at DESC, completed_at DESC NULLS LAST")
    assert len(rows) == 3
    assert rows[0][0] == 'COMPLETED'
    assert rows[0][1] == 100

