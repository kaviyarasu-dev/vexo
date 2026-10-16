import sys
import os
import argparse
import logging

# Add parent dir to path so we can import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.corporate_actions_service import CorporateActionsService
from db.connection import get_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Recompute Corporate Actions Adjustment Factors")
    parser.add_argument("--symbol", type=str, help="Specific symbol to recompute, e.g. NSE:TATASTEEL-EQ", default=None)
    args = parser.parse_args()

    db_manager = get_db()
    service = CorporateActionsService(db_manager)

    conn = db_manager.get_read_cursor()
    
    if args.symbol:
        symbols = [args.symbol]
    else:
        # Fetch all symbols that have corporate actions
        query = "SELECT DISTINCT symbol FROM corporate_actions"
        rows = conn.execute(query).fetchall()
        symbols = [r[0] for r in rows]
        
    logger.info(f"Recomputing adjustment factors for {len(symbols)} symbols...")
    
    success_count = 0
    for sym in symbols:
        try:
            service.recompute_factors(sym)
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to recompute factors for {sym}: {e}")
            
    logger.info(f"Successfully recomputed factors for {success_count} symbols.")

if __name__ == "__main__":
    main()
