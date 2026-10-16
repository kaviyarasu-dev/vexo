import pandas as pd
import numpy as np
from typing import List
from core.interfaces import IIndicator


class StochasticOscillator(IIndicator):
    """Stochastic Oscillator (%K, %D)."""

    def __init__(self, k_period: int = 14, d_period: int = 3, smooth: int = 3):
        self.k_period = k_period
        self.d_period = d_period
        self.smooth = smooth

    def name(self) -> str:
        return f"STOCH_{self.k_period}_{self.d_period}_{self.smooth}"

    def required_columns(self) -> List[str]:
        return ["high", "low", "close"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or len(df) < self.k_period:
            df["Stoch_K"] = np.nan
            df["Stoch_D"] = np.nan
            return df

        low_min = df['low'].rolling(window=self.k_period).min()
        high_max = df['high'].rolling(window=self.k_period).max()

        # Fast %K
        fast_k = 100 * ((df['close'] - low_min) / (high_max - low_min))
        # Handle zero division
        fast_k = fast_k.replace([np.inf, -np.inf], np.nan)

        # Slow / Smoothed %K
        k = fast_k.rolling(window=self.smooth).mean() if self.smooth > 1 else fast_k
        # %D is moving average of %K
        d = k.rolling(window=self.d_period).mean()

        df["Stoch_K"] = k
        df["Stoch_D"] = d
        return df
