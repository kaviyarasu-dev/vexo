"""Integration test verifying DuckDB multi-threaded reader concurrency and single-writer isolation.
Validates plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md Definition of Done Item 2:
'Reader threads execute queries concurrently without waiting on write locks;
 zero database locked exceptions under 50 concurrent reader queries.'
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import logging
from pathlib import Path
import tempfile
import time
import pytest

from db.connection import DuckDBConnectionManager
from db.migrations import init_db
from db.repositories.duckdb_candle_repo import DuckDBCandleRepo

logger = logging.getLogger(__name__)


@pytest.fixture
def temp_db_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_market_data.duckdb")
        manager = DuckDBConnectionManager(db_path=db_path)
        init_db(manager=manager)
        yield manager
        manager.close()


def test_50_concurrent_readers_during_active_background_writes(temp_db_file):
    """Verify 50 concurrent reader queries execute with zero lock errors while writer is committing."""
    manager = temp_db_file
    repo = DuckDBCandleRepo(db=manager)

    # 1. Seed baseline candles
    base_ts = datetime(2024, 1, 1, 9, 15)
    initial_candles = [
        {
            "symbol": "NSE:RELIANCE-EQ",
            "timestamp": (base_ts + timedelta(minutes=i)).isoformat(),
            "open": 2500.0 + i * 0.1,
            "high": 2505.0 + i * 0.1,
            "low": 2495.0 + i * 0.1,
            "close": 2502.0 + i * 0.1,
            "volume": 1000 + i,
        }
        for i in range(2000)
    ]
    repo.batch_insert_1m(initial_candles)

    # 2. Concurrency setup
    stop_writer = False
    write_errors = []
    writes_completed = 0

    def background_writer():
        nonlocal writes_completed
        batch_idx = 0
        while not stop_writer:
            batch_ts = base_ts + timedelta(days=1, minutes=batch_idx * 50)
            batch = [
                {
                    "symbol": "NSE:RELIANCE-EQ",
                    "timestamp": (batch_ts + timedelta(minutes=j)).isoformat(),
                    "open": 2600.0 + j,
                    "high": 2605.0 + j,
                    "low": 2595.0 + j,
                    "close": 2602.0 + j,
                    "volume": 5000,
                }
                for j in range(50)
            ]
            try:
                repo.batch_insert_1m(batch)
                writes_completed += 1
            except Exception as e:
                write_errors.append(e)
            time.sleep(0.05)

    def reader_task(reader_id: int):
        t0 = time.perf_counter()
        # Readers get independent cursor - does NOT acquire write lock
        cursor = manager.get_read_cursor()
        try:
            res = cursor.execute("""
                SELECT count(*), avg(close) 
                FROM candles_1m_raw 
                WHERE symbol = 'NSE:RELIANCE-EQ';
            """).fetchone()
            duration_ms = (time.perf_counter() - t0) * 1000
            return {
                "reader_id": reader_id,
                "count": res[0],
                "avg_close": res[1],
                "duration_ms": duration_ms,
            }
        finally:
            cursor.close()

    # 3. Start writer thread and 50 reader threads
    import threading
    writer_thread = threading.Thread(target=background_writer, daemon=True)
    writer_thread.start()

    # Wait for writer to begin
    time.sleep(0.1)

    reader_results = []
    reader_errors = []

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(reader_task, i) for i in range(50)]
        for f in as_completed(futures):
            try:
                reader_results.append(f.result())
            except Exception as e:
                reader_errors.append(e)

    stop_writer = True
    writer_thread.join(timeout=2.0)

    # 4. Assert zero exceptions and check metrics
    assert len(reader_errors) == 0, f"Reader errors encountered: {reader_errors}"
    assert len(write_errors) == 0, f"Writer errors encountered: {write_errors}"
    assert len(reader_results) == 50
    assert writes_completed > 0

    # Verify query latency
    latencies = sorted(r["duration_ms"] for r in reader_results)
    p50 = latencies[25]
    p95 = latencies[47]

    logger.info(
        "Reader concurrency results: count=%d, P50=%.2f ms, P95=%.2f ms, writes_completed=%d",
        len(reader_results), p50, p95, writes_completed
    )

    # Every reader must have received valid rows
    for r in reader_results:
        assert r["count"] >= 2000
