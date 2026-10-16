"""DuckDB implementation of ICheckpointRepository.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md and plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md.
"""

from datetime import datetime
import logging
from typing import List, Optional
import duckdb

from core.interfaces import Checkpoint, ICheckpointRepository
from db.connection import DuckDBConnectionManager, get_db

logger = logging.getLogger(__name__)


class DuckDBCheckpointRepo(ICheckpointRepository):
    """Repository for resumable download state-machine and checkpoint tracking."""

    def __init__(self, db: Optional[DuckDBConnectionManager] = None) -> None:
        self.db = db or get_db()

    def get_checkpoint(self, symbol: str, timeframe: str) -> Optional[Checkpoint]:
        """Retrieve checkpoint state for a specific symbol and timeframe."""
        cursor = self.db.get_read_cursor()
        try:
            sql = """
                SELECT symbol, timeframe, earliest_ts, latest_ts,
                       total_candles, status, consecutive_empty_count,
                       last_attempt_at, error_message
                FROM download_checkpoints
                WHERE symbol = ? AND timeframe = ?;
            """
            row = cursor.execute(sql, [symbol, timeframe]).fetchone()
            if row is None:
                return None

            return Checkpoint(
                symbol=row[0],
                timeframe=row[1],
                earliest_ts=row[2],
                latest_ts=row[3],
                total_candles=int(row[4]),
                status=row[5],
                consecutive_empty_count=int(row[6]),
                last_attempt_at=row[7],
                error_message=row[8],
            )
        finally:
            cursor.close()

    def update_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Persist or update checkpoint state under writer lock."""
        def _do_update(conn: duckdb.DuckDBPyConnection) -> None:
            sql = """
                INSERT INTO download_checkpoints (
                    symbol, timeframe, earliest_ts, latest_ts,
                    total_candles, status, consecutive_empty_count,
                    last_attempt_at, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (symbol, timeframe) DO UPDATE SET
                    earliest_ts = EXCLUDED.earliest_ts,
                    latest_ts = EXCLUDED.latest_ts,
                    total_candles = EXCLUDED.total_candles,
                    status = EXCLUDED.status,
                    consecutive_empty_count = EXCLUDED.consecutive_empty_count,
                    last_attempt_at = EXCLUDED.last_attempt_at,
                    error_message = EXCLUDED.error_message;
            """
            last_attempt = checkpoint.last_attempt_at or datetime.utcnow()
            conn.execute(sql, [
                checkpoint.symbol,
                checkpoint.timeframe,
                checkpoint.earliest_ts,
                checkpoint.latest_ts,
                checkpoint.total_candles,
                checkpoint.status,
                checkpoint.consecutive_empty_count,
                last_attempt,
                checkpoint.error_message,
            ])

        self.db.execute_write_batch(_do_update)

    def list_pending_symbols(self, timeframe: str, tier: Optional[int] = None) -> List[str]:
        """List active symbols requiring download/sync for the timeframe.
        
        Returns active symbols where checkpoint status is 'PENDING', 'FAILED', or not yet created.
        Ordered by priority_rank ASC.
        """
        cursor = self.db.get_read_cursor()
        try:
            if tier is not None:
                sql = """
                    SELECT s.symbol
                    FROM symbols s
                    LEFT JOIN download_checkpoints dc
                        ON s.symbol = dc.symbol AND dc.timeframe = ?
                    WHERE s.is_active = TRUE
                      AND s.tier = ?
                      AND (dc.status IS NULL OR dc.status IN ('PENDING', 'FAILED'))
                    ORDER BY s.priority_rank ASC, s.symbol ASC;
                """
                rows = cursor.execute(sql, [timeframe, tier]).fetchall()
            else:
                sql = """
                    SELECT s.symbol
                    FROM symbols s
                    LEFT JOIN download_checkpoints dc
                        ON s.symbol = dc.symbol AND dc.timeframe = ?
                    WHERE s.is_active = TRUE
                      AND (dc.status IS NULL OR dc.status IN ('PENDING', 'FAILED'))
                    ORDER BY s.priority_rank ASC, s.symbol ASC;
                """
                rows = cursor.execute(sql, [timeframe]).fetchall()

            return [r[0] for r in rows]
        finally:
            cursor.close()
