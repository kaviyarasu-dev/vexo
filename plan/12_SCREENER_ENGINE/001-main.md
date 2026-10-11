# Phase 12: High-Performance Multi-Factor Screener Engine

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "plan/00_MASTER_ARCHITECTURE.md"
    - "plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md"
    - "plan/03_SYMBOL_MASTER_AND_UNIVERSE_MANAGER.md"
    - "plan/05_RESAMPLING_AND_QUANT_METRICS_ENGINE.md"
  reads:
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#1-canonical-interface-registry"
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#4-canonical-database-schema-registry"
    - "plan/OPEN_QUESTIONS.md#1-open-questions-matrix"
  produces:
    - "services/screener_service.py"
    - "api/v1/screener.py"
    - "static/js/screener_view.js"
    - "config/screener_templates.json"
  exposes:
    - "IScreenerService"
  must_not_modify:
    - "plan/*"
    - "core/rate_governor.py"
  test_plan:
    unit_tests: "tests/unit/test_screener_filters.py"
    integration_tests: "tests/integration/test_screener_execution.py"
    contract_tests: "tests/contract/test_screener_contract.py"
    fixtures: "config/screener_templates.json"
    command: "pytest tests/unit/test_screener_filters.py tests/integration/test_screener_execution.py -v"
  definition_of_done:
    - item: 1
      command: "python -c 'from services.screener_service import ScreenerService; from db.connection import get_db; s = ScreenerService(get_db()); res = s.run_screener(template=\"52_WEEK_HIGH\", universe=\"NIFTY500\"); assert isinstance(res, list)'"
      result: "Executes 52-week high scan on Nifty 500 in < 2.0 seconds returning structured matches."
    - item: 2
      command: "pytest tests/integration/test_screener_execution.py -k test_screener_performance_benchmark"
      result: "Full Nifty 500 multi-factor scan executes in under 2.0 seconds on baseline hardware."
    - item: 3
      command: "python -c 'from services.screener_service import ScreenerService; from db.connection import get_db; s = ScreenerService(get_db()); res = s.run_screener(as_of_date=\"2023-12-29\"); assert all(r.as_of_date == \"2023-12-29\" for r in res)'"
      result: "Historical 'as of' date correctly evaluates state without lookahead bias."
  failure_modes_and_recovery:
    - failure: "Fundamental data file (data/fundamentals_latest.csv) missing"
      detection: "FileNotFoundError when loading fundamental attributes"
      recovery: "Gracefully disable fundamental filter chips with UI tooltip: 'Fundamental metrics not imported. Operating on technical & volume filters.'"
    - failure: "Screener timeout on large unindexed universe scan"
      detection: "Execution time exceeds 3.0 seconds"
      recovery: "Ensure screener SQL operates directly on DuckDB columnar aggregates using pre-filtered symbols WHERE tier <= 3"
  handoff:
    - "IScreenerService operational with 3 pre-built templates."
    - "One-click jump to chart and export integration verified."
    - "Ready for Phase 13 alerts and watchlists implementation."
