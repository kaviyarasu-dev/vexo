import pandas as pd
import numpy as np
from typing import List
from core.interfaces import IIndicator

class RSIIndicator(IIndicator):
    """Relative Strength Index (RSI)."""
    
    def __init__(self, period: int = 14):
        self.period = period
        
    def name(self) -> str:
        return f"RSI_{self.period}"

    def required_columns(self) -> List[str]:
        return ["close"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or len(df) < self.period:
            df[self.name()] = np.nan
            return df
            
        delta = df['close'].diff()
        
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)
        
        # Wilder's Smoothing (Exponential Moving Average with alpha=1/period)
        avg_gain = gain.ewm(alpha=1/self.period, min_periods=self.period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/self.period, min_periods=self.period, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        
        # Handle division by zero
        rsi = np.where(avg_loss == 0, 100, 100 - (100 / (1 + rs)))
        
        df[self.name()] = pd.Series(rsi, index=df.index)
        return df


class MACDIndicator(IIndicator):
    """Moving Average Convergence Divergence (MACD)."""
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal
        
    def name(self) -> str:
        return f"MACD_{self.fast}_{self.slow}_{self.signal}"

    def required_columns(self) -> List[str]:
        return ["close"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            df['MACD'] = np.nan
            df['MACD_Signal'] = np.nan
            df['MACD_Hist'] = np.nan
            return df
            
        ema_fast = df['close'].ewm(span=self.fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.slow, adjust=False).mean()
        
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=self.signal, adjust=False).mean()
        hist = macd - signal
        
        df['MACD'] = macd
        df['MACD_Signal'] = signal
        df['MACD_Hist'] = hist
        
        return df
