"""Stationarity engine using Fractional Differentiation (López de Prado methodology).

Preserves long-term price memory while removing unit roots to satisfy
stationarity constraints (ADF test p < 0.01) required for tabular machine learning.
"""

from typing import Tuple, Optional
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller


def compute_weights(d: float, size: int = 100, threshold: float = 1e-4) -> np.ndarray:
    """Compute expanding/fixed window memory weights for fractional differentiation.
    
    Formula:
        w_0 = 1.0
        w_k = -w_{k-1} * (d - k + 1) / k
        
    Args:
        d: Degree of fractional differentiation (0.0 <= d <= 1.0).
        size: Maximum number of historical lags to consider.
        threshold: Absolute weight cutoff below which memory is truncated.
        
    Returns:
        1D numpy array of weights ordered [w_K, w_{K-1}, ..., w_1, w_0] for convolution.
    """
    weights = [1.0]
    for k in range(1, size):
        w_k = -weights[-1] * (d - k + 1.0) / float(k)
        if abs(w_k) < threshold:
            break
        weights.append(w_k)
        
    return np.array(weights[::-1])  # Reversed for dot product / convolution with [X_{t-k}, ..., X_t]


def fractional_differentiation(
    series: pd.Series,
    d: float = 0.35,
    threshold: float = 1e-4,
    max_lags: int = 150
) -> pd.Series:
    """Compute fractionally differentiated series with fixed window memory.
    
    Strictly causal and anti-lookahead: for any bar t, the output consumes
    strictly values at or before t (X_t, X_{t-1}, ..., X_{t-K}).
    
    Args:
        series: Raw price series (e.g. Close prices).
        d: Fractional differentiation parameter (typically 0.30 - 0.45).
        threshold: Weight threshold for memory cutoff.
        max_lags: Maximum window size.
        
    Returns:
        Pandas Series of fractionally differentiated values with same index.
    """
    if d == 0.0:
        return series.copy()
    if d == 1.0:
        return series.diff()
        
    weights = compute_weights(d, size=min(len(series), max_lags), threshold=threshold)
    k = len(weights)
    
    values = series.to_numpy(dtype=float)
    diff_values = np.full_like(values, fill_value=np.nan)
    
    # Vectorized sliding window dot product
    for i in range(k - 1, len(values)):
        diff_values[i] = np.dot(weights, values[i - k + 1 : i + 1])
        
    return pd.Series(diff_values, index=series.index, name=f"frac_diff_{d}")


def check_stationarity(
    series: pd.Series,
    max_p_value: float = 0.01,
    autolag: str = "AIC"
) -> Tuple[bool, float, float]:
    """Execute Augmented Dickey-Fuller (ADF) test for unit root stationarity.
    
    H0 (Null Hypothesis): The series has a unit root (non-stationary).
    H1: The series is stationary.
    
    Args:
        series: Series to test.
        max_p_value: Significance threshold for rejection of H0 (default: 0.01 = 99% confidence).
        autolag: Method to determine lag order ('AIC', 'BIC', 't-stat', or None).
        
    Returns:
        Tuple of (is_stationary: bool, p_value: float, adf_statistic: float).
    """
    clean_series = series.dropna()
    if len(clean_series) < 20:
        return False, 1.0, 0.0
        
    try:
        res = adfuller(clean_series, autolag=autolag, result_object=True)
        adf_stat = float(res.statistic)
        p_value = float(res.pvalue)
    except TypeError:
        res = adfuller(clean_series, autolag=autolag)
        adf_stat = float(res[0])
        p_value = float(res[1])
    
    is_stationary = p_value < max_p_value
    return is_stationary, p_value, adf_stat


def find_optimal_d(
    series: pd.Series,
    d_candidates: Optional[np.ndarray] = None,
    max_p_value: float = 0.01
) -> float:
    """Find minimum fractional differentiation degree d that achieves stationarity.
    
    Minimizing d retains maximal memory / correlation with original price series.
    """
    if d_candidates is None:
        d_candidates = np.linspace(0.10, 0.90, 17)
        
    for d in d_candidates:
        diff_series = fractional_differentiation(series, d=float(d))
        is_stat, p_val, _ = check_stationarity(diff_series, max_p_value=max_p_value)
        if is_stat:
            return round(float(d), 2)
            
    return 1.0  # Fallback to integer first differences
