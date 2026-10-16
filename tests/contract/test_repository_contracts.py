"""Contract tests verifying DuckDB repositories implement canonical interfaces.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md Section 1.
"""

import inspect
import pytest

from core.interfaces import (
    ICandleReader,
    ICandleWriter,
    ISymbolRepository,
    ICheckpointRepository,
)
from db.repositories.duckdb_candle_repo import DuckDBCandleRepo
from db.repositories.duckdb_symbol_repo import DuckDBSymbolRepo
from db.repositories.duckdb_checkpoint_repo import DuckDBCheckpointRepo
from db.connection import DuckDBConnectionManager


@pytest.fixture
def mock_db():
    manager = DuckDBConnectionManager(db_path=":memory:")
    yield manager
    manager.close()


def test_candle_repo_implements_icandle_reader(mock_db):
    """Verify DuckDBCandleRepo satisfies ICandleReader abstract interface contract."""
    repo = DuckDBCandleRepo(db=mock_db)
    assert isinstance(repo, ICandleReader)
    
    # Contract methods existence and signatures
    sig_raw = inspect.signature(repo.get_raw_candles)
    assert "symbol" in sig_raw.parameters
    assert "timeframe" in sig_raw.parameters
    assert "start" in sig_raw.parameters
    assert "end" in sig_raw.parameters
    assert "limit" in sig_raw.parameters
    assert "cursor" in sig_raw.parameters

    sig_adj = inspect.signature(repo.get_adjusted_candles)
    assert "symbol" in sig_adj.parameters
    assert "timeframe" in sig_adj.parameters
    assert "start" in sig_adj.parameters
    assert "end" in sig_adj.parameters
    assert "limit" in sig_adj.parameters

    sig_latest = inspect.signature(repo.get_latest_candle)
    assert "symbol" in sig_latest.parameters
    assert "timeframe" in sig_latest.parameters


def test_candle_repo_implements_icandle_writer(mock_db):
    """Verify DuckDBCandleRepo satisfies ICandleWriter abstract interface contract."""
    repo = DuckDBCandleRepo(db=mock_db)
    assert isinstance(repo, ICandleWriter)

    sig_1m = inspect.signature(repo.batch_insert_1m)
    assert "candles" in sig_1m.parameters

    sig_1d = inspect.signature(repo.batch_insert_1d)
    assert "candles" in sig_1d.parameters

    sig_stage = inspect.signature(repo.stage_and_merge_1m)
    assert "staging_table" in sig_stage.parameters


def test_symbol_repo_implements_isymbol_repository(mock_db):
    """Verify DuckDBSymbolRepo satisfies ISymbolRepository abstract interface contract."""
    repo = DuckDBSymbolRepo(db=mock_db)
    assert isinstance(repo, ISymbolRepository)

    sig_upsert = inspect.signature(repo.upsert_symbols)
    assert "symbols" in sig_upsert.parameters

    sig_search = inspect.signature(repo.search_symbols)
    assert "query" in sig_search.parameters
    assert "category" in sig_search.parameters
    assert "limit" in sig_search.parameters

    sig_get = inspect.signature(repo.get_by_symbol)
    assert "symbol" in sig_get.parameters

    sig_list = inspect.signature(repo.list_active_symbols)
    assert "tier" in sig_list.parameters


def test_checkpoint_repo_implements_icheckpoint_repository(mock_db):
    """Verify DuckDBCheckpointRepo satisfies ICheckpointRepository abstract interface contract."""
    repo = DuckDBCheckpointRepo(db=mock_db)
    assert isinstance(repo, ICheckpointRepository)

    sig_get = inspect.signature(repo.get_checkpoint)
    assert "symbol" in sig_get.parameters
    assert "timeframe" in sig_get.parameters

    sig_update = inspect.signature(repo.update_checkpoint)
    assert "checkpoint" in sig_update.parameters

    sig_list = inspect.signature(repo.list_pending_symbols)
    assert "timeframe" in sig_list.parameters
    assert "tier" in sig_list.parameters
