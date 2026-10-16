import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import pytz


@dataclass
class VolumeProfileBin:
    price_level: float
    total_volume: float
    up_volume: float
    down_volume: float
    is_poc: bool
    is_in_value_area: bool


@dataclass
class VolumeProfileResult:
    poc_price: float
    vah_price: float
    val_price: float
    total_volume: float
    value_area_volume: float
    bins: List[VolumeProfileBin]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "poc_price": round(self.poc_price, 2),
            "vah_price": round(self.vah_price, 2),
            "val_price": round(self.val_price, 2),
            "total_volume": int(self.total_volume),
            "value_area_volume": int(self.value_area_volume),
            "bins": [asdict(b) for b in self.bins]
        }


@dataclass
class TPOBracket:
    letter: str
    start_time: str
    end_time: str
    high: float
    low: float


@dataclass
class TPOResult:
    session_date: str
    poc_price: float
    vah_price: float
    val_price: float
    ib_high: float # Initial balance high (first hour: brackets A + B)
    ib_low: float  # Initial balance low
    single_print_highs: List[float]
    single_print_lows: List[float]
    brackets: List[TPOBracket]
    price_matrix: Dict[float, List[str]] # price -> list of letters (e.g. ['A', 'B', 'C'])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_date": self.session_date,
            "poc_price": round(self.poc_price, 2),
            "vah_price": round(self.vah_price, 2),
            "val_price": round(self.val_price, 2),
            "ib_high": round(self.ib_high, 2),
            "ib_low": round(self.ib_low, 2),
            "single_print_highs": [round(p, 2) for p in self.single_print_highs],
            "single_print_lows": [round(p, 2) for p in self.single_print_lows],
            "brackets": [asdict(b) for b in self.brackets],
            "price_matrix": {f"{k:.2f}": v for k, v in self.price_matrix.items()}
        }


