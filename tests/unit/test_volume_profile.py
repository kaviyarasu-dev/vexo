import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from services.indicators.volume_profile import VolumeProfileEngine, VolumeProfileResult, TPOResult


@pytest.fixture
def sample_profile_df():
    # 100 periods with known price distribution
    # Clustered around 2500 with high volume
    prices = [2480, 2490, 2500, 2500, 2500, 2510, 2520] * 10
    volumes = [1000, 2000, 10000, 12000, 9000, 2500, 1500] * 10
    
    df = pd.DataFrame({
        "open": [p - 2 for p in prices],
        "high": [p + 4 for p in prices],
        "low": [p - 4 for p in prices],
        "close": [p + 2 for p in prices],
        "volume": volumes
    })
    return df


@pytest.fixture
def sample_intraday_session_df():
    # 2 days of 5-minute candles in IST (09:15 to 15:30)
    records = []
    base_dates = [datetime(2026, 10, 8), datetime(2026, 10, 9)]
    
    for b_date in base_dates:
        # Start at 09:15 IST (03:45 UTC)
        cur_time = datetime(b_date.year, b_date.month, b_date.day, 3, 45)
        for i in range(75): # 75 * 5m = 375m (6h 15m)
            price = 2500 + (i * 0.5)
            records.append({
                "timestamp": cur_time + timedelta(minutes=i*5),
                "open": price - 1,
                "high": price + 2,
                "low": price - 2,
                "close": price + 1,
                "volume": 5000 if i == 20 else 1000 # peak volume at bar 20
            })
            
    return pd.DataFrame(records)


def test_volume_profile_computation(sample_profile_df):
    engine = VolumeProfileEngine(default_rows=50, default_value_area_pct=0.70)
    result = engine.compute_profile(sample_profile_df)

    assert result is not None
    assert isinstance(result, VolumeProfileResult)
    assert len(result.bins) == 50
    assert result.total_volume == pytest.approx(float(sum(sample_profile_df["volume"])))
    
    # POC must be around 2500 where 12,000 volume was concentrated
    assert 2495 <= result.poc_price <= 2505
    # Value Area bounds
    assert result.vah_price >= result.poc_price
    assert result.val_price <= result.poc_price
    # Value Area Volume must be at least 70% of total
    assert result.value_area_volume >= 0.70 * result.total_volume


def test_session_volume_profiles(sample_intraday_session_df):
    engine = VolumeProfileEngine()
    sessions = engine.compute_session_profiles(sample_intraday_session_df)

    assert len(sessions) == 2, "Expected 2 daily sessions"
    assert "2026-10-08" in sessions
    assert "2026-10-09" in sessions
    
    s1 = sessions["2026-10-08"]
    assert "poc_price" in s1
    assert "vah_price" in s1
    assert "val_price" in s1
    assert len(s1["bins"]) > 0


def test_tpo_market_profile(sample_intraday_session_df):
    engine = VolumeProfileEngine()
    tpo = engine.compute_tpo(sample_intraday_session_df, tick_size=1.0)

    assert tpo is not None
    assert isinstance(tpo, TPOResult)
    assert tpo.session_date == "2026-10-09"
    assert len(tpo.brackets) >= 2, "Expected multiple 30-min brackets"
    # Initial balance must be recorded
    assert tpo.ib_high >= tpo.ib_low
    # POC must be in price matrix
    assert tpo.poc_price in tpo.price_matrix
    assert len(tpo.price_matrix[tpo.poc_price]) > 0
