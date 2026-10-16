import pytest
from services.scheduler_service import SchedulerService, get_cron_expression

def test_get_cron_expression():
    assert get_cron_expression() == "45 15 * * 1-5"

@pytest.mark.asyncio
async def test_scheduler_skips_holiday():
    class MockAuth:
        pass
    class MockSync:
        pass
    class MockCalendar:
        def is_trading_day(self, d): return False
        
    scheduler = SchedulerService(auth_service=MockAuth(), sync_service=MockSync(), calendar=MockCalendar())
    scheduler.state = "RUNNING"
    
    # Run the job
    await scheduler.run_daily_sync_job()
    # If it didn't skip, it would crash because MockSync doesn't have sync_daily_delta
    assert scheduler.state == "RUNNING"

@pytest.mark.asyncio
async def test_scheduler_skips_failed_auth():
    scheduler = SchedulerService(auth_service=None, sync_service=None, calendar=None)
    scheduler.state = "FAILED_AUTH"
    
    # Run the job
    await scheduler.run_daily_sync_job()
    # It should just return without doing anything
    assert scheduler.state == "FAILED_AUTH"
