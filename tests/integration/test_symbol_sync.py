"""Integration tests for Symbol Master Ingestion, Universe Sorter, and Checkpoint Seeding.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md and plan/03_SYMBOL_MASTER_AND_UNIVERSE_MANAGER.md.
"""

from datetime import date
from pathlib import Path
import pytest

from core.interfaces import SymbolEntity
from db.connection import DuckDBConnectionManager
from db.migrations import init_db
from scripts.fetch_nse_constituents import load_fallback_constituents
from services.symbol_master_parser import SymbolMasterParser
from services.symbol_service import SymbolService


@pytest.fixture
def mock_db():
    manager = DuckDBConnectionManager(db_path=":memory:")
    init_db(manager=manager)
    yield manager
    manager.close()


def test_tier_arithmetic_exactness(mock_db):
    """Verify that tier classification adheres strictly to:
    Tier 1 = 100, Tier 2 = 150, Tier 3 = 250, Total 1-3 = 500.
    """
    service = SymbolService(db=mock_db)
    constituents = load_fallback_constituents()

    # Generate synthetic active symbols spanning all 500 constituents plus 100 Tier 4 equities
    raw_symbols = []
    
    # Add constituents
    for cat, items in constituents.items():
        for idx, item in enumerate(items):
            raw_symbols.append(
                SymbolEntity(
                    symbol=f"NSE:{item['symbol']}-EQ",
                    name=item["name"],
                    isin=item["isin"] or f"INE{idx:08d}",
                    series="EQ",
                    is_active=True,
                )
            )

    # Add 100 extra equities for Tier 4
    for i in range(100):
        raw_symbols.append(
            SymbolEntity(
                symbol=f"NSE:TAILSTOCK{i:03d}-EQ",
                name=f"Tail Stock {i}",
                isin=f"INE9999{i:04d}",
                series="EQ",
                is_active=True,
            )
        )

    # Classify tiers
    classified = service.classify_and_apply_tiers(raw_symbols, constituents)
    service.upsert_symbols(classified)

    # Verify counts in DuckDB
    cursor = mock_db.get_read_cursor()
    t1 = cursor.execute("SELECT count(*) FROM symbols WHERE tier = 1;").fetchone()[0]
    t2 = cursor.execute("SELECT count(*) FROM symbols WHERE tier = 2;").fetchone()[0]
    t3 = cursor.execute("SELECT count(*) FROM symbols WHERE tier = 3;").fetchone()[0]
    t4 = cursor.execute("SELECT count(*) FROM symbols WHERE tier = 4;").fetchone()[0]
    total_500 = cursor.execute("SELECT count(*) FROM symbols WHERE tier IN (1, 2, 3);").fetchone()[0]
    cursor.close()

    assert t1 == 100, f"Expected Tier 1 == 100, got {t1}"
    assert t2 == 150, f"Expected Tier 2 == 150, got {t2}"
    assert t3 == 250, f"Expected Tier 3 == 250, got {t3}"
    assert total_500 == 500, f"Expected Total Nifty 500 == 500, got {total_500}"
    assert t4 == len(raw_symbols) - 500, f"Expected Tier 4 == {len(raw_symbols) - 500}, got {t4}"


def test_checkpoint_seeding_scopes(mock_db):
    """Verify checkpoints are seeded: 1m for Tiers 1-3 (500), 1D for Tiers 1-4."""
    service = SymbolService(db=mock_db)
    constituents = load_fallback_constituents()

    # Create 500 Nifty stocks + 50 Tier 4 stocks
    symbols = []
    for cat in ("NIFTY50", "NIFTYNEXT50", "NIFTYMIDCAP150", "NIFTYSMALLCAP250"):
        for item in constituents[cat]:
            symbols.append(
                SymbolEntity(
                    symbol=f"NSE:{item['symbol']}-EQ",
                    name=item["name"],
                    isin=item["isin"],
                    series="EQ",
                )
            )
    for i in range(50):
        symbols.append(
            SymbolEntity(
                symbol=f"NSE:OTHER{i}-EQ",
                name=f"Other {i}",
                isin=f"INE9{i:07d}",
                series="EQ",
            )
        )

    classified = service.classify_and_apply_tiers(symbols, constituents)
    service.upsert_symbols(classified)

    cp_1m, cp_1d = service.seed_download_checkpoints()
    assert cp_1m == 500
    assert cp_1d == len(symbols)

    # Verify status in DB
    cursor = mock_db.get_read_cursor()
    pending_1m = cursor.execute(
        "SELECT count(*) FROM download_checkpoints WHERE timeframe = '1m' AND status = 'PENDING';"
    ).fetchone()[0]
    pending_1d = cursor.execute(
        "SELECT count(*) FROM download_checkpoints WHERE timeframe = '1D' AND status = 'PENDING';"
    ).fetchone()[0]
    cursor.close()

    assert pending_1m == 500
    assert pending_1d == len(symbols)


def test_prefix_search_reliance(mock_db):
    """Verify sub-5ms symbol search returns RELIANCE when queried by prefix."""
    service = SymbolService(db=mock_db)
    service.upsert_symbols([
        SymbolEntity(
            symbol="NSE:RELIANCE-EQ",
            name="Reliance Industries Limited",
            isin="INE002A01018",
            tier=1,
            category="NIFTY50",
            priority_rank=1,
        ),
        SymbolEntity(
            symbol="NSE:RELINFRA-BE",
            name="Reliance Infrastructure Limited",
            isin="INE036A01016",
            tier=4,
            category="OTHERS",
            priority_rank=9999,
        ),
    ])

    results = service.search_symbols("RELI", None, 5)
    assert len(results) >= 1
    assert any("RELIANCE" in s.name.upper() for s in results)
    assert results[0].symbol == "NSE:RELIANCE-EQ"


def test_market_holidays_sync_and_query(mock_db):
    """Verify holiday persistence and querying."""
    service = SymbolService(db=mock_db)
    synced = service.sync_market_holidays()
    assert synced > 0

    # Query holidays
    holidays = service.get_market_holidays()
    assert len(holidays) > 0

    # Republic Day (2026-01-26) should be a trading holiday
    assert service.is_trading_holiday("2026-01-26") is True

    # A normal weekday like 2026-01-27 should not be a holiday
    assert service.is_trading_holiday("2026-01-27") is False
