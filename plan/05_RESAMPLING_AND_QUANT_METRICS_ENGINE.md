# Phase 05: Resampling Engine & Quantitative Analytics Module

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "plan/00_MASTER_ARCHITECTURE.md"
    - "plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md"
  reads:
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#1-canonical-interface-registry"
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#2-canonical-timeframe-list"
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#3-canonical-time-conventions"
    - "plan/VERIFICATION_REPORT.md#27-duckdb-time_bucket-origin"
  produces:
    - "services/resampling_service.py"
    - "services/indicator_service.py"
    - "services/indicators/vwap.py"
    - "services/indicators/momentum.py"
    - "services/indicators/volatility.py"
  exposes:
    - "IResamplingService"
    - "IIndicator"
  must_not_modify:
    - "plan/*"
    - "core/rate_governor.py"
  test_plan:
    unit_tests: "tests/unit/test_resampling_math.py tests/unit/test_indicators.py"
    integration_tests: "tests/integration/test_resampling_service.py"
    contract_tests: "tests/contract/test_resampling_contract.py"
    fixtures: "tests/fixtures/reliance_1m_golden_day.json"
    command: "pytest tests/unit/test_resampling_math.py tests/unit/test_indicators.py -v"
  definition_of_done:
    - item: 1
      command: "python -c 'from services.resampling_service import ResamplingService; from db.connection import get_db; s = ResamplingService(get_db()); df = s.resample(\"NSE:RELIANCE-EQ\", \"5m\", start=\"2024-01-10T09:15:00\", end=\"2024-01-10T15:30:00\"); assert len(df) == 75 and df.iloc[0][\"timestamp\"].strftime(\"%H:%M\") == \"09:15\"'"
      result: "Resamples exactly 75 5m candles for a standard 375-minute session starting precisely at 09:15 IST."
    - item: 2
      command: "pytest tests/unit/test_resampling_math.py -k test_all_canonical_timeframes"
      result: "Golden fixture tests pass for all 11 timeframes (1m, 3m, 5m, 10m, 15m, 30m, 1h, 2h, 4h, 1D, 1W) with exact session boundaries."
    - item: 3
      command: "python -c 'from services.indicators.vwap import SessionVWAP; import pandas as pd; assert hasattr(SessionVWAP(), \"compute\")'"
      result: "Session VWAP computes typical price and resets cumulative sums at 09:15:00 IST daily."
  failure_modes_and_recovery:
    - failure: "Clock alignment drift (e.g. 5m bar starts at 09:10 or 09:20)"
      detection: "Assertion failure in test_resampling_math.py verifying bar open timestamp"
      recovery: "Ensure DuckDB time_bucket query uses origin TIMESTAMP '2000-01-01 03:45:00' (03:45 UTC = 09:15 IST)"
    - failure: "Survivorship or unadjusted split distortion during resampling"
      detection: "Extreme price gap (> 50%) detected across known corporate action date"
      recovery: "Resampling query defaults strictly to candles_1m_adjusted view"
  handoff:
    - "In-database resampling engine with session alignment operational."
    - "Quantitative indicator suite (VWAP, RSI, MACD, ATR, BB) implemented."
    - "Ready for Phase 06 automated daily incremental ingestion."
