import asyncio
import logging
from pathlib import Path
import sys

# Ensure project root is in sys.path when script is run directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.connection import get_db, close_db
from db.migrations import init_db
from services.scheduler_service import SchedulerService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

async def main():
    try:
        init_db()
        scheduler = SchedulerService()
        scheduler.start()
        logger.info("Scheduler started. Waiting for jobs...")
        
        # Keep process alive
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
    finally:
        close_db()
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
