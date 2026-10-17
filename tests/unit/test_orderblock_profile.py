"""Unit tests for OrderBlock In-Tile Volume Profile Math and Engine.
Verifies 40-bucket dynamic range calculation, delta volume aggregation,
Point of Control (POC) detection, relative peak scaling, and Support/Resistance classification.
"""

import pytest
from services.orderblock.profile_engine import (
    ProfileBucket,
    VolumeProfile,
    VolumeProfileEngine,
)


def test_bucket_bounds_division():
    """Verify 40 uniform bucket divisions over [day_low, day_high]."""
    engine = VolumeProfileEngine()
    bounds = engine.calculate_bucket_bounds(day_low=100.0, day_high=140.0, num_buckets=40)
    
    assert len(bounds) == 40
    # Bucket 0: [100.0, 101.0]
    assert pytest.approx(bounds[0][0]) == 100.0
    assert pytest.approx(bounds[0][1]) == 101.0
    # Bucket 39: [139.0, 140.0]
    assert pytest.approx(bounds[39][0]) == 139.0
    assert pytest.approx(bounds[39][1]) == 140.0
    
    # Verify continuous boundaries without gaps
    for i in range(len(bounds) - 1):
        assert pytest.approx(bounds[i][1]) == bounds[i + 1][0]


def test_price_to_bucket_index():
    """Verify price mapping to bucket indices including exact edge cases."""
    engine = VolumeProfileEngine()
    
    # Exactly at day_low -> bucket 0
    assert engine.get_bucket_index(100.0, 100.0, 140.0, 40) == 0
    # Mid-range price -> bucket 20 (since width is 1.0, 120.0 is index 20)
    assert engine.get_bucket_index(120.0, 100.0, 140.0, 40) == 20
    # Just below day_high -> bucket 39
    assert engine.get_bucket_index(139.9, 100.0, 140.0, 40) == 39
    # Exactly at day_high -> clamped to bucket 39
    assert engine.get_bucket_index(140.0, 100.0, 140.0, 40) == 39
    # Below day_low -> clamped to bucket 0
    assert engine.get_bucket_index(95.0, 100.0, 140.0, 40) == 0
    # Above day_high -> clamped to bucket 39
    assert engine.get_bucket_index(150.0, 100.0, 140.0, 40) == 39


def test_delta_volume_accumulation():
    """Verify tick delta calculation and bucket assignment."""
    engine = VolumeProfileEngine()
    
    # Tick with positive volume delta
    b_idx, delta_v = engine.accumulate_tick(
        symbol="NSE:RELIANCE-EQ",
        ltp=2820.5,
        total_volume_traded=50000,
        prev_total_volume=45000,
        day_low=2800.0,
        day_high=2840.0,
    )
    assert delta_v == 5000
    assert b_idx == 20

    # Tick with identical volume (zero delta)
    _, zero_delta = engine.accumulate_tick(
        symbol="NSE:RELIANCE-EQ",
        ltp=2820.5,
        total_volume_traded=50000,
        prev_total_volume=50000,
        day_low=2800.0,
        day_high=2840.0,
    )
    assert zero_delta == 0

    # Decreasing volume anomaly should yield 0 delta
    _, neg_delta = engine.accumulate_tick(
        symbol="NSE:RELIANCE-EQ",
        ltp=2820.5,
        total_volume_traded=49000,
        prev_total_volume=50000,
        day_low=2800.0,
        day_high=2840.0,
    )
    assert neg_delta == 0