```

---

## 1. Goal & User Jobs Served
Build an institutional-grade, in-database multi-factor screening engine allowing users to discover trading and investment setups across the NSE universe adhering to the 00A Canonical Registry.

### Core User Jobs:
1. **Find (Retail Beginner)**: "Show me large, liquid companies near 52-week highs or oversold with a single click."
2. **Find (Quant Researcher)**: "Screen 500 stocks across custom multi-factor rules (e.g. Volume Z-Score $> 2.0$, Price $> 20\text{ EMA}$, Daily RSI $< 40$) in under 2.0 seconds."
3. **Workflow Continuity**: "Let me jump directly from a screener result row into its full interactive chart with 1 click."

---

## 2. SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `ScreenerService`: Implements `IScreenerService`, solely responsible for parsing filter trees, translating them into DuckDB SQL analytical queries, and executing scans.
  - `ScreenerTemplateRegistry`: Responsible solely for storing and validating pre-built scan templates and custom user presets.
- **Open/Closed Principle (OCP)**:
  - Filter criteria follow an expression-tree model (`ScreenerCondition`). Adding new mathematical conditions requires registering an operator evaluator without rewriting query generation.
- **Dependency Inversion Principle (DIP)**:
  - The screener engine queries DuckDB via repository abstractions and operates over dynamic views (`candles_1d_adjusted`, `symbols`).

---

## 3. Filter Criteria & Fundamental Data Handling

### 3.1. Supported Filter Dimensions
1. **Technical Filters**:
   - Price vs Moving Average: `Close > SMA(20)`, `Close > EMA(200)`.
   - Momentum: `RSI(14) < 30` (Oversold), `RSI(14) > 70` (Overbought).
   - Price Extremes: Within $X\%$ of 52-Week High or 52-Week Low:
     $$\text{Distance from 52W High} = \frac{\text{52W High} - Close}{\text{52W High}} \le 0.02$$
   - Volatility: Bollinger Bands `%B < 0.1` or Bandwidth contraction.
2. **Liquidity & Volume Filters**:
   - Volume Surge: Volume Z-Score $> 2.0$ relative to 20-day rolling baseline:
     $$Z = \frac{\text{Volume}_t - \mu_{V, 20}}{\sigma_{V, 20}} > 2.0$$
   - Average Daily Turnover (ADT): $\text{ADT}_{30} \ge ₹25\text{ Crores}$ ($250,000,000$).
3. **Universe Filters**:
   - Nifty 50, Nifty Next 50, Nifty Midcap 150, Nifty Smallcap 250, or Full Nifty 500.

### 3.2. Fundamental Data Policy (Settling OQ-06)
- **Source**: Fyers Data API does not provide comprehensive corporate fundamental ratios (P/E, Debt/Equity, ROCE).
- **Architecture**:
  - The system natively supports external fundamental ingestion via local CSV (`data/fundamentals_latest.csv`) or Bhavcopy delivery statistics (`sec_bhavdata_full.csv`).
  - **Graceful Degradation**: If `data/fundamentals_latest.csv` is absent, fundamental filter chips in the UI are cleanly disabled with an informative tooltip:
    `"Fundamental data not loaded. Screener is operating on 100% verified technical and volume data."`
  - The engine never crashes or fails when fundamental feeds are absent.

---

## 4. Pre-Built 1-Click Templates & Presets (`config/screener_templates.json`)

```json
{
  "templates": [
    {
      "id": "volume_surge",
      "name": "Volume Surge Alert",
      "persona": "both",
      "description": "Stocks experiencing trading volume more than 2 standard deviations above their 20-day average.",
      "conditions": [
        { "field": "volume_zscore_20", "operator": ">=", "value": 2.0 },
        { "field": "turnover_today", "operator": ">=", "value": 100000000 }
      ]
    },
    {
      "id": "52_week_high",
      "name": "52-Week High Breakout",
      "persona": "both",
      "description": "High-momentum leaders trading within 2% of their 52-week peak.",
      "conditions": [
        { "field": "dist_from_52w_high_pct", "operator": "<=", "value": 2.0 },
        { "field": "tier", "operator": "<=", "value": 3 }
      ]
    },
    {
      "id": "rsi_oversold",
      "name": "RSI Oversold Bounce Candidates",
      "persona": "both",
      "description": "Quality Nifty 500 stocks with Daily RSI under 30 indicating potential mean-reversion opportunity.",
      "conditions": [
        { "field": "rsi_14", "operator": "<=", "value": 30.0 },
        { "field": "tier", "operator": "<=", "value": 3 }
      ]
    }
  ]
}
```

---

## 5. Execution Rules & Performance Architecture

### 5.1. "As Of" Date Definition
Users can run scans against today's live/closing market state OR historically as of any trading day:
- `as_of_date`: Date string (`YYYY-MM-DD`). Defaults to latest ingested trading session.
- Allows quantitative researchers to backtest scan reliability (e.g. *"Show me what stocks met the 52-week high scan on 2023-10-15"*).

### 5.2. Adjusted-Price Rule
All price-based metrics (moving averages, 52W highs, RSI) are computed strictly against `candles_1d_adjusted` view. Unadjusted raw data is never used for screener calculations to prevent false split signals (e.g. a 10:1 split appearing as a -90% drop).

### 5.3. Performance Target (< 2.0s on Nifty 500)
To achieve sub-2-second execution across 500 stocks:
- The screener builds a single vectorized SQL window query in DuckDB executing over the columnar store:
  ```sql
  WITH daily_metrics AS (
      SELECT 
          symbol,
          date,
          close,
          volume,
          close * volume AS turnover,
          max(high) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 250 PRECEDING AND CURRENT ROW) AS high_52w,
          avg(close) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS sma_20,
          avg(volume) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS vol_avg_20,
          stddev(volume) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS vol_std_20
      FROM candles_1d_adjusted
      WHERE date <= $as_of_date
  )
  SELECT 
      m.symbol,
      s.name,
      s.category,
      m.close,
      m.turnover,
      (m.high_52w - m.close) / m.high_52w * 100 AS dist_from_52w_high_pct,
      (m.volume - m.vol_avg_20) / NULLIF(m.vol_std_20, 0) AS volume_zscore_20
  FROM daily_metrics m
  JOIN symbols s ON m.symbol = s.symbol
  WHERE m.date = $as_of_date AND s.tier <= 3
    AND (m.high_52w - m.close) / m.high_52w * 100 <= 2.0;
  ```
- Executes directly in C++ DuckDB engine in $< 450\text{ ms}$.

---

## 6. Interface Contract (`core/interfaces.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class ScreenerFilter:
    universe: str                     # "NIFTY50", "NIFTY500", "ALL"
    as_of_date: Optional[str] = None  # None = Latest session
    technical_rules: List[Dict[str, Any]] = None
    min_turnover_cr: float = 0.0

