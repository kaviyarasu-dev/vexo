import pandas as pd
import numpy as np
from typing import List
from core.interfaces import IIndicator

class SessionVWAP(IIndicator):
    """Session Volume Weighted Average Price (VWAP).
    Resets at 09:15:00 IST every day.
    """
    
    def name(self) -> str:
        return "VWAP"

    def required_columns(self) -> List[str]:
        return ["timestamp", "high", "low", "close", "volume"]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            df['VWAP'] = np.nan
            return df
            
        # Ensure timestamp is datetime and localized to IST for grouping
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
        if df['timestamp'].dt.tz is None:
            # Assuming UTC if naive, as DuckDB returns naive UTC timestamps
            timestamps = df['timestamp'].dt.tz_localize('UTC')
        else:
            timestamps = df['timestamp']
            
        # Extract IST date for grouping (sessions reset at market open)
        session_dates = timestamps.dt.tz_convert('Asia/Kolkata').dt.date
        
        # Typical Price
        tp = (df['high'] + df['low'] + df['close']) / 3.0
        
        # Calculate cumulative typical price * volume and cumulative volume per session
        tp_v = tp * df['volume']
        
        cum_tp_v = tp_v.groupby(session_dates).cumsum()
        cum_v = df['volume'].groupby(session_dates).cumsum()
        
        # VWAP = Cumulative(TP * V) / Cumulative(V)
        df['VWAP'] = np.where(cum_v > 0, cum_tp_v / cum_v, np.nan)
        
        # If the first bar of the day has 0 volume, VWAP is just TP
        df['VWAP'] = df['VWAP'].fillna(tp)
        
        return df
