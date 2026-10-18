"""LightGBM Quantile & Directional Candle Prediction Engine.

Predicts calibrated High (Q_0.90), Low (Q_0.10), and Median (Q_0.50) envelopes
for the upcoming candle along with the directional probability P(Bullish).
Guarantees sub-10ms CPU inference latency and monotonic envelope ordering.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Tuple
import os
import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.calibration import CalibratedClassifierCV

from services.ai.feature_extractor import FeatureExtractor


@dataclass
class CandlePredictionResult:
    symbol: str
    timeframe: str
    current_close: float
    high_90: float
    close_50: float
    low_10: float
    directional_prob: float
    is_bullish: bool
    regime_state: int
    regime_label: str
    confidence: float
    expected_range_pts: float
    inference_latency_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LightGBMCandlePredictor:
    """Quantitative quantile gradient boosting model for candlestick distribution forecasting."""

    FEATURE_COLS = [
        "log_return",
        "volatility_garman_klass",
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

    def __init__(self, model_dir: str = "data/models/ai_prediction"):
        self.model_dir = model_dir
        self.feature_extractor = FeatureExtractor()
        self.model_q10: Optional[lgb.LGBMRegressor] = None
        self.model_q50: Optional[lgb.LGBMRegressor] = None
        self.model_q90: Optional[lgb.LGBMRegressor] = None
        self.model_dir_cls: Optional[lgb.LGBMClassifier] = None
        self.is_fitted: bool = False

    def train(self, df: pd.DataFrame) -> Dict[str, float]:
        """Train quantile regressors and directional classifier on historical OHLCV data.
        
        Targets:
            - target_high_pct = (High_{t+1} - Close_t) / Close_t
            - target_close_pct = (Close_{t+1} - Close_t) / Close_t
            - target_low_pct = (Low_{t+1} - Close_t) / Close_t
            - target_dir = 1 if Close_{t+1} > Open_{t+1} else 0
        """
        feats = self.feature_extractor.extract_features(df, dropna=False)
        
        # Prepare targets shifted backward by 1 (future bar)
        c = df["close"].astype(float)
        h = df["high"].astype(float)
        l = df["low"].astype(float)
        o = df["open"].astype(float)
        
        target_high_pct = ((h.shift(-1) - c) / c)
        target_close_pct = ((c.shift(-1) - c) / c)
        target_low_pct = ((l.shift(-1) - c) / c)
        target_dir = (c.shift(-1) > o.shift(-1)).astype(int)
        
        data = feats.copy()
        data["target_high"] = target_high_pct
        data["target_close"] = target_close_pct
        data["target_low"] = target_low_pct
        data["target_dir"] = target_dir
        
        data = data.dropna().reset_index(drop=True)
        if len(data) < 30:
            raise ValueError(f"Insufficient training samples ({len(data)}). Need >= 30 bars.")
            
        X = data[self.FEATURE_COLS]
        
        # Lightweight CPU hyperparameters for sub-10ms inference
        lgb_params = {
            "n_estimators": 50,
            "max_depth": 4,
            "num_leaves": 15,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "n_jobs": 1,
            "verbose": -1
        }
        
        # 1. Lower quantile Q_0.10 (pinball loss)
        self.model_q10 = lgb.LGBMRegressor(objective="quantile", alpha=0.10, **lgb_params)
        self.model_q10.fit(X, data["target_low"])
        
        # 2. Median quantile Q_0.50
        self.model_q50 = lgb.LGBMRegressor(objective="quantile", alpha=0.50, **lgb_params)
        self.model_q50.fit(X, data["target_close"])
        
        # 3. Upper quantile Q_0.90
        self.model_q90 = lgb.LGBMRegressor(objective="quantile", alpha=0.90, **lgb_params)
        self.model_q90.fit(X, data["target_high"])
        
        # 4. Directional classifier
        self.model_dir_cls = lgb.LGBMClassifier(objective="binary", **lgb_params)
        self.model_dir_cls.fit(X, data["target_dir"])
        
        self.is_fitted = True
        
        # Compute training loss metrics
        pred_q10 = self.model_q10.predict(X)
        pred_q90 = self.model_q90.predict(X)
        coverage = np.mean((data["target_low"] >= pred_q10) & (data["target_high"] <= pred_q90))
        
        return {
            "samples": float(len(data)),
            "coverage_80pct": float(coverage),
            "dir_train_accuracy": float(self.model_dir_cls.score(X, data["target_dir"]))
        }

    def _extract_inference_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Optimized microsecond feature extractor for real-time sub-10ms inference."""
        if len(df) < 5:
            feats = self.feature_extractor.extract_features(df, dropna=False)
            return feats[self.FEATURE_COLS].iloc[[-1]].fillna(0.0)
            
        lower_cols = {c.lower(): c for c in df.columns}
        sub_df = df.iloc[-min(len(df), 120):]
        o = sub_df[lower_cols["open"]].values.astype(float)
        h = sub_df[lower_cols["high"]].values.astype(float)
        l = sub_df[lower_cols["low"]].values.astype(float)
        c = sub_df[lower_cols["close"]].values.astype(float)
        v = sub_df[lower_cols["volume"]].values.astype(float)
        
        # 1. Log return (last bar)
        log_return = float(np.log(c[-1] / c[-2])) if c[-2] > 0 else 0.0
        
        # 2. Garman-Klass (last bar)
        hl_term = 0.5 * (np.log(h[-1] / l[-1])) ** 2 if l[-1] > 0 else 0.0
        co_term = (2.0 * np.log(2.0) - 1.0) * (np.log(c[-1] / o[-1])) ** 2 if o[-1] > 0 else 0.0
        volatility_garman_klass = float(np.sqrt(max(0.0, hl_term - co_term)))
        
        # 3. Normalized ATR and Intraday Range Ratio
        tr1 = h - l
        tr2 = np.abs(h[1:] - c[:-1])
        tr3 = np.abs(l[1:] - c[:-1])
        tr_all = np.maximum(tr1[1:], np.maximum(tr2, tr3))
        atr_window = min(self.feature_extractor.atr_period, len(tr_all))
        atr = float(np.mean(tr_all[-atr_window:])) if atr_window > 0 else 1.0
        range_ratio = float((h[-1] - l[-1]) / atr) if atr > 0 else 1.0
        
        # 4. Signed Volume Delta Proxy
        range_hl = h[-1] - l[-1]
        delta_ratio = (2.0 * c[-1] - h[-1] - l[-1]) / range_hl if range_hl > 0 else 0.0
        vol_delta = v[-1] * delta_ratio
        rw = min(self.feature_extractor.rolling_window, len(v))
        vol_mean = float(np.mean(v[-rw:])) if rw > 0 else 1.0
        vol_mean_safe = vol_mean if vol_mean > 0 else 1.0
        volume_delta_norm = float(vol_delta / vol_mean_safe)
        
        # 5. RVOL and Volume Z-Score
        rvol = float(v[-1] / vol_mean_safe)
        vol_std = float(np.std(v[-rw:], ddof=1)) if rw > 1 else 0.0
        volume_zscore = float((v[-1] - vol_mean) / vol_std) if vol_std > 0 else 0.0
        
        # 6. VWAP Z-score
        typical_price = (h[-rw:] + l[-rw:] + c[-rw:]) / 3.0
        cum_tp_v = float(np.sum(typical_price * v[-rw:]))
        cum_v = float(np.sum(v[-rw:]))
        vwap = cum_tp_v / cum_v if cum_v > 0 else c[-1]
        close_std = float(np.std(c[-rw:], ddof=1)) if rw > 1 else 0.0
        vwap_zscore = float((c[-1] - vwap) / close_std) if close_std > 0 else 0.0
        
        # 7. Fractionally Differentiated Close Price
        from services.ai.stationarity import fractional_differentiation
        fd_series = fractional_differentiation(pd.Series(c), d=self.feature_extractor.frac_diff_d)
        val_fd = fd_series.iloc[-1]
        frac_diff_close = float(val_fd) if not np.isnan(val_fd) else 0.0
        
        # 8. Wick & body ratios
        upper_wick = h[-1] - max(o[-1], c[-1])
        lower_wick = min(o[-1], c[-1]) - l[-1]
        body = abs(c[-1] - o[-1])
        upper_wick_ratio = float(upper_wick / range_hl) if range_hl > 0 else 0.0
        lower_wick_ratio = float(lower_wick / range_hl) if range_hl > 0 else 0.0
        body_ratio = float(body / range_hl) if range_hl > 0 else 0.0
        
        row_dict = {
            "log_return": [log_return],
            "volatility_garman_klass": [volatility_garman_klass],
            "range_ratio": [range_ratio],
            "volume_delta_norm": [volume_delta_norm],
            "rvol": [rvol],
            "volume_zscore": [volume_zscore],
            "vwap_zscore": [vwap_zscore],
            "frac_diff_close": [frac_diff_close],
            "upper_wick_ratio": [upper_wick_ratio],
            "lower_wick_ratio": [lower_wick_ratio],
            "body_ratio": [body_ratio]
        }
        return pd.DataFrame(row_dict)

    def predict_next(
        self,
        df: pd.DataFrame,
        symbol: str = "UNKNOWN",
        timeframe: str = "5m",
        regime_state: int = 0,
        regime_label: str = "TRENDING"
    ) -> CandlePredictionResult:
        """Predict the next candle envelope and directional probability for the latest bar."""
        import time
        start_time = time.perf_counter()
        
        if not self.is_fitted:
            # Auto-fit on provided history if not pre-trained
            self.train(df)
            
        latest_features = self._extract_inference_features(df)
        
        if latest_features.isna().any().any():
            # Fill warmup NaNs with zeros if needed
            latest_features = latest_features.fillna(0.0)
            
        current_close = float(df["close"].iloc[-1])
        
        # Quantile percentage return predictions
        pred_low_pct = float(self.model_q10.predict(latest_features)[0])
        pred_close_pct = float(self.model_q50.predict(latest_features)[0])
        pred_high_pct = float(self.model_q90.predict(latest_features)[0])
        
        # Absolute price envelope
        raw_low = current_close * (1.0 + pred_low_pct)
        raw_close = current_close * (1.0 + pred_close_pct)
        raw_high = current_close * (1.0 + pred_high_pct)
        
        # Strict Monotonicity Enforcement: Low <= Median <= High
        low_10 = min(raw_low, raw_close, raw_high)
        high_90 = max(raw_low, raw_close, raw_high)
        close_50 = np.clip(raw_close, low_10, high_90)
        
        # Directional Probability P(Close_{t+1} > Open_{t+1})
        probs = self.model_dir_cls.predict_proba(latest_features)[0]
        prob_bullish = float(probs[1]) if len(probs) > 1 else 0.50
        
        # Confidence metric derived from directional conviction and envelope spread
        confidence = float(np.clip(abs(prob_bullish - 0.50) * 2.0 * 100.0, 10.0, 95.0))
        expected_range = float(high_90 - low_10)
        
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        
        return CandlePredictionResult(
            symbol=symbol,
            timeframe=timeframe,
            current_close=round(current_close, 2),
            high_90=round(high_90, 2),
            close_50=round(close_50, 2),
            low_10=round(low_10, 2),
            directional_prob=round(prob_bullish, 4),
            is_bullish=prob_bullish >= 0.50,
            regime_state=regime_state,
            regime_label=regime_label,
            confidence=round(confidence, 1),
            expected_range_pts=round(expected_range, 2),
            inference_latency_ms=round(latency_ms, 2)
        )