@dataclass
class ScreenerMatch:
    symbol: str
    name: str
    category: str
    close: float
    turnover_cr: float
    matched_rules: List[str]
    as_of_date: str

class IScreenerService(ABC):
    @abstractmethod
    def run_screener(self, filter_params: ScreenerFilter) -> List[ScreenerMatch]:
        """Executes multi-factor scan in DuckDB and returns matching symbols."""
        pass

    @abstractmethod
    def save_preset(self, name: str, filter_params: ScreenerFilter) -> str:
        """Saves custom filter criteria into screener_presets table."""
        pass

    @abstractmethod
    def list_presets(self) -> List[Dict[str, Any]]:
        """Returns pre-built and custom saved screener templates."""
        pass
```

---

## 7. Implementation Steps
1. Create `config/screener_templates.json` with the 3 canonical pre-built templates.
2. Implement `services/screener_service.py` (`IScreenerService`):
   - Builds vectorized DuckDB SQL queries utilizing window functions.
   - Evaluates against `candles_1d_adjusted`.
3. Implement `api/v1/screener.py` exposing:
   - `POST /api/v1/screener/run`
   - `GET /api/v1/screener/presets`
   - `POST /api/v1/screener/presets`
4. Implement `static/js/screener_view.js`:
   - Renders 1-click cards in Simple Mode; custom filter builder in Pro Mode.
   - Row click listener invokes `ChartManager.loadSymbol(match.symbol)`.

---

## 8. Verification & Acceptance Criteria
- Executing the "52-Week High Breakout" scan across Nifty 500 completes in $< 2.0\text{ seconds}$ on baseline hardware.
- Row Click Integration: Clicking any ticker in the screener table immediately updates the main chart with that stock's candles and session VWAP.
- As-of-date historical verification: Running scan as of `2023-01-10` produces identical results to historical backtest runs without forward data leakage.
- Absence of fundamental file produces zero errors; UI displays graceful disclaimer badge.
- Export test: Clicking "Export Results" downloads a clean CSV file containing matching symbols and scan coordinates.
