import pandas as pd
import numpy as np
from typing import List
from core.interfaces import IIndicator
from services.indicators.volatility import ATRIndicator


class SMAIndicator(IIndicator):
    """Simple Moving Average (SMA)."""

    def __init__(self, period: int = 20):
        self.period = period

    def name(self) -> str:
        return f"SMA_{self.period}"

    def required_columns(self) -> List[str]:
        return ["close"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            df[self.name()] = np.nan
            return df
        df[self.name()] = df['close'].rolling(window=self.period).mean()
        return df


class EMAIndicator(IIndicator):
    """Exponential Moving Average (EMA)."""

    def __init__(self, period: int = 20):
        self.period = period

    def name(self) -> str:
        return f"EMA_{self.period}"

    def required_columns(self) -> List[str]:
        return ["close"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            df[self.name()] = np.nan
            return df
        df[self.name()] = df['close'].ewm(span=self.period, adjust=False).mean()
        return df


class SupertrendIndicator(IIndicator):
    """Supertrend Trend-Following Indicator."""

    def __init__(self, period: int = 10, multiplier: float = 3.0):
        self.period = period
        self.multiplier = multiplier

    def name(self) -> str:
        return f"SUPERTREND_{self.period}_{self.multiplier}"

    def required_columns(self) -> List[str]:
        return ["high", "low", "close"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or len(df) < self.period:
            df[f"Supertrend_{self.period}"] = np.nan
            df[f"Supertrend_Direction_{self.period}"] = 0
            return df

        # Compute ATR
        atr_ind = ATRIndicator(period=self.period)
        temp_df = atr_ind.compute(df.copy())
        atr = temp_df[f"ATR_{self.period}"]

        hl2 = (df['high'] + df['low']) / 2.0
        basic_upper = hl2 + (self.multiplier * atr)
        basic_lower = hl2 - (self.multiplier * atr)

        final_upper = basic_upper.copy()
        final_lower = basic_lower.copy()
        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=int)

        close = df['close'].values
        b_upper = basic_upper.values
        b_lower = basic_lower.values
        f_upper = np.array(basic_upper.values, copy=True)
        f_lower = np.array(basic_lower.values, copy=True)
        st = np.zeros(len(df))
        dirs = np.zeros(len(df), dtype=int)

        dirs[0] = 1
        st[0] = b_lower[0]

        for i in range(1, len(df)):
            # Final Upper Band
            if b_upper[i] < f_upper[i-1] or close[i-1] > f_upper[i-1]:
                f_upper[i] = b_upper[i]
            else:
                f_upper[i] = f_upper[i-1]

            # Final Lower Band
            if b_lower[i] > f_lower[i-1] or close[i-1] < f_lower[i-1]:
                f_lower[i] = b_lower[i]
            else:
                f_lower[i] = f_lower[i-1]

            # Trend direction switch
            if dirs[i-1] == 1:
                if close[i] < f_lower[i]:
                    dirs[i] = -1
                    st[i] = f_upper[i]
                else:
                    dirs[i] = 1
                    st[i] = f_lower[i]
            else:
                if close[i] > f_upper[i]:
                    dirs[i] = 1
                    st[i] = f_lower[i]
                else:
                    dirs[i] = -1
                    st[i] = f_upper[i]

        df[f"Supertrend_{self.period}"] = st
        df[f"Supertrend_Direction_{self.period}"] = dirs
        return df
