# Plan 02-001: Multi-Broker Tradebook Import Engine (FYERS, Zerodha Console, Groww)

## 1. Execution Contract
```yaml
execution_contract:
  plan_id: "02-001"
  name: "Multi-Broker Tradebook Import Engine"
  feature: "journal-calendar-and-analytics"
  depends_on:
    - "01-001"
  reads:
    - "services/journal_service.py"
    - "api/routers/journal.py"
    - "tests/fixtures/sample_fyers_tradebook.csv"
  produces:
    - "services/journal/importer_engine.py"
    - "services/journal/parsers/fyers_parser.py"
    - "services/journal/parsers/zerodha_parser.py"
    - "services/journal/parsers/groww_parser.py"
    - "tests/fixtures/sample_zerodha_tradebook.csv"
    - "tests/fixtures/sample_groww_tradebook.csv"
    - "tests/unit/test_multi_broker_importers.py"
    - "tests/integration/test_multi_broker_import_api.py"
  exposes:
    - "POST /api/v1/journal/import"
  must_not_modify:
    - "services/journal/calendar_service.py"
    - "services/journal/diagnostics_service.py"
  test_plan:
    unit_tests: "pytest tests/unit/test_multi_broker_importers.py -v"
    integration_tests: "pytest tests/integration/test_multi_broker_import_api.py -v"
    command: "pytest tests/unit/test_multi_broker_importers.py tests/integration/test_multi_broker_import_api.py -v"
  definition_of_done:
    - "Auto-detection correctly distinguishes FYERS, Zerodha Console, and Groww CSV formats by signature headers"
    - "Zerodha parser correctly extracts symbol, exchange, trade date, buy/sell side, quantity, and execution price"
    - "Groww parser correctly parses stock name/symbol, order type, execution date/time, price, and matched quantity"
    - "FIFO reconciler pairs fills into completed round-trip trades, computes Indian charges, and inserts into DuckDB"
    - "Invalid CSVs return clear descriptive validation errors without crashing"
  failure_modes_and_recovery:
    - "Unmatched partial fills: Handled gracefully and recorded as open fills or remaining positions"
    - "Malformed timestamps: Supports ISO-8601, '%Y-%m-%d %H:%M:%S', '%d-%m-%Y %H:%M:%S', and '%d/%m/%Y' formats"
    - "Unknown broker format: Rejects with HTTP 400 detailing expected columns"
  handoff:
    next_plan: "03-001"
    requires: "Multi-broker import engine active and tested across all three broker formats"
```

---

## 2. Goal & Scope / User Jobs Served
Indian quantitative and active traders frequently trade across multiple discount brokers (Zerodha Kite Console, Groww, and FYERS). Currently, the platform only accepts FYERS tradebook CSVs.
- **Intelligent Auto-Detection**: Inspects uploaded CSV headers and automatically identifies the broker format without requiring manual user selection.
- **Zerodha Console Parser**: Ingests Zerodha Kite tradebook reports (including ISIN, exchange, trade_type, and execution timestamps).
- **Groww Parser**: Ingests Groww equity order and trade history reports.
- **Robust Trade Matching**: Pairs multi-fill orders via chronological FIFO matching into complete `JournalEntry` records with statutory cost deductions.

---

## 3. Architecture & SOLID Principles Application
- **Strategy Pattern & Factory**:
  - `IBrokerParser` ABC defining `parse_fills(csv_text: str) -> List[RawTradeFill]`.
  - Concrete implementations: `FyersParser`, `ZerodhaParser`, `GrowwParser`.
  - `BrokerParserFactory.detect_and_get_parser(csv_text: str, broker_hint: Optional[str]) -> IBrokerParser`.
- **FIFO Trade Reconciler (`TradeReconciler`)**:
  - Matches open long/short fills into realized trades with accurate price averaging, statutory cost calculation, and R-multiple estimation.

---

## 4. Domain & Format Specifications

### 4.1 Signature Column Signatures
| Broker | Signature Headers Detected | Timestamp Formats |
| :--- | :--- | :--- |
| **FYERS** | `symbol`, `trade_date`, `side`, `price`, `quantity` | `%Y-%m-%d %H:%M:%S` or ISO |
| **Zerodha Console** | `isin`, `trade_date`, `exchange`, `segment`, `trade_type`, `price`, `quantity` | `%Y-%m-%d %H:%M:%S` |
| **Groww** | `stock name` or `symbol`, `type`, `price`, `quantity`, `execution date` or `date` | `%d-%m-%Y %H:%M:%S` or `%Y-%m-%d` |

### 4.2 Fill Normalization Model (`RawTradeFill`)
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class RawTradeFill:
    symbol: str
    side: str  # 'BUY' | 'SELL'
    quantity: int
    price: float
    timestamp: datetime
    broker: str
    trade_id: str
```

---

## 5. Implementation Steps
1. Create `services/journal/parsers/base_parser.py` with `IBrokerParser` and `RawTradeFill`.
2. Implement:
   - `services/journal/parsers/fyers_parser.py`
   - `services/journal/parsers/zerodha_parser.py`
   - `services/journal/parsers/groww_parser.py`
3. Implement `services/journal/importer_engine.py`:
   - `detect_broker(csv_text: str) -> str`
   - `FIFOReconciler` pairing fills and generating `JournalEntry` objects.
4. Update `POST /api/v1/journal/import` in `api/routers/journal.py` to route through `ImporterEngine`.
5. Create sample fixtures:
   - `tests/fixtures/sample_zerodha_tradebook.csv`
   - `tests/fixtures/sample_groww_tradebook.csv`
6. Author unit tests `tests/unit/test_multi_broker_importers.py` and integration tests `tests/integration/test_multi_broker_import_api.py`.

---

## 6. Verification & Acceptance Criteria
- `pytest tests/unit/test_multi_broker_importers.py tests/integration/test_multi_broker_import_api.py -v` passes 100%.
- Auto-detection identifies FYERS, Zerodha, and Groww samples with 100% accuracy.
- Completed round-trip trades are correctly inserted into DuckDB `journal_entries`.
