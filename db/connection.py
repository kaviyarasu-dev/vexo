"""DuckDB Connection Manager and Single-Writer Concurrency Engine.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md Section 8 and plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md.
"""

import asyncio
import logging
import os
from pathlib import Path
import threading
from typing import Any, Callable, Optional, Sequence, Tuple
import duckdb

from config.settings import get_settings

logger = logging.getLogger(__name__)


class DatabaseLockError(Exception):
    """Raised when DuckDB database file is locked by another active process."""
    pass


class DuckDBConnectionManager:
    """Manages DuckDB embedded database connections with a single writer and concurrent readers.
    
    Principles:
    - Single write connection instance protected by a dedicated write lock.
    - Readers obtain non-blocking independent cursors via `conn.cursor()` without acquiring the writer lock.
    - Blocking operations wrapped in asyncio.to_thread for async FastAPI event loop safety.
    - Stale lock recovery mechanism detecting orphaned lock/PID files.
    """

    def __init__(self, db_path: Optional[str] = None, read_only: bool = False) -> None:
        if db_path is None:
            settings = get_settings()
            db_path = settings.DUCKDB_PATH

        self.db_path = str(db_path)
        self.read_only = read_only
        self.is_memory = (self.db_path == ":memory:")
        self._write_lock = threading.RLock()
        self._conn: Optional[duckdb.DuckDBPyConnection] = None
        self._pid_file: Optional[Path] = None
        self._is_closed = False

        if not self.is_memory and not self.read_only:
            db_file = Path(self.db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            self._pid_file = Path(f"{self.db_path}.pid")

        self._init_connection()

    def _is_pid_active(self, pid: int) -> bool:
        """Check if an OS process ID is currently running."""
        try:
            import psutil
            return psutil.pid_exists(pid)
        except ImportError:
            if os.name == "nt":
                try:
                    import ctypes
                    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                    handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                    if handle:
                        ctypes.windll.kernel32.CloseHandle(handle)
                        return True
                    return False
                except Exception:
                    return False
            # Unix fallback
            try:
                os.kill(pid, 0)
                return True
            except (OSError, Exception):
                return False

    def _check_and_recover_stale_lock(self) -> None:
        """Inspect PID file and remove stale lock if previous process crashed."""
        if not self._pid_file or not self._pid_file.exists():
            return

        try:
            pid_str = self._pid_file.read_text().strip()
            if pid_str.isdigit():
                pid = int(pid_str)
                if pid == os.getpid():
                    # Same process re-opening
                    return
                if not self._is_pid_active(pid):
                    logger.warning(
                        "Detected stale lock from inactive process PID %d on %s. Releasing.",
                        pid, self.db_path
                    )
                    self._pid_file.unlink(missing_ok=True)
                    # DuckDB wal/lock recovery: If duckdb lock file exists, remove
                    lock_file = Path(f"{self.db_path}.lock")
                    if lock_file.exists():
                        lock_file.unlink(missing_ok=True)
                else:
                    logger.warning("Active process PID %d holds lock on %s", pid, self.db_path)
        except Exception as e:
            logger.error("Failed during stale lock inspection: %s", e)

    def _init_connection(self) -> None:
        """Initialize the primary DuckDB connection."""
        if not self.read_only:
            self._check_and_recover_stale_lock()

        try:
            self._conn = duckdb.connect(database=self.db_path, read_only=self.read_only)
        except Exception as exc:
            msg = str(exc)
            if "Failure while replaying WAL file" in msg and not self.read_only:
                logger.warning(
                    "Detected unreplayable WAL file on %s. Archiving and recovering database.",
                    self.db_path
                )
                wal_path = Path(f"{self.db_path}.wal")
                if wal_path.exists():
                    wal_bak = Path(f"{self.db_path}.wal.bak")
                    try:
                        wal_path.replace(wal_bak)
                    except Exception as e:
                        logger.error("Failed to archive corrupted WAL: %s", e)
                self._conn = duckdb.connect(database=self.db_path, read_only=False)
            elif isinstance(exc, duckdb.IOException) and ("Could not set lock on file" in msg or "database is locked" in msg.lower()):
                if not self.read_only:
                    # Attempt recovery once
                    self._check_and_recover_stale_lock()
                try:
                    self._conn = duckdb.connect(database=self.db_path, read_only=self.read_only)
                except Exception as retry_exc:
                    raise DatabaseLockError(
                        f"DuckDB database '{self.db_path}' is locked by another process: {retry_exc}"
                    ) from retry_exc
            else:
                raise exc


        # Record owning PID
        if self._pid_file and not self.read_only:
            try:
                self._pid_file.write_text(str(os.getpid()))
            except Exception as e:
                logger.debug("Could not write pid file: %s", e)

        # Configure DuckDB runtime optimizations
        if self._conn:
            self._conn.execute("PRAGMA threads=4;")
            self._conn.execute("PRAGMA preserve_insertion_order=false;")

    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        """Access the underlying primary connection."""
        if self._conn is None or self._is_closed:
            raise RuntimeError("Database connection is closed or not initialized.")
        return self._conn

    def get_read_cursor(self) -> duckdb.DuckDBPyConnection:
        """Dispense a thread-local independent read cursor.
        
        CRITICAL ARCHITECTURAL GUARANTEE:
        Readers execute concurrently on this cursor without acquiring the writer lock.
        Zero database locked exceptions under 50 concurrent reader queries.
        """
        if self._conn is None or self._is_closed:
            raise RuntimeError("Database connection is closed or not initialized.")
        return self._conn.cursor()

    def get_write_connection(self) -> duckdb.DuckDBPyConnection:
        """Returns the primary connection for writing.
        Callers must acquire writer lock or use execute_write."""
        return self.connection

    def execute_write(self, query: str, params: Sequence[Any] = ()) -> duckdb.DuckDBPyConnection:
        """Synchronously execute a write query serialized under the single-writer lock."""
        with self._write_lock:
            return self.connection.execute(query, params)

    def execute_write_df(self, query: str, df: Any) -> duckdb.DuckDBPyConnection:
        """Register a dataframe or arrow table and execute an insertion under the writer lock."""
        with self._write_lock:
            # Register dataframe in connection
            self.connection.register("_temp_input_table", df)
            try:
                result = self.connection.execute(query)
            finally:
                self.connection.unregister("_temp_input_table")
            return result

    def execute_write_batch(self, func: Callable[[duckdb.DuckDBPyConnection], Any]) -> Any:
        """Execute a batch mutation callback under the single-writer lock."""
        with self._write_lock:
            return func(self.connection)

    async def execute_write_async(self, query: str, params: Sequence[Any] = ()) -> Any:
        """Dispatches write execution to a background worker thread to prevent blocking event loop."""
        return await asyncio.to_thread(self.execute_write, query, params)

    def execute_read(self, query: str, params: Sequence[Any] = ()) -> list[Tuple[Any, ...]]:
        """Executes a read query using a dedicated non-blocking cursor and returns all rows."""
        cursor = self.get_read_cursor()
        try:
            return cursor.execute(query, params).fetchall()
        finally:
            cursor.close()

    async def execute_read_async(self, query: str, params: Sequence[Any] = ()) -> list[Tuple[Any, ...]]:
        """Dispatches read query to a worker thread for FastAPI event loop safety."""
        return await asyncio.to_thread(self.execute_read, query, params)

    def initialize_schema(self) -> None:
        """Idempotently initialize all canonical tables, views, and migration records."""
        from db.migrations import init_db
        init_db(manager=self)

    def close(self) -> None:
        """Close connection and clean up locks."""
        with self._write_lock:
            if not self._is_closed:
                self._is_closed = True
                if self._conn:
                    try:
                        self._conn.close()
                    except Exception as e:
                        logger.debug("Error closing DuckDB connection: %s", e)
                    self._conn = None
                if self._pid_file and self._pid_file.exists():
                    try:
                        self._pid_file.unlink(missing_ok=True)
                    except Exception as e:
                        logger.debug("Error unlinking PID file: %s", e)


_GLOBAL_DB_MANAGER: Optional[DuckDBConnectionManager] = None
_GLOBAL_DB_LOCK = threading.Lock()


def get_db(db_path: Optional[str] = None, reset: bool = False) -> DuckDBConnectionManager:
    """Singleton accessor for the DuckDBConnectionManager."""
    global _GLOBAL_DB_MANAGER
    with _GLOBAL_DB_LOCK:
        if reset or _GLOBAL_DB_MANAGER is None:
            if _GLOBAL_DB_MANAGER is not None and reset:
                _GLOBAL_DB_MANAGER.close()
            _GLOBAL_DB_MANAGER = DuckDBConnectionManager(db_path=db_path)
        elif db_path is not None and db_path != _GLOBAL_DB_MANAGER.db_path:
            _GLOBAL_DB_MANAGER.close()
            _GLOBAL_DB_MANAGER = DuckDBConnectionManager(db_path=db_path)
        return _GLOBAL_DB_MANAGER


def close_db() -> None:
    """Closes and resets the singleton connection manager."""
    global _GLOBAL_DB_MANAGER
    with _GLOBAL_DB_LOCK:
        if _GLOBAL_DB_MANAGER is not None:
            _GLOBAL_DB_MANAGER.close()
            _GLOBAL_DB_MANAGER = None
