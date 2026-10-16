import pandas as pd
from datetime import datetime, time
import pytz
from typing import Optional

from core.interfaces import IResamplingService
from db.connection import DuckDBConnectionManager

class ResamplingService(IResamplingService):
    def __init__(self, db: DuckDBConnectionManager):
        self.db = db

    def _get_interval_sql(self, timeframe: str) -> str:
        mapping = {
            "3m": "3 MINUTES",
            "5m": "5 MINUTES",
            "10m": "10 MINUTES",
            "15m": "15 MINUTES",
            "30m": "30 MINUTES",
            "1h": "1 HOUR",
            "2h": "2 HOURS",
            "4h": "4 HOURS",
            "1D": "1 DAY",
            "1W": "7 DAYS"
        }
        return mapping.get(timeframe, "1 MINUTE")

    def resample(
        self, 
        symbol: str, 
        target_timeframe: str, 
        start: datetime, 
        end: datetime, 
        adjusted: bool = True
    ) -> pd.DataFrame:
        table_name = "candles_1m_adjusted" if adjusted else "candles_1m_raw"
        
        # Format timestamps in UTC for DB queries
        start_utc_str = start.astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')
        end_utc_str = end.astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')

        if target_timeframe == "1m":
            query = f"""
                SELECT timestamp, open, high, low, close, volume, 
                       CAST(0 AS BOOLEAN) AS is_zero_volume
                FROM {table_name}
                WHERE symbol = ?
                  AND timestamp >= ?
                  AND timestamp <= ?
                ORDER BY timestamp ASC
            """
            cursor = self.db.get_read_cursor()
            try:
                df = cursor.execute(query, [symbol, start_utc_str, end_utc_str]).df()
            finally:
                cursor.close()
        else:
            interval_sql = self._get_interval_sql(target_timeframe)
            query = f"""
                SELECT 
                    time_bucket(INTERVAL '{interval_sql}', timestamp, TIMESTAMP '2000-01-01 03:45:00') AS timestamp,
                    arg_min(open, timestamp) AS open,
                    max(high) AS high,
                    min(low) AS low,
                    arg_max(close, timestamp) AS close,
                    sum(volume) AS volume
                FROM {table_name}
                WHERE symbol = ?
                  AND timestamp >= ?
                  AND timestamp <= ?
                GROUP BY 1
                ORDER BY 1 ASC
            """
            cursor = self.db.get_read_cursor()
            try:
                df = cursor.execute(query, [symbol, start_utc_str, end_utc_str]).df()
            finally:
                cursor.close()
                
            df['is_zero_volume'] = False

        if df.empty and target_timeframe in ("1D", "1W"):
            d_table = "candles_1d_adjusted" if adjusted else "candles_1d_raw"
            d_query = f"""
                SELECT CAST(date AS TIMESTAMP) + INTERVAL '3 HOURS 45 MINUTES' AS timestamp,
                       open, high, low, close, volume,
                       CAST(0 AS BOOLEAN) AS is_zero_volume
                FROM {d_table}
                WHERE symbol = ?
                  AND date >= CAST(? AS DATE)
                  AND date <= CAST(? AS DATE)
                ORDER BY date ASC
            """
            cursor = self.db.get_read_cursor()
            try:
                df = cursor.execute(d_query, [symbol, start_utc_str, end_utc_str]).df()
            except Exception:
                pass
            finally:
                cursor.close()

        if df.empty:
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'is_zero_volume'])

            
        # Ensure timestamp is UTC localized so we can manipulate it properly
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC')

        # Gap filling using Pandas (as chosen via /grill-me Option A)
        # We only do gap filling for intraday timeframes
        if target_timeframe not in ["1D", "1W"]:
            df = self._fill_intraday_gaps(df, target_timeframe)

        return df

    def _fill_intraday_gaps(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Forward fill gaps representing periods with zero trades within the market session."""
        if df.empty:
            return df
            
        # Get unique trading days in IST from the existing data
        df['date_ist'] = df['timestamp'].dt.tz_convert('Asia/Kolkata').dt.date
        unique_dates = df['date_ist'].unique()
        
        # Build the exact expected session buckets for these days
        # E.g., for 5m, we want 09:15 to 15:25
        freq = timeframe.replace('m', 'min').replace('h', 'h')
        
        all_expected_times = []
        for d in unique_dates:
            # 09:15 IST
            session_start = pd.Timestamp(datetime.combine(d, time(9, 15))).tz_localize('Asia/Kolkata')
            # 15:30 IST
            session_end = pd.Timestamp(datetime.combine(d, time(15, 30))).tz_localize('Asia/Kolkata')
            
            # Generate the time grid
            grid = pd.date_range(start=session_start, end=session_end, freq=freq, inclusive='left')
            # Also handle stub bars - if the grid doesn't cleanly divide 375 minutes
            # Pandas date_range with inclusive='left' correctly stops before or exactly at session_end.
            # But wait, for 1h, it goes 09:15, 10:15, 11:15, 12:15, 13:15, 14:15, 15:15. This is 7 bars.
            # This is exactly correct!
            
            # Convert back to UTC for merging
            grid_utc = grid.tz_convert('UTC')
            all_expected_times.extend(grid_utc)
            
        expected_idx = pd.DatetimeIndex(all_expected_times)
        
        # Set index and reindex
        df = df.set_index('timestamp')
        df = df.reindex(expected_idx)
        
        # Mark zero volume
        is_missing = df['open'].isna()
        
        # Forward fill close price to all OHLC
        df['close'] = df['close'].ffill()
        df['open'] = df['open'].fillna(df['close'])
        df['high'] = df['high'].fillna(df['close'])
        df['low'] = df['low'].fillna(df['close'])
        
        df['volume'] = df['volume'].fillna(0)
        df['is_zero_volume'] = df['is_zero_volume'].fillna(True)
        # Existing data where volume was 0 (if any) should also be flagged
        df.loc[df['volume'] == 0, 'is_zero_volume'] = True
        
        # Cleanup
        df = df.reset_index().rename(columns={'index': 'timestamp'})
        df = df.drop(columns=['date_ist'], errors='ignore')
        
        return df
