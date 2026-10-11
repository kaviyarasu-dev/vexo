import pandas as pd
import numpy as np
from typing import List
from core.interfaces import IIndicator

class LogReturnsCalculator(IIndicator):
    """Logarithmic Returns."""
    
    def name(self) -> str:
        return "Log_Return"

    def required_columns(self) -> List[str]:
        return ["close"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            df['Log_Return'] = np.nan
            return df
            
        df['Log_Return'] = np.log(df['close'] / df['close'].shift(1))
        return df


class VolumeZScoreCalculator(IIndicator):
    """Volume Z-Score."""
    
    def __init__(self, period: int = 20):
        self.period = period
        
    def name(self) -> str:
        return f"Volume_Z_{self.period}"

    def required_columns(self) -> List[str]:
        return ["volume"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            df[self.name()] = np.nan
            return df
            
        vol = df['volume']
        rolling_mean = vol.rolling(window=self.period).mean()
        rolling_std = vol.rolling(window=self.period).std(ddof=0)
        
        z_score = (vol - rolling_mean) / rolling_std
        z_score = z_score.replace([np.inf, -np.inf], np.nan)
        
        df[self.name()] = z_score
        return df
