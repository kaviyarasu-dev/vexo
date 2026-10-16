import pytest
import pandas as pd
import numpy as np
from datetime import datetime, time

from services.indicators.vwap import SessionVWAP
from services.indicators.momentum import RSIIndicator, MACDIndicator
from services.indicators.volatility import ATRIndicator, BollingerBandsIndicator
from services.indicator_service import IndicatorService

def test_session_vwap():
    # Construct a tiny dataframe spanning 2 days
    dates = pd.date_range("2024-01-10 09:15:00", periods=3, freq="5min", tz="Asia/Kolkata").append(
            pd.date_range("2024-01-11 09:15:00", periods=2, freq="5min", tz="Asia/Kolkata"))
            
    df = pd.DataFrame({
        "timestamp": dates,
        "high": [105, 110, 108, 102, 105],
        "low": [95, 100, 102, 98, 100],
        "close": [100, 105, 105, 100, 102],
        "volume": [1000, 2000, 1500, 500, 1000]
    })
    
    vwap = SessionVWAP().compute(df)
    
    # Day 1 calculations
    tp1 = (105 + 95 + 100) / 3  # 100
    tp2 = (110 + 100 + 105) / 3 # 105
    tp3 = (108 + 102 + 105) / 3 # 105
    
    v1, v2, v3 = 1000, 2000, 1500
    
    expected_vwap_d1_bar1 = tp1
    expected_vwap_d1_bar2 = (tp1*v1 + tp2*v2) / (v1 + v2)
    expected_vwap_d1_bar3 = (tp1*v1 + tp2*v2 + tp3*v3) / (v1 + v2 + v3)
    
    # Day 2 calculations (should reset)
    tp4 = (102 + 98 + 100) / 3 # 100
    tp5 = (105 + 100 + 102) / 3 # 102.333
    v4, v5 = 500, 1000
    
    expected_vwap_d2_bar1 = tp4
    expected_vwap_d2_bar2 = (tp4*v4 + tp5*v5) / (v4 + v5)
    
    np.testing.assert_allclose(
        vwap["VWAP"].values, 
        [expected_vwap_d1_bar1, expected_vwap_d1_bar2, expected_vwap_d1_bar3, expected_vwap_d2_bar1, expected_vwap_d2_bar2]
    )

def test_rsi_indicator():
    # Increasing series should have high RSI
    df = pd.DataFrame({"close": np.linspace(100, 200, 30)})
    rsi = RSIIndicator(period=14).compute(df)
    assert not rsi["RSI_14"].isna().all()
    # It should be close to 100 because it's only gaining
    assert rsi["RSI_14"].iloc[-1] > 99.0

def test_indicator_service():
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-10 09:15:00", periods=50, freq="1D", tz="UTC"),
        "high": np.linspace(105, 150, 50),
        "low": np.linspace(95, 140, 50),
        "close": np.linspace(100, 145, 50),
        "volume": np.full(50, 1000)
    })
    
    service = IndicatorService([
        SessionVWAP(),
        RSIIndicator(period=14),
        MACDIndicator(),
        ATRIndicator(period=14),
        BollingerBandsIndicator()
    ])
    
    result = service.compute_all(df)
    assert "VWAP" in result.columns
    assert "RSI_14" in result.columns
    assert "MACD" in result.columns
    assert "ATR_14" in result.columns
    assert "BB_Middle" in result.columns
