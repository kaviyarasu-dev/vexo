"""Unit tests for DuckDB repositories and connection manager.
Tests DuckDBCandleRepo, DuckDBSymbolRepo, DuckDBCheckpointRepo, and DuckDBConnectionManager.
"""

from datetime import date, datetime
import json
from pathlib import Path
import pytest

from core.interfaces import Candle, Checkpoint, SymbolEntity
from db.connection import DuckDBConnectionManager
from db.migrations import init_db
from db.repositories.duckdb_candle_repo import DuckDBCandleRepo
from db.repositories.duckdb_checkpoint_repo import DuckDBCheckpointRepo
from db.repositories.duckdb_symbol_repo import DuckDBSymbolRepo


@pytest.fixture
def in_memory_db():
    """Provides an isolated in-memory DuckDB connection with all canonical schemas applied."""
    manager = DuckDBConnectionManager(db_path=":memory:")
    init_db(manager=manager)
    yield manager
    manager.close()


@pytest.fixture
def candle_repo(in_memory_db):
    return DuckDBCandleRepo(db=in_memory_db)


@pytest.fixture
def symbol_repo(in_memory_db):
    return DuckDBSymbolRepo(db=in_memory_db)


@pytest.fixture
def checkpoint_repo(in_memory_db):
    return DuckDBCheckpointRepo(db=in_memory_db)


@pytest.fixture
def sample_candles_data():
    fixture_path = Path("tests/fixtures/sample_candles.json")
    return json.loads(fixture_path.read_text(encoding="utf-8"))


# ============================================================================
# DuckDBCandleRepo Tests (ICandleWriter & ICandleReader)
# ============================================================================

def test_batch_insert_1m_and_deduplication(candle_repo, in_memory_db, sample_candles_data):
    """Verify batch insertion and anti-join deduplication for 1m candles."""
    candles = sample_candles_data["candles_1m"]
    
    # First insert: all rows should be inserted
    inserted_first = candle_repo.batch_insert_1m(candles)
    assert inserted_first == len(candles)

    # Verify rows in database
    cursor = in_memory_db.get_read_cursor()
    total = cursor.execute("SELECT count(*) FROM candles_1m_raw;").fetchone()[0]
    assert total == len(candles)

    # Second insert with identical candles: anti-join should reject all duplicates (0 inserted)
    inserted_second = candle_repo.batch_insert_1m(candles)
    assert inserted_second == 0

    # Total in DB must remain unchanged
    total_after = cursor.execute("SELECT count(*) FROM candles_1m_raw;").fetchone()[0]
    assert total_after == len(candles)
    cursor.close()


def test_batch_insert_1d_and_deduplication(candle_repo, in_memory_db, sample_candles_data):
    """Verify batch insertion and anti-join deduplication for 1D daily candles."""
    candles = sample_candles_data["candles_1d"]

    inserted_first = candle_repo.batch_insert_1d(candles)
    assert inserted_first == len(candles)

    # Re-insert should yield 0 new rows
    inserted_second = candle_repo.batch_insert_1d(candles)
    assert inserted_second == 0

    cursor = in_memory_db.get_read_cursor()
    total = cursor.execute("SELECT count(*) FROM candles_1d_raw;").fetchone()[0]
    assert total == len(candles)
    cursor.close()


def test_stage_and_merge_1m(candle_repo, in_memory_db, sample_candles_data):
    """Verify stage_and_merge_1m from an existing staging table."""
    conn = in_memory_db.get_write_connection()
    conn.execute("""
        CREATE TEMP TABLE my_custom_staging (
            symbol VARCHAR,
            timestamp TIMESTAMP,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume BIGINT
        );
    """)
    conn.execute("""
        INSERT INTO my_custom_staging VALUES
        ('NSE:INFY-EQ', '2024-01-10 03:45:00', 1450.0, 1455.0, 1448.0, 1452.0, 5000),
        ('NSE:INFY-EQ', '2024-01-10 03:46:00', 1452.0, 1458.0, 1451.0, 1457.0, 6200);
    """)

    merged = candle_repo.stage_and_merge_1m("my_custom_staging")
    assert merged == 2

    # Verify records present in candles_1m_raw
    cursor = in_memory_db.get_read_cursor()
    rows = cursor.execute("SELECT symbol, volume FROM candles_1m_raw WHERE symbol='NSE:INFY-EQ';").fetchall()
    assert len(rows) == 2
    cursor.close()


