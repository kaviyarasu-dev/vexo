import pytest
import pandas as pd
import numpy as np
from services.indicators.trend import SMAIndicator, EMAIndicator, SupertrendIndicator
from services.indicators.oscillators import StochasticOscillator


@pytest.fixture
def sample_ohlcv_df():
    # 50 periods of mock price series
    np.random.seed(42)
    n = 60
    prices = 100 + np.cumsum(np.random.randn(n) * 1.5)
    highs = prices + np.abs(np.random.randn(n) * 1.0)
    lows = prices - np.abs(np.random.randn(n) * 1.0)
    opens = prices - 0.2
    closes = prices + 0.2
    volumes = np.random.randint(1000, 50000, size=n)

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes
    })
    return df


def test_sma_indicator(sample_ohlcv_df):
    sma = SMAIndicator(period=20)
    df = sma.compute(sample_ohlcv_df.copy())
    assert "SMA_20" in df.columns
    assert np.isnan(df["SMA_20"].iloc[0])
    assert not np.isnan(df["SMA_20"].iloc[25])
    # Mathematical rolling mean verification
    expected_25 = sample_ohlcv_df["close"].iloc[6:26].mean()
    np.testing.assert_almost_equal(df["SMA_20"].iloc[25], expected_25)


def test_ema_indicator(sample_ohlcv_df):
    ema = EMAIndicator(period=20)
    df = ema.compute(sample_ohlcv_df.copy())
    assert "EMA_20" in df.columns
    assert not np.isnan(df["EMA_20"].iloc[20])
    # EMA responds faster to price than SMA on strong movement
    assert len(df["EMA_20"]) == len(sample_ohlcv_df)


def test_supertrend_indicator(sample_ohlcv_df):
    st = SupertrendIndicator(period=10, multiplier=3.0)
    df = st.compute(sample_ohlcv_df.copy())
    assert "Supertrend_10" in df.columns
    assert "Supertrend_Direction_10" in df.columns
    # Direction should be 1 (bullish) or -1 (bearish)
    valid_dirs = df["Supertrend_Direction_10"].dropna().unique()
    assert set(valid_dirs).issubset({1, -1})


def test_stochastic_oscillator(sample_ohlcv_df):
    stoch = StochasticOscillator(k_period=14, d_period=3, smooth=3)
    df = stoch.compute(sample_ohlcv_df.copy())
    assert "Stoch_K" in df.columns
    assert "Stoch_D" in df.columns
    
    # Stochastic values should be bounded between 0 and 100
    valid_k = df["Stoch_K"].dropna()
    assert (valid_k >= 0).all()
    assert (valid_k <= 100).all()
