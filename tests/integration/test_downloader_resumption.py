"""Integration tests for HistoricalDownloader: resumption, stop conditions, and deduplication.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md and plan/04_HISTORICAL_DOWNLOADER_ENGINE.md.
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock
import pytest

from core.interfaces import Checkpoint, IMarketDataProvider, SymbolEntity
from core.rate_governor import RateGovernor
from db.connection import DuckDBConnectionManager
from db.migrations import init_db
from db.repositories.duckdb_candle_repo import DuckDBCandleRepo
from db.repositories.duckdb_checkpoint_repo import DuckDBCheckpointRepo
from db.repositories.duckdb_symbol_repo import DuckDBSymbolRepo
from services.downloader_service import HistoricalDownloader


@pytest.fixture
def mock_db():
    manager = DuckDBConnectionManager(db_path=":memory:")
    init_db(manager=manager)
    yield manager
    manager.close()


@pytest.fixture
def fast_rate_governor():
    return RateGovernor(
        target_per_min=180,
        burst_per_sec=10,
        daily_cap=10000,
        time_provider=lambda: 1000.0,
        sleep_provider=lambda s: None,
    )


def test_downloader_interruption_and_resumption(mock_db, fast_rate_governor):
    """Verify simulated interruption cleanly commits in-flight checkpoint and resumption avoids duplicates."""
    symbol_repo = DuckDBSymbolRepo(mock_db)
    checkpoint_repo = DuckDBCheckpointRepo(mock_db)
    candle_repo = DuckDBCandleRepo(mock_db)

    # Seed symbol
    symbol = "NSE:INFY-EQ"
    symbol_repo.upsert_symbols([
        SymbolEntity(
            symbol=symbol,
            name="Infosys Limited",
            listing_date=date(2023, 1, 1),
            tier=1,
            priority_rank=1,
        )
    ])

    # Build synthetic candles generator per date chunk
    def synthetic_fetch(symbol, resolution, range_from, range_to, cont_flag="0"):
        from_d = datetime.strptime(range_from, "%Y-%m-%d").date()
        to_d = datetime.strptime(range_to, "%Y-%m-%d").date()
        # Return 5 candles per chunk
        candles = []
        cur_d = to_d
        count = 0
        while cur_d >= from_d and count < 5:
            ts = datetime.combine(cur_d, datetime.min.time()) + timedelta(hours=9, minutes=15)
            candles.append({
                "symbol": symbol,
                "timestamp": ts,
                "open": 1500.0,
                "high": 1510.0,
                "low": 1495.0,
                "close": 1505.0,
                "volume": 1000,
            })
            cur_d -= timedelta(days=1)
            count += 1
        return candles

    mock_provider = MagicMock(spec=IMarketDataProvider)
    mock_provider.fetch_candles.side_effect = synthetic_fetch

    downloader = HistoricalDownloader(
        market_data_provider=mock_provider,
        candle_writer=candle_repo,
        checkpoint_repo=checkpoint_repo,
        symbol_repo=symbol_repo,
        db=mock_db,
    )

    # 1. Run with interruption simulated after 1st chunk
    original_fetch = downloader.market_data_provider.fetch_candles
    chunks_processed = 0

    def interrupting_fetch(*args, **kwargs):
        nonlocal chunks_processed
        res = original_fetch(*args, **kwargs)
        chunks_processed += 1
        if chunks_processed == 1:
            # Simulate SIGINT interruption after first chunk
            downloader.cancel()
        return res

    downloader.market_data_provider.fetch_candles = interrupting_fetch

    # Execute first run
    end_date = date(2023, 12, 31)
    downloader.download_symbol(symbol, timeframe="1m", target_years=1, end_date=end_date)

    # Verify state after interruption
    cp1 = checkpoint_repo.get_checkpoint(symbol, "1m")
    assert cp1 is not None
    assert cp1.status == "IN_PROGRESS"
    assert cp1.total_candles == 5
    assert cp1.earliest_ts is not None

    # Count rows in DuckDB after first run
    read_cursor = mock_db.get_read_cursor()
    count_1 = read_cursor.execute("SELECT count(*) FROM candles_1m_raw WHERE symbol = ?", [symbol]).fetchone()[0]
    read_cursor.close()
    assert count_1 == 5

    # 2. Resumption Run: Create fresh downloader and resume
    downloader2 = HistoricalDownloader(
        market_data_provider=mock_provider,
        candle_writer=candle_repo,
        checkpoint_repo=checkpoint_repo,
        symbol_repo=symbol_repo,
        db=mock_db,
    )
    # Restore normal non-interrupting fetch
    downloader2.market_data_provider.fetch_candles = synthetic_fetch

    downloader2.download_symbol(symbol, timeframe="1m", target_years=1, end_date=end_date)

    # Verify state after resumption
    cp2 = checkpoint_repo.get_checkpoint(symbol, "1m")
    assert cp2 is not None
    assert cp2.status == "COMPLETED"
    assert cp2.total_candles > 5

    # Verify DuckDB has zero duplicate rows
    read_cursor = mock_db.get_read_cursor()
    total_rows = read_cursor.execute("SELECT count(*) FROM candles_1m_raw WHERE symbol = ?", [symbol]).fetchone()[0]
    distinct_rows = read_cursor.execute("SELECT count(DISTINCT timestamp) FROM candles_1m_raw WHERE symbol = ?", [symbol]).fetchone()[0]
    read_cursor.close()

    assert total_rows == distinct_rows, "Duplicate candle timestamps detected in candles_1m_raw!"


def test_end_of_history_stop_condition(mock_db, fast_rate_governor):
    """Verify stop condition requires BOTH >= 3 consecutive empty chunks AND chunk_start < listing_date."""
    symbol_repo = DuckDBSymbolRepo(mock_db)
    checkpoint_repo = DuckDBCheckpointRepo(mock_db)
    candle_repo = DuckDBCandleRepo(mock_db)

    symbol = "NSE:NEWCO-EQ"
    listing_date = date(2023, 6, 1)

    symbol_repo.upsert_symbols([
        SymbolEntity(
            symbol=symbol,
            name="New Company Limited",
            listing_date=listing_date,
            tier=2,
            priority_rank=10,
        )
    ])

    # Provider that returns candles only for dates >= listing_date, empty before that
    def mock_fetch(symbol, resolution, range_from, range_to, cont_flag="0"):
        to_d = datetime.strptime(range_to, "%Y-%m-%d").date()
        from_d = datetime.strptime(range_from, "%Y-%m-%d").date()
        if to_d < listing_date:
            return []  # No data before listing date
        return [{
            "symbol": symbol,
            "timestamp": datetime.combine(to_d, datetime.min.time()),
            "open": 100.0,
            "high": 105.0,
            "low": 95.0,
            "close": 102.0,
            "volume": 500,
        }]

    mock_provider = MagicMock(spec=IMarketDataProvider)
    mock_provider.fetch_candles.side_effect = mock_fetch

    downloader = HistoricalDownloader(
        market_data_provider=mock_provider,
        candle_writer=candle_repo,
        checkpoint_repo=checkpoint_repo,
        symbol_repo=symbol_repo,
        db=mock_db,
    )

    downloader.download_symbol(symbol, timeframe="1m", target_years=3, end_date=date(2023, 12, 31))

    cp = checkpoint_repo.get_checkpoint(symbol, "1m")
    assert cp is not None
    assert cp.status == "COMPLETED"
    # Should have stopped cleanly when empty chunks occurred before listing date
    assert cp.consecutive_empty_count >= 3


def test_pause_and_resume_controls(mock_db, fast_rate_governor):
    """Verify pause() and resume() toggles safely control ingestion."""
    downloader = HistoricalDownloader(
        candle_writer=DuckDBCandleRepo(mock_db),
        checkpoint_repo=DuckDBCheckpointRepo(mock_db),
        symbol_repo=DuckDBSymbolRepo(mock_db),
        db=mock_db,
    )

    assert not downloader.is_paused
    downloader.pause()
    assert downloader.is_paused
    downloader.resume()
    assert not downloader.is_paused