def test_get_raw_candles_and_pagination(candle_repo, sample_candles_data):
    """Verify get_raw_candles filtering by timeframe, date range, limit, and cursor."""
    candle_repo.batch_insert_1m(sample_candles_data["candles_1m"])

    start = datetime(2024, 1, 10, 3, 45, 0)
    end = datetime(2024, 1, 10, 3, 49, 0)

    # Query with limit 3
    results = candle_repo.get_raw_candles(
        symbol="NSE:RELIANCE-EQ",
        timeframe="1m",
        start=start,
        end=end,
        limit=3
    )
    assert len(results) == 3
    assert results[0].symbol == "NSE:RELIANCE-EQ"
    assert results[0].open == 2580.0

    # Query with cursor pagination (after 3rd candle timestamp)
    third_ts = results[2].timestamp.isoformat()
    paginated = candle_repo.get_raw_candles(
        symbol="NSE:RELIANCE-EQ",
        timeframe="1m",
        start=start,
        end=end,
        limit=3,
        cursor=third_ts
    )
    assert len(paginated) == 2
    assert paginated[0].open == 2589.0


def test_get_adjusted_candles_with_corporate_actions(candle_repo, in_memory_db):
    """Verify get_adjusted_candles applies dynamic adjustment factor views."""
    # Seed raw daily candle
    daily_candles = [
        {
            "symbol": "NSE:SPLITTEST-EQ",
            "date": "2024-01-05",
            "open": 1000.0,
            "high": 1020.0,
            "low": 990.0,
            "close": 1010.0,
            "volume": 100000
        },
        {
            "symbol": "NSE:SPLITTEST-EQ",
            "date": "2024-01-15",
            "open": 205.0,
            "high": 210.0,
            "low": 200.0,
            "close": 208.0,
            "volume": 500000
        }
    ]
    candle_repo.batch_insert_1d(daily_candles)

    # Seed adjustment factor: 5:1 stock split on 2024-01-10 -> factor_price = 0.2, factor_volume = 5.0
    conn = in_memory_db.get_write_connection()
    conn.execute("""
        INSERT INTO adjustment_factors (symbol, ex_date, factor_price, factor_volume)
        VALUES ('NSE:SPLITTEST-EQ', '2024-01-10', 0.2, 5.0);
    """)

    adjusted = candle_repo.get_adjusted_candles(
        symbol="NSE:SPLITTEST-EQ",
        timeframe="1D",
        start=date(2024, 1, 1),
        end=date(2024, 1, 20)
    )

    assert len(adjusted) == 2
    # Pre-split candle (2024-01-05 <= 2024-01-10) should have adjusted price (1000 * 0.2 = 200) and volume (100000 * 5 = 500000)
    assert adjusted[0].open == pytest.approx(200.0)
    assert adjusted[0].close == pytest.approx(202.0)
    assert adjusted[0].volume == 500000

    # Post-split candle (2024-01-15 > 2024-01-10) should remain unadjusted (factor 1.0)
    assert adjusted[1].open == pytest.approx(205.0)
    assert adjusted[1].volume == 500000


def test_get_latest_candle(candle_repo, sample_candles_data):
    """Verify get_latest_candle retrieves the latest timestamp/date candle."""
    candle_repo.batch_insert_1m(sample_candles_data["candles_1m"])
    candle_repo.batch_insert_1d(sample_candles_data["candles_1d"])

    latest_1m = candle_repo.get_latest_candle("NSE:RELIANCE-EQ", "1m")
    assert latest_1m is not None
    assert latest_1m.close == 2591.5

    latest_1d = candle_repo.get_latest_candle("NSE:RELIANCE-EQ", "1D")
    assert latest_1d is not None
    assert latest_1d.close == 2610.0

    non_existent = candle_repo.get_latest_candle("NSE:NONEXISTENT-EQ", "1m")
    assert non_existent is None


