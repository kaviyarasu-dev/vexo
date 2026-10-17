"""Unit tests for Late-Start Hybrid Backfill Service.
Verifies uniform 1-minute candle volume distribution across overlapping price buckets
and strict total volume conservation.
"""

import pytest
from services.orderblock.backfill_service import VolumeProfileBackfillService


def test_single_candle_backfill_conservation():
    """Verify that a single candle's volume is distributed uniformly across overlapping buckets
    with exact volume conservation.
    """
    service = VolumeProfileBackfillService()
    # Day range 100.0 to 140.0 with 40 buckets -> width = 1.0 per bucket
    # Bucket i spans [100 + i, 100 + i + 1]
    # Candle low=105.0, high=115.0 spans buckets 5 through 14 (10 buckets)
    candle = {
        "open": 106.0,
        "high": 115.0,
        "low": 105.0,
        "close": 112.0,
        "volume": 1000,
    }
    
    buckets = service.backfill_from_1m_candles(
        symbol="NSE:RELIANCE-EQ",
        trade_date="2026-10-19",
        day_low=100.0,
        day_high=140.0,
        candles_1m=[candle],
        num_buckets=40,
    )

    # 1. Exact volume conservation
    assert sum(buckets.values()) == 1000

    # 2. Correct bucket range occupied
    for b in range(5):
        assert buckets.get(b, 0) == 0
    for b in range(5, 15):
        assert buckets.get(b, 0) == 100  # 1000 / 10 = 100
    for b in range(15, 40):
        assert buckets.get(b, 0) == 0


def test_multi_candle_backfill_conservation_with_remainders():
    """Verify volume conservation across multiple candles where volume is not cleanly divisible."""
    service = VolumeProfileBackfillService()
    candles = [
        {"open": 100.0, "high": 105.0, "low": 100.0, "close": 104.0, "volume": 1500},
        {"open": 104.0, "high": 110.0, "low": 103.0, "close": 108.0, "volume": 2237},  # Prime number
        {"open": 108.0, "high": 125.0, "low": 107.0, "close": 120.0, "volume": 5873},  # Prime number
    ]
    total_candle_vol = sum(c["volume"] for c in candles)
    
    buckets = service.backfill_from_1m_candles(
        symbol="NSE:TCS-EQ",
        trade_date="2026-10-19",
        day_low=100.0,
        day_high=140.0,
        candles_1m=candles,
        num_buckets=40,
    )

    assert sum(buckets.values()) == total_candle_vol


def test_single_point_candle():
    """Verify zero-range candle (low == high) assigns full volume to the exact bucket."""
    service = VolumeProfileBackfillService()
    candle = {"open": 120.5, "high": 120.5, "low": 120.5, "close": 120.5, "volume": 500}
    
    buckets = service.backfill_from_1m_candles(
        symbol="NSE:INFY-EQ",
        trade_date="2026-10-19",
        day_low=100.0,
        day_high=140.0,
        candles_1m=[candle],
        num_buckets=40,
    )

    assert sum(buckets.values()) == 500
    # 120.5 falls in bucket 20: [120.0, 121.0]
    assert buckets.get(20, 0) == 500


def test_out_of_bounds_candle():
    """Verify candle outside initial day range clamps safely to boundary buckets."""
    service = VolumeProfileBackfillService()
    candles = [
        {"open": 90.0, "high": 95.0, "low": 90.0, "close": 94.0, "volume": 100},  # below day_low
        {"open": 145.0, "high": 150.0, "low": 145.0, "close": 148.0, "volume": 200}, # above day_high
    ]
    buckets = service.backfill_from_1m_candles(
        symbol="NSE:TEST-EQ",
        trade_date="2026-10-19",
        day_low=100.0,
        day_high=140.0,
        candles_1m=candles,
        num_buckets=40,
    )
    assert sum(buckets.values()) == 300
    assert buckets.get(0, 0) == 100
    assert buckets.get(39, 0) == 200


def test_backfill_from_db_candles_integration():
    """Verify loading 1m candles directly from DuckDB and persisting volume_profile_buckets."""
    from db.connection import DuckDBConnectionManager
    from db.migrations import init_db

    manager = DuckDBConnectionManager(db_path=":memory:")
    init_db(manager=manager)

    try:
        # Seed raw 1m candles for 2026-10-19
        def _seed(conn):
            conn.execute(
                """
                INSERT INTO candles_1m_raw (symbol, timestamp, open, high, low, close, volume)
                VALUES 
                    ('NSE:RELIANCE-EQ', '2026-10-19 09:15:00', 2800.0, 2810.0, 2800.0, 2805.0, 10000),
                    ('NSE:RELIANCE-EQ', '2026-10-19 09:16:00', 2805.0, 2825.0, 2802.0, 2820.0, 25000),
                    ('NSE:RELIANCE-EQ', '2026-10-19 09:17:00', 2820.0, 2840.0, 2818.0, 2835.0, 15000)
                """
            )

        manager.execute_write_batch(_seed)

        service = VolumeProfileBackfillService()
        profile = service.backfill_from_db_candles(
            symbol="NSE:RELIANCE-EQ",
            trade_date="2026-10-19",
            manager=manager,
            num_buckets=40,
        )

        assert profile is not None
        assert profile.symbol == "NSE:RELIANCE-EQ"
        assert profile.trade_date == "2026-10-19"
        assert profile.day_low == 2800.0
        assert profile.day_high == 2840.0
        assert profile.current_price == 2835.0
        assert len(profile.buckets) == 40
        assert sum(b.volume for b in profile.buckets) == 50000

        # Verify persisted in volume_profile_buckets table
        cursor = manager.get_read_cursor()
        persisted_count = cursor.execute(
            "SELECT COUNT(*) FROM volume_profile_buckets WHERE symbol = 'NSE:RELIANCE-EQ'"
        ).fetchone()[0]
        cursor.close()
        assert persisted_count == 40
    finally:
        manager.close()

