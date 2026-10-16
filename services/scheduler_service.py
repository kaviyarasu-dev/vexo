import asyncio
import datetime
import logging
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from core.exceptions import AuthenticationExpiredError
from services.auth_service import AuthService
from services.incremental_sync_service import IncrementalSyncService
from services.trading_calendar import TradingCalendar
from services.options_service import OptionChainCollector
from db.connection import get_db

logger = logging.getLogger(__name__)

class SchedulerService:
    """Automated daily scheduler for incremental updates."""
    
    def __init__(
        self,
        auth_service: Optional[AuthService] = None,
        sync_service: Optional[IncrementalSyncService] = None,
        calendar: Optional[TradingCalendar] = None
    ):
        self.auth_service = auth_service or AuthService()
        self.sync_service = sync_service or IncrementalSyncService()
        self.calendar = calendar or TradingCalendar()
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Kolkata'))
        self.db = get_db()
        self.state = "RUNNING"
        self._setup_jobs()
        
    def _setup_jobs(self):
        # 15:40 Pre-flight token probe
        self.scheduler.add_job(
            self.pre_flight_auth_probe,
            CronTrigger(hour=15, minute=40, day_of_week='0-4', timezone=pytz.timezone('Asia/Kolkata')),
            id='pre_flight_probe'
        )
        
        # 15:45 Incremental Sync
        self.scheduler.add_job(
            self.run_daily_sync_job,
            CronTrigger(hour=15, minute=45, day_of_week='0-4', timezone=pytz.timezone('Asia/Kolkata')),
            id='daily_sync'
        )

        # 15:35 Option Chain Snapshot
        self.scheduler.add_job(
            self.run_option_snapshot_job,
            CronTrigger(hour=15, minute=35, day_of_week='0-4', timezone=pytz.timezone('Asia/Kolkata')),
            id='option_snapshot'
        )
        
    def start(self):
        self.scheduler.start()
        asyncio.create_task(self.check_missed_runs())
        
    def get_cron_expression(self) -> str:
        return "45 15 * * 1-5"
        
    async def pre_flight_auth_probe(self):
        logger.info("Scheduler: Running pre-flight auth probe at 15:40 IST")
        valid = self.auth_service.validate_session()
        if not valid:
            logger.info("Session invalid. Attempting refresh...")
            refreshed = self.auth_service.refresh_token_if_needed()
            if not refreshed:
                logger.error("Token refresh failed. Entering FAILED_AUTH standby mode.")
                self.state = "FAILED_AUTH"
                self._log_job('MAINTENANCE', 'FAILED_AUTH', "Pre-flight auth probe failed. Token refresh unsuccessful.")
                return
        logger.info("Pre-flight auth probe successful.")
        
    async def run_daily_sync_job(self):
        if self.state == "FAILED_AUTH":
            logger.warning("Scheduler is in FAILED_AUTH state. Skipping sync job.")
            return
            
        today = datetime.date.today()
        if not self.calendar.is_trading_day(today):
            logger.info("Today is a holiday or weekend. Skipping daily sync.")
            return
            
        logger.info("Starting scheduled daily incremental sync...")
        self._log_job('DAILY_INCREMENTAL', 'RUNNING', "Job started")
        
        try:
            # Sync all active symbols (Tier 1-4)
            symbols = self._get_all_active_symbols()
            # Since DuckDB blocking calls should be in a thread, we wrap sync in to_thread
            stats = await asyncio.to_thread(self.sync_service.sync_daily_delta, symbols)
            
            self._log_job('DAILY_INCREMENTAL', 'COMPLETED', f"Processed {stats['symbols_processed']}, failed {stats['symbols_failed']}", stats)
            logger.info(f"Daily sync completed. Stats: {stats}")
        except AuthenticationExpiredError:
            self.state = "FAILED_AUTH"
            self._log_job('DAILY_INCREMENTAL', 'FAILED_AUTH', "Auth expired during sync")
            logger.error("Auth expired during daily sync. Halting.")
        except Exception as e:
            self._log_job('DAILY_INCREMENTAL', 'FAILED', str(e))
            logger.error(f"Daily sync failed: {e}")

    async def run_option_snapshot_job(self):
        if self.state == "FAILED_AUTH":
            logger.warning("Scheduler is in FAILED_AUTH state. Skipping option snapshot job.")
            return
            
        today = datetime.date.today()
        if not self.calendar.is_trading_day(today):
            logger.info("Today is a holiday or weekend. Skipping option snapshot.")
            return
            
        logger.info("Starting scheduled option chain snapshot...")
        self._log_job('OPTION_SNAPSHOT', 'RUNNING', "Job started")
        
        try:
            collector = OptionChainCollector()
            await collector.collect_snapshot("NSE:NIFTY50-INDEX")
            self._log_job('OPTION_SNAPSHOT', 'COMPLETED', "Snapshot collected successfully")
        except AuthenticationExpiredError:
            self.state = "FAILED_AUTH"
            self._log_job('OPTION_SNAPSHOT', 'FAILED_AUTH', "Auth expired during snapshot")
            logger.error("Auth expired during option snapshot. Halting.")
        except Exception as e:
            self._log_job('OPTION_SNAPSHOT', 'FAILED', str(e))
            logger.error(f"Option snapshot failed: {e}")
            
    async def check_missed_runs(self):
        """On startup, checks if catchup is needed and runs it silently."""
        logger.info("Checking for missed runs...")
        now = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
        today = now.date()
        
        # Check if market is currently open
        market_open = datetime.time(9, 15)
        market_close = datetime.time(15, 40) # Wait until post-closing
        
        if self.calendar.is_trading_day(today) and market_open <= now.time() <= market_close:
            logger.info("Market currently active. Delaying catch-up until 15:45 IST")
            return
            
        # Needs catchup? We check the last completed job
        last_job_row = await self.db.execute_read_async(
            "SELECT completed_at FROM job_logs WHERE job_type = 'DAILY_INCREMENTAL' AND status = 'COMPLETED' ORDER BY completed_at DESC LIMIT 1"
        )
        
        if not last_job_row:
            logger.info("No previous incremental job found. Will rely on historical backfill.")
            return
            
        last_completed = last_job_row[0][0]
        if last_completed:
            last_date = last_completed.date()
            prev_trading = self.calendar.get_previous_trading_day(today)
            if last_date < prev_trading:
                logger.info(f"Last sync was {last_date}, missing up to {prev_trading}. Running catchup...")
                await self.run_daily_sync_job()
            else:
                logger.info("No missed runs detected.")
                
    def _get_all_active_symbols(self) -> list[str]:
        rows = self.db.execute_read("SELECT symbol FROM symbols WHERE is_active = TRUE")
        return [r[0] for r in rows]
        
    def _log_job(self, job_type: str, status: str, details: str, stats: dict = None):
        import uuid
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.utcnow()
        if not stats:
            stats = {"symbols_processed": 0, "symbols_failed": 0, "total_candles_ingested": 0}
            
        self.db.execute_write(
            """
            INSERT INTO job_logs (job_id, job_type, started_at, completed_at, symbols_processed, symbols_failed, total_candles_ingested, status, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [job_id, job_type, now, now if status != 'RUNNING' else None, stats['symbols_processed'], stats['symbols_failed'], stats['total_candles_ingested'], status, details]
        )

def get_cron_expression() -> str:
    """Helper for definition of done test"""
    return "45 15 * * 1-5"