def test_poc_detection_and_relative_scaling():
    """Verify Point of Control (POC) detection and 0-100% relative width normalization."""
    engine = VolumeProfileEngine()
    bucket_volumes = {
        5: 1000,
        15: 5000,  # Max volume -> POC
        25: 2500,
    }
    profile = engine.build_profile(
        symbol="NSE:RELIANCE-EQ",
        trade_date="2026-10-19",
        day_low=2800.0,
        day_high=2840.0,
        current_price=2820.0,
        bucket_volumes=bucket_volumes,
    )

    assert profile.symbol == "NSE:RELIANCE-EQ"
    assert profile.trade_date == "2026-10-19"
    assert len(profile.buckets) == 40
    assert profile.poc_volume == 5000
    
    # POC bucket properties
    poc_bucket = profile.buckets[15]
    assert poc_bucket.is_poc is True
    assert poc_bucket.width_pct == 100.0
    assert profile.poc_price == pytest.approx((poc_bucket.price_low + poc_bucket.price_high) / 2.0)

    # Relative scaling
    assert profile.buckets[25].width_pct == 50.0   # 2500 / 5000 * 100
    assert profile.buckets[5].width_pct == 20.0    # 1000 / 5000 * 100
    assert profile.buckets[0].width_pct == 0.0
    assert profile.buckets[0].is_poc is False


def test_support_vs_resistance_classification():
    """Verify side classification: SUPPORT if bucket price_high <= current_price, else RESISTANCE."""
    engine = VolumeProfileEngine()
    bucket_volumes = {10: 1000, 30: 1000}
    
    profile = engine.build_profile(
        symbol="NSE:INFY-EQ",
        trade_date="2026-10-19",
        day_low=2800.0,
        day_high=2840.0,
        current_price=2820.0,  # Boundary of bucket 20
        bucket_volumes=bucket_volumes,
    )

    # Bucket 10: [2810.0, 2811.0] <= 2820.0 -> SUPPORT
    assert profile.buckets[10].side == "SUPPORT"
    # Bucket 30: [2830.0, 2831.0] > 2820.0 -> RESISTANCE
    assert profile.buckets[30].side == "RESISTANCE"


def test_flat_range_edge_case():
    """Verify handling when day_high == day_low (e.g., at market opening tick)."""
    engine = VolumeProfileEngine()
    bounds = engine.calculate_bucket_bounds(day_low=1500.0, day_high=1500.0, num_buckets=40)
    assert len(bounds) == 40

    profile = engine.build_profile(
        symbol="NSE:HDFCBANK-EQ",
        trade_date="2026-10-19",
        day_low=1500.0,
        day_high=1500.0,
        current_price=1500.0,
        bucket_volumes={0: 250},
    )
    assert len(profile.buckets) == 40
    assert profile.poc_volume == 250
    assert profile.buckets[0].is_poc is True
    assert profile.buckets[0].width_pct == 100.0


def test_zero_total_volume():
    """Verify profile when all bucket volumes are zero."""
    engine = VolumeProfileEngine()
    profile = engine.build_profile(
        symbol="NSE:SBIN-EQ",
        trade_date="2026-10-19",
        day_low=800.0,
        day_high=840.0,
        current_price=820.0,
        bucket_volumes={},
    )
    assert len(profile.buckets) == 40
    assert profile.poc_volume == 0
    for b in profile.buckets:
        assert b.width_pct == 0.0


def test_duckdb_profile_persistence():
    """Verify storing and loading volume profile buckets in DuckDB."""
    from db.connection import DuckDBConnectionManager
    from db.migrations import init_db

    manager = DuckDBConnectionManager(db_path=":memory:")
    init_db(manager=manager)

    try:
        engine = VolumeProfileEngine()
        bucket_volumes = {5: 1200, 15: 8400, 25: 4200}
        profile = engine.build_profile(
            symbol="NSE:RELIANCE-EQ",
            trade_date="2026-10-19",
            day_low=2800.0,
            day_high=2840.0,
            current_price=2820.0,
            bucket_volumes=bucket_volumes,
        )

        engine.persist_profile_buckets(profile, manager=manager)
        loaded = engine.load_profile_buckets("NSE:RELIANCE-EQ", "2026-10-19", manager=manager)

        assert loaded[5] == 1200
        assert loaded[15] == 8400
        assert loaded[25] == 4200
        assert loaded[0] == 0
    finally:
        manager.close()
