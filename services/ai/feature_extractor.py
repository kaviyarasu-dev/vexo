"""Quantitative Microstructure Feature Extractor for AI Candlestick Prediction.

Extracts strictly stationary, scale-invariant engineered features from OHLCV data.
Guarantees zero forward lookahead bias: row t consumes strictly data <= t.
"""

from typing import Optional, List
import numpy as np
import pandas as pd

from services.ai.stationarity import fractional_differentiation


class FeatureExtractor:
    """Vectorized quantitative feature engineering engine."""

    def __init__(self, frac_diff_d: float = 0.35, atr_period: int = 14, rolling_window: int = 20):
        self.frac_diff_d = frac_diff_d
        self.atr_period = atr_period
        self.rolling_window = rolling_window

    def extract_features(self, df: pd.DataFrame, dropna: bool = True) -> pd.DataFrame:
        """Extract stationary quantitative features from raw or adjusted OHLCV data.
        
        Args:
            df: DataFrame containing columns: ['open', 'high', 'low', 'close', 'volume'].
            dropna: If True, purges initial warmup NaN rows.
            
        Returns:
            DataFrame with original timestamps/dates and engineered feature columns.
        """
        # Defensive validation
        required_cols = {'open', 'high', 'low', 'close', 'volume'}
        lower_cols = {c.lower(): c for c in df.columns}
        if not required_cols.issubset(lower_cols.keys()):
            missing = required_cols - set(lower_cols.keys())
            raise ValueError(f"Input DataFrame missing required OHLCV columns: {missing}")

        # Standardize working column names
        data = pd.DataFrame(index=df.index)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            data[col] = df[lower_cols[col]].astype(float)

        if 'timestamp' in lower_cols:
            data['timestamp'] = df[lower_cols['timestamp']]
        elif 'date' in lower_cols:
            data['date'] = df[lower_cols['date']]

        features = pd.DataFrame(index=df.index)
        if 'timestamp' in data.columns:
            features['timestamp'] = data['timestamp']
        elif 'date' in data.columns:
            features['date'] = data['date']

        o = data['open']
        h = data['high']
        l = data['low']
        c = data['close']
        v = data['volume']

        # 1. Log Returns
        features['log_return'] = np.log(c / c.shift(1))

        # 2. Garman-Klass Volatility: sigma_GK^2 = 0.5 * (ln(H/L))^2 - (2*ln(2) - 1) * (ln(C/O))^2
        hl_term = 0.5 * (np.log(h / l.replace(0, np.nan))) ** 2
        co_term = (2.0 * np.log(2.0) - 1.0) * (np.log(c / o.replace(0, np.nan))) ** 2
        gk_var = np.maximum(0.0, hl_term - co_term)
        features['volatility_garman_klass'] = np.sqrt(gk_var)

        # 3. Normalized ATR and Intraday Range Ratio
        tr1 = h - l
        tr2 = (h - c.shift(1)).abs()
        tr3 = (l - c.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=self.atr_period, min_periods=self.atr_period).mean()
        features['atr'] = atr
        features['range_ratio'] = np.where(atr > 0, (h - l) / atr, 1.0)

        # 4. Signed Volume Delta Proxy: V * ( (C - L) - (H - C) ) / (H - L)
        range_hl = h - l
        delta_ratio = np.where(range_hl > 0, (2.0 * c - h - l) / range_hl, 0.0)
        vol_delta = v * delta_ratio
        vol_mean = v.rolling(window=self.rolling_window, min_periods=1).mean().replace(0, 1.0)
        features['volume_delta_norm'] = vol_delta / vol_mean

        # 5. Relative Volume (RVOL) and Volume Z-Score
        vol_std = v.rolling(window=self.rolling_window, min_periods=self.rolling_window).std().replace(0, np.nan)
        features['rvol'] = v / vol_mean
        features['volume_zscore'] = np.where(vol_std > 0, (v - vol_mean) / vol_std, 0.0)

        # 6. Session / Rolling VWAP Z-score distance
        typical_price = (h + l + c) / 3.0
        cum_tp_v = (typical_price * v).rolling(window=self.rolling_window, min_periods=1).sum()
        cum_v = v.rolling(window=self.rolling_window, min_periods=1).sum().replace(0, np.nan)
        vwap = cum_tp_v / cum_v
        close_std = c.rolling(window=self.rolling_window, min_periods=self.rolling_window).std().replace(0, np.nan)
        features['vwap_zscore'] = np.where(close_std > 0, (c - vwap) / close_std, 0.0)

        # 7. Fractionally Differentiated Close Price (Memory preservation with stationarity)
        features['frac_diff_close'] = fractional_differentiation(c, d=self.frac_diff_d)

        # 8. Normalized Wick Geometry Ratios
        features['upper_wick_ratio'] = np.where(range_hl > 0, (h - np.maximum(o, c)) / range_hl, 0.0)
        features['lower_wick_ratio'] = np.where(range_hl > 0, (np.minimum(o, c) - l) / range_hl, 0.0)
        features['body_ratio'] = np.where(range_hl > 0, (c - o).abs() / range_hl, 0.0)

        if dropna:
            features = features.dropna().reset_index(drop=True)

        return features
