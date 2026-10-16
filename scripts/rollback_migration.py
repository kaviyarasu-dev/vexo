import logging
from pathlib import Path
import sys

# Ensure project root is in sys.path when script is run directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.connection import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def rollback_latest_migration():
    db = get_db()
    
    def _rollback(conn):
        row = conn.execute("SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1").fetchone()
        if not row:
            logger.info("No migrations to rollback.")
            return
            
        version = row[0]
        logger.info(f"Rolling back migration {version}")
        
        if version == "1.0.0":
            # the down() equivalent for 1.0.0
            tables = [
                "schema_version", "symbols", "candles_1m_raw", "candles_1d_raw",
                "corporate_actions", "adjustment_factors", "download_checkpoints",
                "market_holidays", "job_logs"
            ]
            views = ["candles_1d_adjusted", "candles_1m_adjusted"]
            
            for view in views:
                conn.execute(f"DROP VIEW IF EXISTS {view};")
            for table in tables:
                conn.execute(f"DROP TABLE IF EXISTS {table};")
        else:
            logger.warning(f"No down() method defined for version {version}")
            return
            
        try:
            conn.execute("DELETE FROM schema_version WHERE version = ?", [version])
        except Exception:
            pass # schema_version might have been dropped above
            
        logger.info(f"Successfully rolled back {version}")
        
    db.execute_write_batch(_rollback)

if __name__ == "__main__":
    rollback_latest_migration()
