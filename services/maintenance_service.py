import logging
from pathlib import Path

from db.connection import DuckDBConnectionManager

logger = logging.getLogger(__name__)

class MaintenanceService:
    def __init__(self, db: DuckDBConnectionManager):
        self.db = db

    def run_checkpoint(self) -> None:
        """Flushes WAL to columnar file and truncates WAL."""
        logger.info("Running database CHECKPOINT")
        self.db.execute_write("CHECKPOINT;")

    def run_vacuum(self) -> None:
        """Defragments database and updates zone maps."""
        logger.info("Running database VACUUM")
        self.db.execute_write("VACUUM;")

    def export_snapshot(self, backup_dir: str = "data/backups/weekly_snapshot") -> None:
        """Exports a Parquet snapshot of the database."""
        logger.info(f"Exporting database snapshot to {backup_dir}")
        Path(backup_dir).parent.mkdir(parents=True, exist_ok=True)
        # Using string interpolation for path. Export paths must be literal in duckdb.
        self.db.execute_write(f"EXPORT DATABASE '{backup_dir}' (FORMAT PARQUET);")