```

---

## 1. Goal & Scope
Build a high-performance in-database and vectorized analytics engine that resamples canonical 1-minute (`1m`) candles into any higher timeframe and computes essential quantitative indicators adhering to the 00A Canonical Registry.

This phase delivers:
- Precise time-bucket aggregation across all canonical timeframes (`3m`, `5m`, `10m`, `15m`, `30m`, `1h`, `2h`, `4h`, `1D`, `1W`) strictly aligned to the NSE market opening time (09:15:00 IST / 03:45:00 UTC).
- DuckDB SQL vectorized downsampling executing directly inside database memory.
- Default query source: `candles_1m_adjusted` (split-adjusted view), with support for raw unadjusted reads via `adjusted=False`.
- Zero-volume bar policy: empty periods are never forward-filled into raw storage; resampled empty buckets produce explicit `is_zero_volume = TRUE` bars with volume = 0 and previous close.
- Pluggable indicator suite (`IIndicator`) computing Session VWAP (session-reset at 09:15 IST), Moving Averages (SMA, EMA), Volatility (ATR, Bollinger Bands), Momentum (RSI, MACD), Log Returns, and Volume Z-Scores.
- Golden-fixture unit tests covering every canonical timeframe.

---

## 2. SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `ResamplingService`: Implements `IResamplingService`, solely responsible for aggregating 1m candles into higher-timeframe OHLCV bars.
  - `SessionBoundaryManager`: Solely responsible for mapping UTC timestamps to IST session grids and handling special Muhurat trading hours.
  - `IndicatorService`: Solely responsible for chaining mathematical indicators over resampled series.
- **Open/Closed Principle (OCP)**:
  - Indicators adhere to the `IIndicator` contract. Adding a new indicator requires creating a new class implementing `compute(df) -> df` without altering existing calculator code.
- **Interface Segregation Principle (ISP)**:
  - Decouple `IResamplingService` from `IIndicator`. Consumers requiring raw OHLCV bars never pay the computational cost of indicator processing.

---

## 3. NSE Market Hours & IST Resampling Mathematics

### 3.1. The Indian Session Alignment & UTC Offset Math
Standard Unix time-bucket algorithms group timestamps based on UTC `00:00:00` boundaries:
- Indian Standard Time (IST) is UTC+05:30.
- Standard NSE equity trading spans **09:15:00 to 15:30:00 IST** (375 minutes total).
- **Exact UTC Conversion**:
  $$09:15:00\text{ IST} - 05:30:00 = \mathbf{03:45:00\text{ UTC}}$$
  $$15:30:00\text{ IST} - 05:30:00 = \mathbf{10:00:00\text{ UTC}}$$
- Naive UTC bucketing divides from `00:00:00 UTC`, creating bars like `09:00-10:00` (combining 15 mins of actual trades with 45 mins of pre-market) and `10:00-11:00`. This is mathematically invalid for Indian market analysis.

### 3.2. DuckDB `time_bucket` with Explicit Session Origin
DuckDB's native `time_bucket` function accepts an explicit `origin` parameter. Setting origin to `TIMESTAMP '2000-01-01 03:45:00'` anchors every grid cleanly to 09:15:00 IST:

```sql
SELECT 
    symbol,
    time_bucket(INTERVAL '15 MINUTES', timestamp, TIMESTAMP '2000-01-01 03:45:00') AS bucket,
    arg_min(open, timestamp) AS open,
    max(high) AS high,
    min(low) AS low,
    arg_max(close, timestamp) AS close,
    sum(volume) AS volume
FROM candles_1m_adjusted
WHERE symbol = $symbol 
  AND timestamp >= $start_utc 
  AND timestamp <= $end_utc
