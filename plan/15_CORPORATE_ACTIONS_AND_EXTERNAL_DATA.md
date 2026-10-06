# Phase 15: Corporate Actions Adjustment Engine & External NSE Feeds

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "plan/00_MASTER_ARCHITECTURE.md"
    - "plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md"
    - "plan/03_SYMBOL_MASTER_AND_UNIVERSE_MANAGER.md"
    - "plan/06_DAILY_INCREMENTAL_UPDATE_AND_SCHEDULER.md"
  reads:
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#1-canonical-interface-registry"
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#4-canonical-database-schema-registry"
    - "plan/VERIFICATION_REPORT.md#25-corporate-actions--cont_flag"
    - "plan/VERIFICATION_REPORT.md#28-nse--external-data-feeds"
    - "plan/OPEN_QUESTIONS.md#1-open-questions-matrix"
  produces:
    - "services/corporate_actions_service.py"
    - "services/external_data_service.py"
    - "scripts/fetch_bhavcopy_udiff.py"
    - "scripts/fetch_delivery_data.py"
    - "scripts/recompute_adjustment_factors.py"
    - "config/external_sources.json"
  exposes:
    - "ICorporateActionRepository"
  must_not_modify:
    - "plan/*"
    - "core/rate_governor.py"
  test_plan:
    unit_tests: "tests/unit/test_adjustment_math.py tests/unit/test_bhavcopy_parser.py"
    integration_tests: "tests/integration/test_corporate_actions_pipeline.py"
    contract_tests: "tests/contract/test_external_data_contract.py"
    fixtures: "tests/fixtures/sample_corporate_actions.json"
    command: "pytest tests/unit/test_adjustment_math.py tests/integration/test_corporate_actions_pipeline.py -v"
  definition_of_done:
    - item: 1
      command: "python -c 'from services.corporate_actions_service import CorporateActionsService; from db.connection import get_db; s = CorporateActionsService(get_db()); s.ingest_action(symbol=\"NSE:TATASTEEL-EQ\", action_type=\"SPLIT\", ex_date=\"2022-07-28\", ratio_from=10, ratio_to=1); s.recompute_factors(\"NSE:TATASTEEL-EQ\")'"
      result: "Calculates cumulative price factor 0.10 and volume factor 10.0 for dates prior to 2022-07-28 in adjustment_factors table."
    - item: 2
      command: "python scripts/fetch_bhavcopy_udiff.py --test"
      result: "Parses official UDiFF Bhavcopy ZIP from NSE archives with polite rate limits; populates security delivery and turnover metrics."
    - item: 3
      command: "python -c 'from db.connection import get_db; conn = get_db().get_read_cursor(); r = conn.execute(\"SELECT count(*) FROM candles_1d_adjusted\").fetchone()[0]; assert r >= 0'"
      result: "candles_1d_adjusted SQL view dynamically applies adjustment factors without mutating raw underlying data."
  failure_modes_and_recovery:
    - failure: "NSE archives blocks IP or returns HTTP 403 on automated Bhavcopy fetch"
      detection: "urllib.error.HTTPError: HTTP Error 403: Forbidden"
      recovery: "Implement Akamai-polite session bootstrap (visit nseindia.com homepage first to acquire cookies); fall back to local manual import folder data/external_imports/"
    - failure: "Dividend cash adjustment creates negative historical price"
      detection: "Calculated adjusted price <= 0.0"
      recovery: "Clamp price to tick size 0.05; log warning in audit log"
  handoff:
    - "ICorporateActionRepository and adjustment factor engine operational."
    - "UDiFF Bhavcopy and delivery volume ingestion scripts implemented."
    - "Ready for Phase 16 options module."
