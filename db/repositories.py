"""Unified repository exports for db package.
Implements and exposes canonical interfaces ICandleWriter, ICandleReader, ISymbolRepository, ICheckpointRepository.
"""

from core.interfaces import (
    ICandleReader,
    ICandleWriter,
    ISymbolRepository,
    ICheckpointRepository,
    Candle,
    SymbolEntity,
    Checkpoint,
)
from db.repositories.duckdb_candle_repo import DuckDBCandleRepo
from db.repositories.duckdb_symbol_repo import DuckDBSymbolRepo
from db.repositories.duckdb_checkpoint_repo import DuckDBCheckpointRepo

__all__ = [
    "ICandleReader",
    "ICandleWriter",
    "ISymbolRepository",
    "ICheckpointRepository",
    "Candle",
    "SymbolEntity",
    "Checkpoint",
    "DuckDBCandleRepo",
    "DuckDBSymbolRepo",
    "DuckDBCheckpointRepo",
]