# ============================================================================
# DuckDBSymbolRepo Tests (ISymbolRepository)
# ============================================================================

def test_symbol_repository_upsert_and_search(symbol_repo):
    """Verify symbol master upsert, search, get, and listing by tier."""
    symbols = [
        SymbolEntity(
            symbol="NSE:RELIANCE-EQ",
            name="Reliance Industries Limited",
            isin="INE002A01018",
            category="NIFTY50",
            tier=1,
            priority_rank=1,
        ),
        SymbolEntity(
            symbol="NSE:TCS-EQ",
            name="Tata Consultancy Services Limited",
            isin="INE467B01029",
            category="NIFTY50",
            tier=1,
            priority_rank=2,
        ),
        SymbolEntity(
            symbol="NSE:MIDCAP1-EQ",
            name="Sample Midcap Stock",
            category="NIFTYMIDCAP150",
            tier=2,
            priority_rank=101,
        ),
    ]

    count = symbol_repo.upsert_symbols(symbols)
    assert count == 3

    # Exact lookup
    rel = symbol_repo.get_by_symbol("NSE:RELIANCE-EQ")
    assert rel is not None
    assert rel.name == "Reliance Industries Limited"
    assert rel.isin == "INE002A01018"
    assert rel.tier == 1

    # Search by partial query
    matches = symbol_repo.search_symbols("TATA")
    assert len(matches) == 1
    assert matches[0].symbol == "NSE:TCS-EQ"

    # Search with category filter
    nifty50_matches = symbol_repo.search_symbols("", category="NIFTY50")
    assert len(nifty50_matches) == 2

    # List active symbols by tier
    tier1 = symbol_repo.list_active_symbols(tier=1)
    assert len(tier1) == 2

    tier2 = symbol_repo.list_active_symbols(tier=2)
    assert len(tier2) == 1
    assert tier2[0].symbol == "NSE:MIDCAP1-EQ"


# ============================================================================
# DuckDBCheckpointRepo Tests (ICheckpointRepository)
# ============================================================================

def test_checkpoint_repository_lifecycle(checkpoint_repo, symbol_repo):
    """Verify checkpoint state tracking and pending symbols retrieval."""
    # Seed symbols
    symbol_repo.upsert_symbols([
        SymbolEntity(symbol="NSE:AAA-EQ", name="AAA Corp", tier=1, priority_rank=1),
        SymbolEntity(symbol="NSE:BBB-EQ", name="BBB Corp", tier=1, priority_rank=2),
        SymbolEntity(symbol="NSE:CCC-EQ", name="CCC Corp", tier=2, priority_rank=3),
    ])

    # Initially, all Tier 1 symbols are pending
    pending_tier1 = checkpoint_repo.list_pending_symbols("1m", tier=1)
    assert pending_tier1 == ["NSE:AAA-EQ", "NSE:BBB-EQ"]

    # Update checkpoint for AAA to COMPLETED
    cp = Checkpoint(
        symbol="NSE:AAA-EQ",
        timeframe="1m",
        earliest_ts=datetime(2019, 1, 1),
        latest_ts=datetime(2024, 1, 1),
        total_candles=468750,
        status="COMPLETED",
    )
    checkpoint_repo.update_checkpoint(cp)

    # AAA should no longer be pending
    pending_tier1_after = checkpoint_repo.list_pending_symbols("1m", tier=1)
    assert pending_tier1_after == ["NSE:BBB-EQ"]

    # Verify retrieval
    retrieved = checkpoint_repo.get_checkpoint("NSE:AAA-EQ", "1m")
    assert retrieved is not None
    assert retrieved.status == "COMPLETED"
    assert retrieved.total_candles == 468750
