"""3-State Latent Market Regime Classifier for Candlestick Dynamics.

Classifies incoming market conditions into three latent market regimes:
- State 0: Low-Volatility Bullish Trend (BULLISH_TREND)
- State 1: High-Volatility Trend / Momentum Breakout (HIGH_VOL_TREND)
- State 2: Mean-Reverting Choppy / Sideways Range (CHOPPY_SIDEWAYS)

Used to condition candle forecasts and prevent fakeouts during choppy regimes.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture


@dataclass
class RegimeResult:
    state: int
    label: str
    description: str
    probabilities: Dict[str, float]
    volatility_level: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MarketRegimeClassifier:
    """3-State Gaussian Mixture Regime Detector."""

    STATE_LABELS = {
        0: ("BULLISH_TREND", "Low-Vol Bullish Trend - Momentum favors longs"),
        1: ("HIGH_VOL_TREND", "High-Vol Trend / Breakout - Explosive range expansions"),
        2: ("CHOPPY_SIDEWAYS", "Mean-Reverting Choppy - Fakeout risk high, favor range boundaries")
    }

    def __init__(self, random_state: int = 42):
        self.gmm = GaussianMixture(n_components=3, covariance_type="full", random_state=random_state)
        self.is_fitted: bool = False
        self.state_map: Dict[int, int] = {0: 0, 1: 1, 2: 2}

    def _extract_regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        c = df["close"].astype(float)
        h = df["high"].astype(float)
        l = df["low"].astype(float)
        o = df["open"].astype(float)

        log_ret = np.log(c / c.shift(1))
        
        # Garman Klass proxy
        hl = np.log(h / l.replace(0, np.nan)) ** 2
        co = np.log(c / o.replace(0, np.nan)) ** 2
        gk_vol = np.sqrt(np.maximum(0.0, 0.5 * hl - (2.0 * np.log(2.0) - 1.0) * co))
        
        # Rolling realized volatility (20 bars)
        roll_vol = log_ret.rolling(20, min_periods=5).std().fillna(0.0)
        roll_ret = log_ret.rolling(20, min_periods=5).mean().fillna(0.0)

        feats = pd.DataFrame({
            "return": roll_ret,
            "volatility": gk_vol.fillna(0.0),
            "roll_vol": roll_vol
        })
        return feats.fillna(0.0)

    def fit(self, df: pd.DataFrame) -> "MarketRegimeClassifier":
        """Fit 3-state Gaussian mixture model and map states deterministically."""
        X = self._extract_regime_features(df)
        if len(X) < 30:
            self.is_fitted = True
            return self

        self.gmm.fit(X)
        self.is_fitted = True

        # Order states by volatility and mean return:
        # Cluster with lowest vol and positive return -> State 0 (BULLISH_TREND)
        # Cluster with highest vol -> State 1 (HIGH_VOL_TREND)
        # Remaining -> State 2 (CHOPPY_SIDEWAYS)
        means = self.gmm.means_
        vols = means[:, 1]
        rets = means[:, 0]

        high_vol_idx = int(np.argmax(vols))
        remaining = [i for i in range(3) if i != high_vol_idx]
        
        if rets[remaining[0]] >= rets[remaining[1]]:
            bull_idx, chop_idx = remaining[0], remaining[1]
        else:
            bull_idx, chop_idx = remaining[1], remaining[0]

        self.state_map = {
            bull_idx: 0,
            high_vol_idx: 1,
            chop_idx: 2
        }
        return self

    def predict_regime(self, df: pd.DataFrame) -> RegimeResult:
        """Classify the latest candle bar into active latent market regime."""
        if not self.is_fitted:
            self.fit(df)

        X = self._extract_regime_features(df)
        latest_x = X.iloc[[-1]]

        probs = self.gmm.predict_proba(latest_x)[0]
        raw_state = int(np.argmax(probs))
        mapped_state = self.state_map.get(raw_state, 0)

        label, desc = self.STATE_LABELS[mapped_state]

        # Re-map probabilities according to state map
        prob_dict = {
            self.STATE_LABELS[self.state_map[i]][0]: round(float(probs[i]), 4)
            for i in range(3)
        }

        # Volatility level description
        current_vol = float(latest_x["volatility"].iloc[0])
        if current_vol < 0.005:
            vol_level = "LOW"
        elif current_vol < 0.015:
            vol_level = "MODERATE"
        else:
            vol_level = "ELEVATED"

        return RegimeResult(
            state=mapped_state,
            label=label,
            description=desc,
            probabilities=prob_dict,
            volatility_level=vol_level
        )
