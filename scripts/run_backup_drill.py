import os
import shutil
from pathlib import Path
import sys
import duckdb

# Ensure project root is in sys.path when script is run directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.connection import get_db
from services.maintenance_service import MaintenanceService

def run_drill(snapshot_dir="data/backups/weekly_snapshot", scratch_db_path="data/scratch/restore_test.duckdb", db=None):
    if db is None:
        db = get_db()
        
    m = MaintenanceService(db)
    snapshot_dir_path = Path(snapshot_dir)
    
    # 1. Export snapshot
    if snapshot_dir_path.exists():
        shutil.rmtree(snapshot_dir_path)
        
    m.export_snapshot(str(snapshot_dir_path))
    
    # 2. Setup restore DB
    scratch_db = Path(scratch_db_path)
    scratch_db.parent.mkdir(parents=True, exist_ok=True)
    if scratch_db.exists():
        scratch_db.unlink()
        
    restore_conn = duckdb.connect(str(scratch_db))
    try:
        # 3. Import snapshot
        restore_conn.execute(f"IMPORT DATABASE '{snapshot_dir_path}';")
        
        # 4. Compare row counts
        tables = ["symbols", "candles_1m_raw", "candles_1d_raw", "corporate_actions", "adjustment_factors"]
        prod_conn = db.get_read_cursor()
        try:
            for table in tables:
                prod_count = prod_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                rest_count = restore_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                assert prod_count == rest_count, f"Row count mismatch on {table}: {prod_count} != {rest_count}"
        finally:
            prod_conn.close()
            
        print("Backup and restore drill successful. 100% row count match.")
        
    finally:
        restore_conn.close()
        
    # 5. Delete scratch file
    if scratch_db.exists():
        scratch_db.unlink()

if __name__ == "__main__":
    run_drill()