class VolumeProfileEngine:
    """Quantitative Volume Profile and Market Profile (TPO) Engine."""

    def __init__(self, default_rows: int = 70, default_value_area_pct: float = 0.70):
        self.default_rows = default_rows
        self.default_value_area_pct = default_value_area_pct

    def compute_profile(
        self,
        df: pd.DataFrame,
        num_rows: Optional[int] = None,
        value_area_pct: Optional[float] = None
    ) -> Optional[VolumeProfileResult]:
        """Vectorized price binning and 70% Value Area calculation."""
        if df.empty or len(df) < 2:
            return None

        rows = num_rows or self.default_rows
        va_pct = value_area_pct or self.default_value_area_pct

        min_price = float(df['low'].min())
        max_price = float(df['high'].max())
        price_range = max_price - min_price

        if price_range <= 0:
            return None

        bin_size = price_range / rows
        # Define bin edges
        bin_edges = np.linspace(min_price, max_price, rows + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0

        total_vols = np.zeros(rows, dtype=np.float64)
        up_vols = np.zeros(rows, dtype=np.float64)
        down_vols = np.zeros(rows, dtype=np.float64)

        closes = df['close'].values
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        volumes = df['volume'].values

        is_up = closes >= opens

        for i in range(len(df)):
            c_high = highs[i]
            c_low = lows[i]
            c_vol = volumes[i]

            if c_vol <= 0 or c_high == c_low:
                idx = min(int((c_low - min_price) / bin_size), rows - 1)
                idx = max(0, idx)
                total_vols[idx] += c_vol
                if is_up[i]:
                    up_vols[idx] += c_vol
                else:
                    down_vols[idx] += c_vol
                continue

            # Overlapping bins for candle range [low, high]
            start_bin = max(0, int((c_low - min_price) / bin_size))
            end_bin = min(rows - 1, int((c_high - min_price) / bin_size))
            num_covered = max(1, end_bin - start_bin + 1)
            vol_per_bin = c_vol / num_covered

            for b in range(start_bin, end_bin + 1):
                total_vols[b] += vol_per_bin
                if is_up[i]:
                    up_vols[b] += vol_per_bin
                else:
                    down_vols[b] += vol_per_bin

        # 1. Point of Control (POC)
        poc_idx = int(np.argmax(total_vols))
        poc_price = float(bin_centers[poc_idx])
        total_volume = float(np.sum(total_vols))

        if total_volume <= 0:
            return None

        target_va_vol = total_volume * va_pct

        # 2. Value Area Traversal (70% Rule expanding outward from POC)
        in_va = np.zeros(rows, dtype=bool)
        in_va[poc_idx] = True
        cum_va_vol = total_vols[poc_idx]

        idx_above = poc_idx + 1
        idx_below = poc_idx - 1

        while cum_va_vol < target_va_vol:
            vol_above = total_vols[idx_above] if idx_above < rows else 0.0
            vol_below = total_vols[idx_below] if idx_below >= 0 else 0.0

            if vol_above == 0.0 and vol_below == 0.0:
                break

            if vol_above >= vol_below and idx_above < rows:
                in_va[idx_above] = True
                cum_va_vol += vol_above
                idx_above += 1
            elif idx_below >= 0:
                in_va[idx_below] = True
                cum_va_vol += vol_below
                idx_below -= 1

        # Determine VAH and VAL
        va_indices = np.where(in_va)[0]
        vah_idx = int(np.max(va_indices))
        val_idx = int(np.min(va_indices))

        vah_price = float(bin_centers[vah_idx])
        val_price = float(bin_centers[val_idx])

        bins_list = []
        for i in range(rows):
            bins_list.append(VolumeProfileBin(
                price_level=round(float(bin_centers[i]), 2),
                total_volume=round(float(total_vols[i]), 2),
                up_volume=round(float(up_vols[i]), 2),
                down_volume=round(float(down_vols[i]), 2),
                is_poc=(i == poc_idx),
                is_in_value_area=bool(in_va[i])
            ))

        return VolumeProfileResult(
            poc_price=poc_price,
            vah_price=vah_price,
            val_price=val_price,
            total_volume=total_volume,
            value_area_volume=float(cum_va_vol),
            bins=bins_list
        )

    def compute_session_profiles(
        self,
        df: pd.DataFrame,
        num_rows: int = 50,
        value_area_pct: float = 0.70
    ) -> Dict[str, Dict[str, Any]]:
        """Computes separate volume profile for each trading session (IST date)."""
        if df.empty or 'timestamp' not in df.columns:
            return {}

        df_work = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df_work['timestamp']):
            df_work['timestamp'] = pd.to_datetime(df_work['timestamp'])

        if df_work['timestamp'].dt.tz is None:
            ts = df_work['timestamp'].dt.tz_localize('UTC')
        else:
            ts = df_work['timestamp']

        ist_dates = ts.dt.tz_convert('Asia/Kolkata').dt.strftime('%Y-%m-%d')
        df_work['session_date'] = ist_dates

        results = {}
        for session_date, group in df_work.groupby('session_date'):
            prof = self.compute_profile(group, num_rows=num_rows, value_area_pct=value_area_pct)
            if prof:
                results[str(session_date)] = prof.to_dict()

        return results

    def compute_tpo(
        self,
        df: pd.DataFrame,
        tick_size: float = 0.5,
        session_date: Optional[str] = None
    ) -> Optional[TPOResult]:
        """Computes 30-min Market Profile / TPO letter brackets (A-M) and Initial Balance."""
        if df.empty or 'timestamp' not in df.columns:
            return None

        df_work = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df_work['timestamp']):
            df_work['timestamp'] = pd.to_datetime(df_work['timestamp'])

        if df_work['timestamp'].dt.tz is None:
            ts = df_work['timestamp'].dt.tz_localize('UTC')
        else:
            ts = df_work['timestamp']

        ist_dt = ts.dt.tz_convert('Asia/Kolkata')
        df_work['ist_time'] = ist_dt
        df_work['date_str'] = ist_dt.dt.strftime('%Y-%m-%d')

        if session_date:
            session_df = df_work[df_work['date_str'] == session_date]
        else:
            # Latest session date
            latest_date = df_work['date_str'].iloc[-1]
            session_df = df_work[df_work['date_str'] == latest_date]
            session_date = str(latest_date)

        if session_df.empty:
            return None

        # NSE Brackets: A=09:15-09:45, B=09:45-10:15 ... M=15:15-15:30
        bracket_labels = "ABCDEFGHIJKLM"
        brackets = []
        price_matrix = {}

        # Round prices to tick size bins
        min_p = float(session_df['low'].min())
        max_p = float(session_df['high'].max())
        ticks = np.arange(np.floor(min_p / tick_size) * tick_size, (np.ceil(max_p / tick_size) + 1) * tick_size, tick_size)

        for p in ticks:
            price_matrix[round(float(p), 2)] = []

        # Partition into 30-min brackets
        ib_high = -float('inf')
        ib_low = float('inf')

        for b_idx in range(len(bracket_labels)):
            b_letter = bracket_labels[b_idx]
            # 30-min increments starting 09:15 IST
            start_min = 15 + (b_idx * 30)
            start_hour = 9 + (start_min // 60)
            start_min_mod = start_min % 60

            end_min = start_min + 30
            end_hour = 9 + (end_min // 60)
            end_min_mod = end_min % 60

            # Filter candles in this bracket window
            mask = (session_df['ist_time'].dt.hour * 60 + session_df['ist_time'].dt.minute >= (start_hour * 60 + start_min_mod)) & \
                   (session_df['ist_time'].dt.hour * 60 + session_df['ist_time'].dt.minute < (end_hour * 60 + end_min_mod))
            b_candles = session_df[mask]

            if b_candles.empty:
                continue

            b_high = float(b_candles['high'].max())
            b_low = float(b_candles['low'].min())

            # Initial Balance (first hour: Brackets A & B)
            if b_letter in ('A', 'B'):
                ib_high = max(ib_high, b_high)
                ib_low = min(ib_low, b_low)

            brackets.append(TPOBracket(
                letter=b_letter,
                start_time=f"{start_hour:02d}:{start_min_mod:02d}",
                end_time=f"{end_hour:02d}:{end_min_mod:02d}",
                high=b_high,
                low=b_low
            ))

            # Populate price matrix with this letter
            for p in ticks:
                if b_low <= p <= b_high:
                    pk = round(float(p), 2)
                    if b_letter not in price_matrix[pk]:
                        price_matrix[pk].append(b_letter)

        # Remove empty price levels
        price_matrix = {k: v for k, v in price_matrix.items() if len(v) > 0}
        if not price_matrix:
            return None

        # TPO POC: Price tick with highest letter count
        poc_price = max(price_matrix.keys(), key=lambda k: len(price_matrix[k]))

        # TPO Value Area (70% of total letters)
        total_letters = sum(len(v) for v in price_matrix.values())
        target_letters = total_letters * 0.70

        sorted_prices = sorted(price_matrix.keys())
        poc_idx = sorted_prices.index(poc_price)
        selected_va_prices = {poc_price}
        current_letters = len(price_matrix[poc_price])

        up_idx = poc_idx + 1
        down_idx = poc_idx - 1

        while current_letters < target_letters:
            let_up = len(price_matrix[sorted_prices[up_idx]]) if up_idx < len(sorted_prices) else 0
            let_down = len(price_matrix[sorted_prices[down_idx]]) if down_idx >= 0 else 0

            if let_up == 0 and let_down == 0:
                break

            if let_up >= let_down and up_idx < len(sorted_prices):
                selected_va_prices.add(sorted_prices[up_idx])
                current_letters += let_up
                up_idx += 1
            elif down_idx >= 0:
                selected_va_prices.add(sorted_prices[down_idx])
                current_letters += let_down
                down_idx -= 1

        vah_price = max(selected_va_prices)
        val_price = min(selected_va_prices)

        # Single Prints: Prices touched in only 1 bracket (buying/selling tails)
        single_prints = [p for p, letters in price_matrix.items() if len(letters) == 1]
        sp_highs = [p for p in single_prints if p > vah_price]
        sp_lows = [p for p in single_prints if p < val_price]

        return TPOResult(
            session_date=session_date,
            poc_price=poc_price,
            vah_price=vah_price,
            val_price=val_price,
            ib_high=ib_high if ib_high != -float('inf') else vah_price,
            ib_low=ib_low if ib_low != float('inf') else val_price,
            single_print_highs=sp_highs,
            single_print_lows=sp_lows,
            brackets=brackets,
            price_matrix=price_matrix
        )
