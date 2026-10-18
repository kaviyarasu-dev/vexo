"""Unit tests for Fyers WebSocket Tick Recorder Daemon.
Tests in-memory volume delta accumulation, 40-bucket routing, dirty tracking,
DuckDB 10-second batch flushing, and reconnection data preservation.
"""

import asyncio
from datetime import datetime
import pytest

from db.connection import DuckDBConnectionManager
from db.migrations import init_db
from services.orderblock.tick_recorder import FyersTickRecorder, StockProfileBuffer


@pytest.fixture
def mem_db():
    manager = DuckDBConnectionManager(db_path=":memory:")
    init_db(manager=manager)
    yield manager
    manager.close()


@pytest.mark.asyncio
async def test_tick_delta_and_bucket_routing(mem_db):
    recorder = FyersTickRecorder(db_manager=mem_db, flush_interval_sec=10.0)
    symbol = "NSE:RELIANCE-EQ"

    # Tick 1: Initial baseline tick (total volume = 50,000)
    recorder.handle_tick(
        symbol=symbol,
        ltp=2800.0,
        total_volume_traded=50000,
        day_low=2800.0,
        day_high=2840.0,
    )

    buf = recorder.get_buffer(symbol)
    assert buf is not None
    assert buf.prev_total_volume == 50000
    assert sum(buf.bucket_volumes.values()) == 0  # Initial baseline does not create phantom delta

    # Tick 2: 5,000 shares traded at LTP 2820.0 (bucket 20)
    recorder.handle_tick(
        symbol=symbol,
        ltp=2820.0,
        total_volume_traded=55000,
        day_low=2800.0,
        day_high=2840.0,
    )
    assert buf.prev_total_volume == 55000
    assert buf.bucket_volumes[20] == 5000
    assert buf.is_dirty is True

    # Tick 3: 3,000 shares traded at LTP 2835.0 (bucket 35)
    recorder.handle_tick(
        symbol=symbol,
        ltp=2835.0,
        total_volume_traded=58000,
        day_low=2800.0,
        day_high=2840.0,
    )
    assert buf.prev_total_volume == 58000
    assert buf.bucket_volumes[35] == 3000
    assert buf.bucket_volumes[20] == 5000
    assert sum(buf.bucket_volumes.values()) == 8000


@pytest.mark.asyncio
async def test_dirty_flag_and_batch_flush(mem_db):
    recorder = FyersTickRecorder(db_manager=mem_db, flush_interval_sec=10.0)
    symbol = "NSE:INFY-EQ"

    # Setup ticks
    recorder.handle_tick(symbol, 1500.0, 10000, 1500.0, 1540.0)
    recorder.handle_tick(symbol, 1520.0, 16000, 1500.0, 1540.0)
    
    buf = recorder.get_buffer(symbol)
    assert buf.is_dirty is True

    # Execute batch flush
    await recorder.flush_dirty_profiles()

    assert buf.is_dirty is False

    # Check persistence in DuckDB
    cursor = mem_db.get_read_cursor()
    rows = cursor.execute(
        "SELECT bucket_index, volume FROM volume_profile_buckets WHERE symbol = ? AND volume > 0",
        (symbol,),
    ).fetchall()
    cursor.close()

    assert len(rows) == 1
    assert rows[0][0] == 20  # bucket 20
    assert rows[0][1] == 6000


@pytest.mark.asyncio
async def test_reconnect_preserves_memory_state(mem_db):
    recorder = FyersTickRecorder(db_manager=mem_db, flush_interval_sec=10.0)
    symbol = "NSE:TCS-EQ"

    recorder.handle_tick(symbol, 3500.0, 10000, 3500.0, 3540.0)
    recorder.handle_tick(symbol, 3510.0, 14000, 3500.0, 3540.0)
    
    buf_before = recorder.get_buffer(symbol)
    vol_before = sum(buf_before.bucket_volumes.values())
    assert vol_before == 4000

    # Simulate reconnect
    recorder.on_reconnect()

    buf_after = recorder.get_buffer(symbol)
    assert buf_after is not None
    assert sum(buf_after.bucket_volumes.values()) == 4000
    assert buf_after.prev_total_volume == 14000


def test_get_mini_profile(mem_db):
    recorder = FyersTickRecorder(db_manager=mem_db, flush_interval_sec=10.0)
    symbol = "NSE:SBIN-EQ"

    recorder.handle_tick(symbol, 800.0, 10000, 800.0, 840.0)
    recorder.handle_tick(symbol, 820.0, 15000, 800.0, 840.0)  # 5,000 vol in bucket 20
    recorder.handle_tick(symbol, 830.0, 17500, 800.0, 840.0)  # 2,500 vol in bucket 30

    mini = recorder.get_mini_profile(symbol)
    assert mini is not None
    assert mini["poc_price"] == pytest.approx(820.5, abs=0.6)
    assert mini["poc_width_pct"] == 100.0
    assert mini["current_bucket_idx"] == 30
    assert len(mini["mini_buckets"]) == 40
    assert mini["mini_buckets"][20] == 100.0
    assert mini["mini_buckets"][30] == 50.0
