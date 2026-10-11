"""Database layer for the NSE Quant Platform.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md and plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md.
"""

from db.connection import (
    DuckDBConnectionManager,
    get_db,
    close_db,
    DatabaseLockError,
)
from db.migrations import (
    init_db,
    get_current_schema_version,
    CURRENT_SCHEMA_VERSION,
)
from db.repositories.duckdb_candle_repo import DuckDBCandleRepo
from db.repositories.duckdb_symbol_repo import DuckDBSymbolRepo
from db.repositories.duckdb_checkpoint_repo import DuckDBCheckpointRepo

__all__ = [
    "DuckDBConnectionManager",
    "get_db",
    "close_db",
    "DatabaseLockError",
    "init_db",
    "get_current_schema_version",
    "CURRENT_SCHEMA_VERSION",
    "DuckDBCandleRepo",
    "DuckDBSymbolRepo",
    "DuckDBCheckpointRepo",
]
