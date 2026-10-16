import pandas as pd
import numpy as np
from typing import List
from core.interfaces import IIndicator

class ATRIndicator(IIndicator):
    """Average True Range (ATR)."""
    
    def __init__(self, period: int = 14):
        self.period = period
        
    def name(self) -> str:
        return f"ATR_{self.period}"

    def required_columns(self) -> List[str]:
        return ["high", "low", "close"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or len(df) < 1:
            df[self.name()] = np.nan
            return df
            
        high = df['high']
        low = df['low']
        prev_close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Wilder's Smoothing (Exponential Moving Average with alpha=1/period)
        atr = tr.ewm(alpha=1/self.period, min_periods=self.period, adjust=False).mean()
        
        df[self.name()] = atr
        return df


class BollingerBandsIndicator(IIndicator):
    """Bollinger Bands."""
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev
        
    def name(self) -> str:
        return f"BB_{self.period}_{self.std_dev}"

    def required_columns(self) -> List[str]:
        return ["close"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            df['BB_Middle'] = np.nan
            df['BB_Upper'] = np.nan
            df['BB_Lower'] = np.nan
            df['BB_PctB'] = np.nan
            return df
            
        middle = df['close'].rolling(window=self.period).mean()
        std = df['close'].rolling(window=self.period).std(ddof=0)
        
        upper = middle + (std * self.std_dev)
        lower = middle - (std * self.std_dev)
        
        # %B
        pct_b = (df['close'] - lower) / (upper - lower)
        
        # Handle division by zero
        pct_b = pct_b.replace([np.inf, -np.inf], np.nan)
        
        df['BB_Middle'] = middle
        df['BB_Upper'] = upper
        df['BB_Lower'] = lower
        df['BB_PctB'] = pct_b
        
        return df
