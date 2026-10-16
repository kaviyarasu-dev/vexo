"""Contract tests verifying SymbolService satisfies ISymbolRepository.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md Section 1.
"""

import inspect
import pytest

from core.interfaces import ISymbolRepository, SymbolEntity
from db.connection import DuckDBConnectionManager
from db.migrations import init_db
from db.repositories.duckdb_symbol_repo import DuckDBSymbolRepo
from services.symbol_service import SymbolService


@pytest.fixture
def mock_db():
    manager = DuckDBConnectionManager(db_path=":memory:")
    init_db(manager=manager)
    yield manager
    manager.close()


def test_symbol_service_implements_isymbol_repository(mock_db):
    """Verify SymbolService satisfies ISymbolRepository abstract interface contract."""
    service = SymbolService(db=mock_db)
    assert isinstance(service, ISymbolRepository)

    # Contract method existence and signatures
    sig_upsert = inspect.signature(service.upsert_symbols)
    assert "symbols" in sig_upsert.parameters

    sig_search = inspect.signature(service.search_symbols)
    assert "query" in sig_search.parameters
    assert "category" in sig_search.parameters
    assert "limit" in sig_search.parameters

    sig_get = inspect.signature(service.get_by_symbol)
    assert "symbol" in sig_get.parameters

    sig_list = inspect.signature(service.list_active_symbols)
    assert "tier" in sig_list.parameters


def test_duckdb_symbol_repo_implements_isymbol_repository(mock_db):
    """Verify DuckDBSymbolRepo satisfies ISymbolRepository abstract interface contract."""
    repo = DuckDBSymbolRepo(db=mock_db)
    assert isinstance(repo, ISymbolRepository)


def test_symbol_service_crud_contract(mock_db):
    """Verify standard operations through SymbolService facade."""
    service = SymbolService(db=mock_db)

    symbols = [
        SymbolEntity(
            symbol="NSE:TCS-EQ",
            name="Tata Consultancy Services Limited",
            isin="INE467B01029",
            category="NIFTY50",
            tier=1,
            priority_rank=1,
        ),
        SymbolEntity(
            symbol="NSE:INFY-EQ",
            name="Infosys Limited",
            isin="INE009A01021",
            category="NIFTY50",
            tier=1,
            priority_rank=2,
        ),
    ]

    count = service.upsert_symbols(symbols)
    assert count == 2

    # Exact lookup
    tcs = service.get_by_symbol("NSE:TCS-EQ")
    assert tcs is not None
    assert tcs.name == "Tata Consultancy Services Limited"

    # Search
    results = service.search_symbols("INFY")
    assert len(results) == 1
    assert results[0].symbol == "NSE:INFY-EQ"

    # Listing by tier
    tier1 = service.list_active_symbols(tier=1)
    assert len(tier1) == 2