GROUP BY symbol, bucket
ORDER BY bucket ASC;
```

### 3.3. Intraday Session Stub Bars Breakdown
Because 375 minutes is not evenly divisible by all hour intervals, standard exchange rules mandate session stub closing bars:
- **`5m`**: $375 / 5 = \mathbf{75\text{ bars/day}}$ (Zero stubs).
- **`15m`**: $375 / 15 = \mathbf{25\text{ bars/day}}$ (Zero stubs).
- **`30m`**: 12 full 30m bars ($12 \times 30 = 360\text{ mins}$) + **1 session stub bar of 15 mins** (`15:15 to 15:30 IST`). Total: **13 bars/day**.
- **`1h`**: 6 full 1h bars ($6 \times 60 = 360\text{ mins}$) + **1 session stub bar of 15 mins** (`15:15 to 15:30 IST`). Total: **7 bars/day**.
- **`2h`**: 3 full 2h bars ($3 \times 120 = 360\text{ mins}$) + **1 session stub bar of 15 mins** (`15:15 to 15:30 IST`). Total: **4 bars/day**.
- **`4h`**: 1 full 4h bar ($240\text{ mins}$, `09:15 to 13:15 IST`) + **1 session stub bar of 2h 15m** (`13:15 to 15:30 IST`). Total: **2 bars/day**.

### 3.4. Zero-Volume Bar Policy
If a stock does not trade during an intraday period:
1. No synthetic bars are inserted into `candles_1m_raw`.
2. When resampling to higher timeframes, if an entire bucket contains no trade records:
   - Resampler generates a bar with `open = prev_close`, `high = prev_close`, `low = prev_close`, `close = prev_close`, `volume = 0`.
   - Flags record with boolean `is_zero_volume = TRUE`.

---

## 4. Quantitative Indicators Specification

### 4.1. Session VWAP (Volume Weighted Average Price)
- **Mathematical Formula**:
  $$\text{Typical Price } (TP_t) = \frac{\text{High}_t + \text{Low}_t + \text{Close}_t}{3}$$
  $$\text{Session VWAP}_t = \frac{\sum_{i=\text{session\_start}}^{t} (TP_i \times \text{Volume}_i)}{\sum_{i=\text{session\_start}}^{t} \text{Volume}_i}$$
- **Session Reset Rule**: Cumulative sums strictly reset to 0 at `09:15:00 IST` (`03:45:00 UTC`) on every trading day. Rolling multi-day VWAP is prohibited.

### 4.2. Statistical Volatility & Returns
- **Log Returns**: $r_t = \ln(P_t / P_{t-1})$.
- **Percentage Returns**: $R_t = (P_t - P_{t-1}) / P_{t-1}$.
- **Average True Range (ATR, period=14)**:
  $$TR_t = \max(\text{High}_t - \text{Low}_t, |\text{High}_t - \text{Close}_{t-1}|, |\text{Low}_t - \text{Close}_{t-1}|)$$
  $$\text{ATR}_t = \text{WilderSmoothing}(TR, 14)$$
- **Bollinger Bands (20, 2.0)**:
  - Middle: 20-period SMA of Close.
  - Upper / Lower: Middle $\pm 2.0 \times \sigma_{20}$.
  - %B: $(\text{Close} - \text{Lower}) / (\text{Upper} - \text{Lower})$.

### 4.3. Momentum Indicators
- **RSI (Relative Strength Index, period=14)**: Wilder Exponential Smoothing of gains and losses.
- **MACD (12, 26, 9)**: Fast EMA(12) - Slow EMA(26); Signal Line = EMA(9, MACD).

---

## 5. Domain Contracts & Service Interfaces

```python
from abc import ABC, abstractmethod
from datetime import datetime
import pandas as pd

class IResamplingService(ABC):
    @abstractmethod
    def resample(
        self, 
        symbol: str, 
        target_timeframe: str, 
        start: datetime, 
        end: datetime, 
        adjusted: bool = True
    ) -> pd.DataFrame:
        """Resamples 1m data to target canonical timeframe with strict session alignment."""
        pass

class IIndicator(ABC):
    @abstractmethod
    def name(self) -> str:
        """Unique identifier of the indicator."""
        pass

    @abstractmethod
    def required_columns(self) -> list[str]:
        """Required input dataframe columns."""
        pass

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """Vectorized computation returning dataframe enriched with indicator columns."""
        pass
```

---

## 6. Implementation Steps
1. Create `services/resampling_service.py` implementing `IResamplingService`:
   - Builds parameterized DuckDB SQL queries utilizing `time_bucket(INTERVAL, timestamp, TIMESTAMP '2000-01-01 03:45:00')`.
   - Defaults to querying `candles_1m_adjusted`; toggles to `candles_1m_raw` when `adjusted=False`.
   - Implements post-aggregation session stub handler for 30m, 1h, 2h, 4h intervals.
2. Implement indicator classes under `services/indicators/`:
   - `vwap.py` (`SessionVWAP` with daily IST reset).
   - `momentum.py` (`RSIIndicator`, `MACDIndicator`).
   - `volatility.py` (`ATRIndicator`, `BollingerBandsIndicator`).
   - `returns.py` (`LogReturnsCalculator`, `VolumeZScoreCalculator`).
3. Build golden-fixture test suite comparing resampled candles against recorded exchange reference bars.

---

## 7. Verification & Acceptance Criteria
- 5m Resampling Verification: On a full trading session (`2024-01-10`), resampler produces exactly 75 candles starting at `09:15:00` and ending at `15:25:00 IST`.
- 1h Session Stub Test: 1-hour resampling produces exactly 7 bars, with the 7th bar covering `15:15:00 to 15:30:00 IST`.
- Mathematical Consistency: Resampled High equals `max(High)` of the constituent 1m candles; resampled Volume equals `sum(Volume)`.
- VWAP Reset Test: At 09:15 IST, VWAP equals Typical Price $(H+L+C)/3$; overnight volume does not bleed into the new session.
- Latency Benchmark: Resampling 500,000 1m candles into 5m bars with VWAP + RSI + MACD executes in $< 120\text{ ms}$.
