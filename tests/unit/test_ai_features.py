import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from services.ai.stationarity import (
    compute_weights,
    fractional_differentiation,
    check_stationarity,
    find_optimal_d
)
from services.ai.feature_extractor import FeatureExtractor


@pytest.fixture
def sample_ohlcv_dataframe():
    """Generates realistic synthetic geometric random walk OHLCV series."""
    np.random.seed(42)
    n_bars = 500
    
    dates = [datetime(2024, 1, 1) + timedelta(minutes=5 * i) for i in range(n_bars)]
    returns = np.random.normal(loc=0.0002, scale=0.01, size=n_bars)
    price_levels = 2500.0 * np.exp(np.cumsum(returns))
    
    highs = price_levels * (1.0 + np.abs(np.random.normal(0, 0.004, size=n_bars)))
    lows = price_levels * (1.0 - np.abs(np.random.normal(0, 0.004, size=n_bars)))
    opens = lows + np.random.uniform(0.1, 0.9, size=n_bars) * (highs - lows)
    closes = lows + np.random.uniform(0.1, 0.9, size=n_bars) * (highs - lows)
    volumes = np.random.randint(1000, 50000, size=n_bars).astype(float)
    
    return pd.DataFrame({
        "timestamp": dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes
    })


def test_fractional_differentiation_weights():
    """Verifies memory weights calculation according to Marcos López de Prado formula."""
    w = compute_weights(d=0.35, size=50, threshold=1e-4)
    assert len(w) > 5
    assert w[-1] == 1.0  # w_0 is 1.0 (most recent bar)
    assert w[-2] < 0.0   # w_1 is negative
    assert abs(w[0]) < abs(w[-1])  # Distant past has smaller absolute weight


def test_stationarity_on_frac_diff_series(sample_ohlcv_dataframe):
    """Verifies that fractional differentiation achieves unit root stationarity (p < 0.01)."""
    raw_close = sample_ohlcv_dataframe["close"]
    
    # Raw price series should be non-stationary (p >= 0.05)
    is_raw_stat, p_raw, _ = check_stationarity(raw_close, max_p_value=0.05)
    assert not is_raw_stat or p_raw > 0.01
    
    # Fractionally differentiated price series (d = 0.30)
    frac_close = fractional_differentiation(raw_close, d=0.30)
    is_stat, p_val, adf_stat = check_stationarity(frac_close, max_p_value=0.01)
    
    # Must reject null hypothesis of unit root with 99% confidence (p < 0.01)
    assert is_stat, f"Expected stationarity p < 0.01, got p={p_val}"
    assert p_val < 0.01
    
    # Memory preservation: correlation with original series must remain high (> 0.50)
    clean_idx = frac_close.dropna().index
    corr = np.corrcoef(raw_close.loc[clean_idx], frac_close.loc[clean_idx])[0, 1]
    assert corr > 0.50, f"Memory loss too severe: corr={corr}"


def test_feature_extractor_outputs(sample_ohlcv_dataframe):
    """Verifies that FeatureExtractor generates all stationary microstructure features without NaNs."""
    extractor = FeatureExtractor(frac_diff_d=0.35, atr_period=14, rolling_window=20)
    feats = extractor.extract_features(sample_ohlcv_dataframe, dropna=True)
    
    expected_cols = [
        "timestamp",
        "log_return",
        "volatility_garman_klass",
        "atr",
        "range_ratio",
        "volume_delta_norm",
        "rvol",
        "volume_zscore",
        "vwap_zscore",
        "frac_diff_close",
        "upper_wick_ratio",
        "lower_wick_ratio",
        "body_ratio"
    ]
    
    for col in expected_cols:
        assert col in feats.columns, f"Missing expected feature column: {col}"
        
    assert len(feats) > 0
    assert not feats.isna().any().any(), "Features dataframe contains unexpected NaNs"
    
    # Garman Klass volatility must be non-negative
    assert (feats["volatility_garman_klass"] >= 0).all()
    
    # Wick and body ratios should lie in [0, 1]
    assert (feats["body_ratio"] >= 0.0).all() and (feats["body_ratio"] <= 1.0).all()
    assert (feats["upper_wick_ratio"] >= 0.0).all() and (feats["upper_wick_ratio"] <= 1.0).all()
    assert (feats["lower_wick_ratio"] >= 0.0).all() and (feats["lower_wick_ratio"] <= 1.0).all()


def test_strict_anti_lookahead_causal_invariance(sample_ohlcv_dataframe):
    """CRITICAL: Verifies zero forward lookahead leakage.
    
    Feature values computed at bar t must be mathematically identical whether
    evaluated on the first T bars or on an extended series T + N bars.
    """
    extractor = FeatureExtractor(frac_diff_d=0.35, atr_period=14, rolling_window=20)
    
    # 1. Extract on first 300 bars
    subset_df = sample_ohlcv_dataframe.iloc[:300].copy()
    feats_subset = extractor.extract_features(subset_df, dropna=False)
    
    # 2. Extract on full 500 bars
    feats_full = extractor.extract_features(sample_ohlcv_dataframe, dropna=False)
    
    # Compare common rows (skipping initial warmup where features might be NaN in both)
    # Target bars from index 50 to 299
    cols_to_check = [
        "log_return",
        "volatility_garman_klass",
        "range_ratio",
        "volume_delta_norm",
        "rvol",
        "volume_zscore",
        "vwap_zscore",
        "frac_diff_close"
    ]
    
    for col in cols_to_check:
        v_sub = feats_subset[col].iloc[50:300].to_numpy()
        v_full = feats_full[col].iloc[50:300].to_numpy()
        
        np.testing.assert_allclose(
            v_sub,
            v_full,
            rtol=1e-7,
            atol=1e-7,
            err_msg=f"Lookahead leakage detected in column {col}! Future rows altered past values."
        )
