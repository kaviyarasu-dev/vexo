import pytest
import pandas as pd
from datetime import datetime
import pytz

from services.resampling_service import ResamplingService
from db.connection import get_db

@pytest.fixture
def mock_db():
    db = get_db(":memory:", reset=True)
    db.execute_write("""
        CREATE TABLE candles_1m_adjusted (
            symbol VARCHAR,
            timestamp TIMESTAMP,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume BIGINT
        )
    """)
    # Insert 100 candles from 09:15 to 10:54 IST
    # 09:15 IST = 03:45 UTC
    start = pd.Timestamp("2024-01-10 03:45:00", tz="UTC")
    timestamps = [start + pd.Timedelta(minutes=i) for i in range(100)]
    
    df = pd.DataFrame({
        "symbol": "NSE:RELIANCE-EQ",
        "timestamp": [t.tz_localize(None) for t in timestamps],
        "open": 100.0,
        "high": 101.0,
        "low": 99.0,
        "close": 100.0,
        "volume": 100
    })
    
    db.execute_write_df("INSERT INTO candles_1m_adjusted SELECT * FROM _temp_input_table", df)
    yield db
    db.close()


def test_resampling_5m(mock_db):
    service = ResamplingService(mock_db)
    
    start = datetime(2024, 1, 10, 9, 15, tzinfo=pytz.timezone("Asia/Kolkata"))
    end = datetime(2024, 1, 10, 15, 30, tzinfo=pytz.timezone("Asia/Kolkata"))
    
    df = service.resample("NSE:RELIANCE-EQ", "5m", start, end)
    
    # 375 minutes in a session -> 75 bars
    assert len(df) == 75
    
    # First 20 bars should have actual volume = 500 (100 * 5)
    assert df.iloc[0]["volume"] == 500
    assert not df.iloc[0]["is_zero_volume"]
    
    # Remaining bars should be zero volume
    assert df.iloc[20]["volume"] == 0
    assert df.iloc[20]["is_zero_volume"]
    assert df.iloc[20]["close"] == 100.0

def test_all_canonical_timeframes(mock_db):
    service = ResamplingService(mock_db)
    start = datetime(2024, 1, 10, 9, 15, tzinfo=pytz.timezone("Asia/Kolkata"))
    end = datetime(2024, 1, 10, 15, 30, tzinfo=pytz.timezone("Asia/Kolkata"))
    
    timeframes_lengths = {
        "5m": 75,
        "15m": 25,
        "30m": 13,
        "1h": 7,
        "2h": 4,
        "4h": 2
    }
    
    for tf, expected_len in timeframes_lengths.items():
        df = service.resample("NSE:RELIANCE-EQ", tf, start, end)
        assert len(df) == expected_len, f"{tf} expected {expected_len} bars, got {len(df)}"