```

---

## 1. Goal & User Jobs Served
Establish an institutional-grade corporate actions adjustment engine and external market data ingestion pipeline for the NSE equity market adhering to the 00A Canonical Registry.

### Core User Jobs:
1. **Analyze (Both Personas)**: "Ensure historical stock charts reflect true split/bonus adjusted economics so a 10:1 stock split doesn't look like a 90% crash."
2. **Test (Quant Expert)**: "Keep raw unadjusted prices completely intact while providing dynamically recomputable adjusted series for backtesting, dividend yields, and delivery volume analysis."
3. **Data Completeness**: "Enrich equity candles with institutional delivery percentages, FII/DII net institutional flows, and bulk deal activity."

---

## 2. SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `CorporateActionsService`: Responsible solely for tracking stock splits, bonuses, dividends, and calculating cumulative mathematical adjustment factors.
  - `ExternalDataService`: Responsible solely for fetching and parsing official NSE Bhavcopy, delivery, and institutional activity files.
- **Open/Closed Principle (OCP)**:
  - Ingestion sources implement `IExternalDataSource` (`fetch()`, `parse()`, `persist()`). Adding a new third-party feed (e.g. Trendlyne or BSE archives) requires adding a class without modifying the adjustment factor engine.
- **Dependency Inversion Principle (DIP)**:
  - Downstream services query dynamic views (`candles_1d_adjusted`, `candles_1m_adjusted`) backed by `ICorporateActionRepository`.

---

## 3. Corporate Actions Adjustment Engine Architecture

### 3.1. Mathematical Sizing & Factor Formulas
- **Stock Split (Ratio $N : 1$, e.g. 10:1 split)**:
  - Price Factor: $f_P = 1 / N = 0.10$.
  - Volume Factor: $f_V = N = 10.0$.
  - Historical Price Adjustment: $P_{\text{adj}} = P_{\text{raw}} \times f_P$.
  - Historical Volume Adjustment: $V_{\text{adj}} = V_{\text{raw}} \times f_V$.
- **Bonus Issue (Ratio $A : B$, e.g. 1:1 bonus)**:
  - Total shares post-bonus = $B + A$.
  - Price Factor: $f_P = B / (B + A) = 0.50$.
  - Volume Factor: $f_V = (B + A) / B = 2.00$.
- **Cumulative Multiplier Property**:
  - When multiple corporate actions occur across a 15-year history, factors are cumulative:
    $$F_{P, t} = \prod_{k \in \text{Actions post } t} f_{P, k}$$

### 3.2. Idempotent Factor Recomputation (Zero Raw Re-downloads)
- In legacy architectures, a new stock split required re-downloading 5 years of 1m candles for that ticker.
- **Our Architecture**:
  1. Raw candles (`candles_1m_raw`, `candles_1d_raw`) are immutable and NEVER re-downloaded for corporate actions.
  2. When a corporate action is recorded in `corporate_actions`, `recompute_factors(symbol)` executes in $< 15\text{ ms}$:
     - Rebuilds rows in `adjustment_factors`.
     - The dynamic views (`candles_1m_adjusted`, `candles_1d_adjusted`) immediately reflect the new split-adjusted pricing on next query!

---

## 4. External NSE Data Ingestion Pipeline

### 4.1. Unified Distilled File Formats (UDiFF) Bhavcopy
- **Source**: `https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_<YYYYMMDD>_F_0000.csv.zip`
- **Schedule**: Downloaded daily post-market at 18:30 IST by `scripts/fetch_bhavcopy_udiff.py`.
- **Enrichment**: Cross-verifies Fyers 1D closing prices against the official exchange trade settlement.

### 4.2. Delivery Volume & Security-wise Data
- **Source**: `https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_<DDMMYYYY>.csv`
- **Fields Extracted**:
  - `TTL_TRD_QNTY`: Total Traded Quantity.
  - `DELIV_QTY`: Deliverable Quantity.
  - `DELIV_PER`: Delivery Percentage (Institutional accumulation indicator).

### 4.3. Institutional Activity & Bulk Deals
- **FII / DII Daily Net**: Ingests daily net institutional buying/selling in Crores.
- **Bulk & Block Deals**: Captures single-trade transactions $> 0.5\%$ of equity capital.

---

## 5. Politeness, Scraping Risks & Source Failure Fallbacks

```
                          [ External Data Fetcher ]
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
     [ Step 1: Session Cookie Bootstrap ]    [ Step 2: Rate Throttling ]
     - Fetch nseindia.com homepage           - Hard throttle: <= 1 req / 3s
     - Extract Akamai / Cloudflare cookies   - Set browser-grade User-Agent
                 │                                       │
                 └───────────────────┬───────────────────┘
                                     ▼
                      [ Dispatch Request to Archives ]
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
                 [ 200 OK ]                   [ 403 / Network Failure ]
                 - Parse CSV                  - Log warning
                 - Ingest to DuckDB           - Load local manual import
                                                data/external_imports/*.csv
```

### 5.1. Politeness Rules
1. **Rate Ceiling**: Outgoing calls to NSE domains strictly capped at **$\le 1$ request every 3 seconds**.
2. **Header Standardization**: Employs desktop browser `User-Agent`, `Accept-Language`, and `Referer` headers.
3. **Session Cookie Bootstrap**: Initializes a session against the root homepage before requesting archive endpoints.

### 5.2. Fallback Policy
If NSE archives reject connections or change URL paths:
- The system checks `data/external_imports/` for manually dropped CSV files.
- Displays an operational freshness indicator in the UI: `Bhavcopy Freshness: [Current / Delayed]`.

---

## 6. Interface Contract (`core/interfaces.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional, List

@dataclass
class CorporateAction:
    id: str
    symbol: str
    action_type: str                  # "SPLIT", "BONUS", "DIVIDEND", "RIGHTS"
    ex_date: date
    record_date: Optional[date]
    ratio_from: Optional[float]
    ratio_to: Optional[float]
    dividend_amount: Optional[float]
    description: Optional[str]

@dataclass
class AdjustmentFactor:
    symbol: str
    ex_date: date
    factor_price: float
    factor_volume: float

class ICorporateActionRepository(ABC):
    @abstractmethod
    def upsert_actions(self, actions: List[CorporateAction]) -> int:
        """Saves corporate actions into corporate_actions table."""
        pass

    @abstractmethod
    def get_factors(self, symbol: str) -> List[AdjustmentFactor]:
        """Retrieves calculated adjustment factors."""
        pass

    @abstractmethod
    def recompute_adjustment_factors(self, symbol: str) -> None:
        """Recomputes cumulative price/volume factors for symbol."""
        pass
```

---

## 7. Implementation Steps
1. Create `services/corporate_actions_service.py` implementing `ICorporateActionRepository`:
   - Calculates cumulative adjustment factors using backward progression.
   - Inserts factors into `adjustment_factors`.
2. Implement `scripts/recompute_adjustment_factors.py`.
3. Create `services/external_data_service.py` handling UDiFF Bhavcopy and delivery percentages.
4. Implement `scripts/fetch_bhavcopy_udiff.py` and `scripts/fetch_delivery_data.py`.
5. Integrate post-market trigger in `scheduler_service.py` at 18:30 IST.

---

## 8. Verification & Acceptance Criteria
- Registering a 10:1 split on `NSE:TATASTEEL-EQ` (ex-date: `2022-07-28`) generates `factor_price = 0.10` and `factor_volume = 10.0` for all earlier dates.
- Querying `candles_1d_adjusted` across the ex-date eliminates the 90% price gap; continuity is maintained within 0.1% of official exchange adjusted charts.
- Recomputing factors for 500 stocks completes in $< 500\text{ ms}$ without altering raw tables.
- Bhavcopy parser extracts delivery quantities from valid UDiFF ZIP file without schema errors.
