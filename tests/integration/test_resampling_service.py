import pytest
import pandas as pd
from datetime import datetime
import pytz
import os

from services.resampling_service import ResamplingService
from services.indicator_service import IndicatorService
from services.indicators.vwap import SessionVWAP
from services.indicators.momentum import RSIIndicator, MACDIndicator
from db.connection import get_db

@pytest.fixture
def test_db():
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
    start = pd.Timestamp("2024-01-10 03:45:00", tz="UTC")
    timestamps = [start + pd.Timedelta(minutes=i) for i in range(375)]
    
    df = pd.DataFrame({
        "symbol": "NSE:RELIANCE-EQ",
        "timestamp": [t.tz_localize(None) for t in timestamps],
        "open": [100.0 + i for i in range(375)],
        "high": [101.0 + i for i in range(375)],
        "low": [99.0 + i for i in range(375)],
        "close": [100.5 + i for i in range(375)],
        "volume": [1000 for _ in range(375)]
    })
    
    db.execute_write_df("INSERT INTO candles_1m_adjusted SELECT * FROM _temp_input_table", df)
    yield db
    db.close()


def test_integration_resampling_and_indicators(test_db):
    resampler = ResamplingService(test_db)
    
    start = datetime(2024, 1, 10, 9, 15, tzinfo=pytz.timezone("Asia/Kolkata"))
    end = datetime(2024, 1, 10, 15, 30, tzinfo=pytz.timezone("Asia/Kolkata"))
    
    # Resample to 5m
    df_5m = resampler.resample("NSE:RELIANCE-EQ", "5m", start, end)
    
    # 375 minutes / 5 = 75 bars
    assert len(df_5m) == 75
    
    # Apply indicators
    ind_service = IndicatorService([
        SessionVWAP(),
        RSIIndicator(period=14),
        MACDIndicator()
    ])
    
    enriched = ind_service.compute_all(df_5m)
    
    assert "VWAP" in enriched.columns
    assert "RSI_14" in enriched.columns
    assert "MACD" in enriched.columns
