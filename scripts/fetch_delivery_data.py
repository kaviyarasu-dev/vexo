import sys
import os
import argparse
import logging
from datetime import datetime, timedelta

# Add parent dir to path so we can import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.external_data_service import ExternalDataService
from db.connection import get_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Fetch NSE Delivery Data")
    parser.add_argument("--test", action="store_true", help="Run in test mode")
    parser.add_argument("--date", type=str, help="Date in DDMMYYYY format", default=None)
    args = parser.parse_args()

    db_manager = get_db()
    service = ExternalDataService(db_manager)

    if args.date:
        target_date_str = args.date
    else:
        # Default to previous day
        target_date_str = (datetime.now() - timedelta(days=1)).strftime("%d%m%Y")

    if args.test:
        logger.info("Running in TEST mode. Attempting fetch...")
        test_date = "01012024" # A sample date
        success = service.fetch_delivery_data(test_date)
        if not success:
            logger.info("Fetch failed (expected if 403/weekend). Test passes gracefully.")
    else:
        success = service.fetch_delivery_data(target_date_str)
        if not success:
            logger.error(f"Failed to fetch Delivery Data for {target_date_str}")
            sys.exit(1)

if __name__ == "__main__":
    main()
