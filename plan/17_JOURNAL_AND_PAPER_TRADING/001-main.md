# Phase 17: Trade Journal, Analytics & Paper-Trading Simulator

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "plan/00_MASTER_ARCHITECTURE.md"
    - "plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md"
    - "plan/14_BACKTESTING_ENGINE.md"
  reads:
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#1-canonical-interface-registry"
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#4-canonical-database-schema-registry"
  produces:
    - "services/journal_service.py"
    - "services/paper_trading_service.py"
    - "api/v1/journal.py"
    - "static/js/journal_view.js"
    - "config/mistake_tags.json"
  exposes:
    - "IJournalService"
  must_not_modify:
    - "plan/*"
    - "core/rate_governor.py"
  test_plan:
    unit_tests: "tests/unit/test_r_multiple.py tests/unit/test_tradebook_import.py"
    integration_tests: "tests/integration/test_paper_trading_execution.py"
    contract_tests: "tests/contract/test_journal_contract.py"
    fixtures: "tests/fixtures/sample_fyers_tradebook.csv"
    command: "pytest tests/unit/test_r_multiple.py tests/integration/test_paper_trading_execution.py -v"
  definition_of_done:
    - item: 1
      command: "python -c 'from services.journal_service import JournalService; from db.connection import get_db; j = JournalService(get_db()); r = j.calculate_r_multiple(entry=2500, exit=2600, stop_loss=2450, direction=\"LONG\"); assert r == 2.0'"
      result: "R-multiple evaluates precisely to 2.0R for a 100 pt gain against a 50 pt risk."
    - item: 2
      command: "python -c 'from services.paper_trading_service import PaperTradingService; from db.connection import get_db; p = PaperTradingService(get_db()); fill = p.execute_order(symbol=\"NSE:RELIANCE-EQ\", quantity=100, side=\"BUY\", order_type=\"MARKET\", current_price=2500.0); assert fill.total_charges > 0 and fill.fill_price > 2500.0'"
      result: "Paper trade execution deducts Indian statutory taxes and adds 5 bps slippage penalty."
    - item: 3
      command: "pytest tests/unit/test_tradebook_import.py"
      result: "Imports external CSV tradebook, parses fills, matches buy/sell pairs, and records trades in journal_entries."
  failure_modes_and_recovery:
    - failure: "Trade entry has Stop Loss placed on wrong side of Entry"
      detection: "Long trade with Stop Loss >= Entry, or Short trade with Stop Loss <= Entry"
      recovery: "Reject trade with ValidationError: 'Stop Loss must be below Entry for Long, above Entry for Short'"
    - failure: "Malformed external tradebook CSV format"
      detection: "Missing required columns (symbol, trade_date, price, quantity)"
      recovery: "Emit descriptive import error modal showing expected CSV headers and sample row"
  handoff:
    - "IJournalService and paper-trading simulator operational."
    - "R-multiple analytics and psychological mistake tagging verified."
    - "Ready for Phase 18 beginner learning layer."
```

---

## 1. Goal & User Jobs Served
Build a quantitative trade journaling, psychological review, and paper-trading simulation module adhering to the 00A Canonical Registry.

### Core User Jobs:
1. **Review (Both Personas)**: "Log my live and paper trades, review performance, and evaluate whether my winners are generating sufficient risk-reward ($R$-multiples)."
2. **Review (Beginner)**: "Help me identify psychological mistakes (e.g. FOMO, moving stop losses, exiting winners too early) so I can improve my discipline."
3. **Test / Simulate (Both Personas)**: "Practice trading systematic setups in real-time with virtual money, experiencing realistic fills, slippage, and statutory Indian taxes without risking capital."

---

## 2. SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `JournalService`: Implements `IJournalService`, responsible for CRUD operations, CSV tradebook ingestion, and performance metrics aggregation.
  - `PaperTradingService`: Responsible solely for maintaining virtual cash accounts, simulated limit/market order book matching, and fill generation.
  - `MistakeTagManager`: Responsible solely for categorizing and analyzing behavioral leak patterns.
- **Open/Closed Principle (OCP)**:
  - Trade import parsers implement `ITradebookParser`. Adding Zerodha, Upstox, or Groww tradebook formats requires implementing an importer class without altering core journal logic.
- **Dependency Inversion Principle (DIP)**:
  - Paper trading execution reuses the `IndianEquityCostModel` defined in Phase 14 (`services/backtest/cost_model.py`), ensuring mathematical uniformity between backtests and paper trading.

---

## 3. Trade Journal Architecture & Mathematical Derivations

### 3.1. $R$-Multiple Formulation
In quantitative trading, raw rupee P&L is misleading because position sizing varies. The institutional standard is the **$R$-Multiple**, measuring return normalized by initial risk:

- **Initial Dollar Risk per Share**:
  $$R_{\text{risk}} = |\text{Entry Price} - \text{Stop Loss}|$$
- **Gross Profit per Share**:
  $$\text{Gain}_{\text{Long}} = \text{Exit Price} - \text{Entry Price}$$
  $$\text{Gain}_{\text{Short}} = \text{Entry Price} - \text{Exit Price}$$
- **$R$-Multiple**:
  $$R = \frac{\text{Gain per Share}}{R_{\text{risk}}}$$

*Example*:
- Buy Reliance @ ₹2,500 with Stop Loss @ ₹2,450 ($R_{\text{risk}} = ₹50$).
- Exit @ ₹2,650 (Gain = ₹150).
- $R\text{-Multiple} = 150 / 50 = \mathbf{+3.0R}$.
- If stopped out @ ₹2,450: $R\text{-Multiple} = -50 / 50 = \mathbf{-1.0R}$.

### 3.2. Trade Import Specification
Supports automated ingestion of broker tradebook CSV dumps:
- **Supported Formats**: Fyers Tradebook CSV, Zerodha Console Tradebook CSV.
- **Matching Algorithm**: First-In, First-Out (FIFO) trade reconciliation matching Buy executions with corresponding Sell executions to form closed round-trip trade entities.

### 3.3. Behavioral Mistake Tagging System (`config/mistake_tags.json`)
Allows traders to tag behavioral leaks during post-trade review:
```json
{
  "tags": [
    { "id": "FOMO", "name": "Chased Extended Move", "category": "ENTRY" },
    { "id": "NO_PLAN", "name": "Entered Without Stop Loss", "category": "RISK" },
    { "id": "EARLY_EXIT", "name": "Exited Winner Prematurely", "category": "EXIT" },
    { "id": "OVERSIZED", "name": "Risked > 2% of Capital", "category": "SIZING" },
    { "id": "REVENGE", "name": "Revenge Trade Post-Loss", "category": "PSYCHOLOGY" }
  ]
}
```
- **Analytics View**: Displays "Cost of Mistakes" — calculates the cumulative rupee loss attributed to trades tagged with behavioral leaks.

---

## 4. Paper-Trading Execution Simulator

```
      [ Virtual Order: BUY 100 RELIANCE @ MKT ]
                         │
                         ▼
        [ Current Quote / Candle Check ]
        - Check 09:15-15:30 IST Session Hours
        - Current Ask Price = ₹2,500.00
                         │
                         ▼
        [ Slippage Engine: +5 bps (0.05%) ]
        - Fill Price = ₹2,500 * 1.0005 = ₹2,501.25
                         │
                         ▼
        [ Phase 14 Statutory Indian Cost Model ]
        - Brokerage: ₹20.00
        - STT (Delivery Buy): 0.1% = ₹250.13
        - Exchange Charges: ₹7.43
        - Stamp Duty: 0.015% = ₹37.52
        - GST: 18% on (20 + 7.43) = ₹4.94
        - Total Friction = ₹320.02
                         │
                         ▼
        [ Update Virtual Cash & Open Positions ]
        - Cash Deducted: ₹250,125.00 + ₹320.02 = ₹250,445.02
        - Position: +100 RELIANCE @ ₹2,501.25
```

### 4.1. Simulated Fill Mechanics
- **Market Orders**: Fill on the subsequent tick/candle with a standardized **5 basis point (0.05%) slippage penalty**.
- **Limit Orders**: Fill only if the market trades through the limit price:
  - Buy Limit ($L$): Fills if $\text{Low}_{\text{bar}} \le L$.
  - Sell Limit ($L$): Fills if $\text{High}_{\text{bar}} \ge L$.
- **Cost Deductions**: Reuses `IndianEquityCostModel` from Phase 14, accurately deducting STT, stamp duty, exchange charges, and brokerage from virtual cash balances.

---

## 5. Interface Contract (`core/interfaces.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

@dataclass
class JournalEntry:
    trade_id: str
    symbol: str
    trade_type: str                   # 'PAPER' or 'MANUAL'
    direction: str                    # 'LONG' or 'SHORT'
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime]
    exit_price: Optional[float]
    quantity: int
    stop_loss: float
    take_profit: Optional[float]
    pnl_gross: Optional[float]
    total_charges: Optional[float]
    pnl_net: Optional[float]
    r_multiple: Optional[float]
    mistake_tags: List[str]
    notes: Optional[str]

class IJournalService(ABC):
    @abstractmethod
    def record_trade(self, trade: JournalEntry) -> str:
        """Saves or updates trade record in journal_entries table."""
        pass

    @abstractmethod
    def list_trades(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[JournalEntry]:
        """Retrieves trade records for review."""
        pass

    @abstractmethod
    def import_tradebook_csv(self, file_content: str, broker: str = "FYERS") -> int:
        """Parses external tradebook CSV and reconciles into journal entries."""
        pass

    @abstractmethod
    def get_performance_summary(self) -> Dict[str, Any]:
        """Calculates win rate, average R, expectancy, and cost of mistakes."""
        pass
```

---

## 6. Implementation Steps
1. Create `config/mistake_tags.json` defining psychological and execution mistake tags.
2. Implement `services/journal_service.py` (`IJournalService`):
   - Computes $R$-multiples and cumulative net P&L.
   - Reconciles FIFO trade pairs from external CSV files.
3. Implement `services/paper_trading_service.py`:
   - Maintains virtual portfolio state in DuckDB.
   - Executes simulated fills with Phase 14 cost model.
4. Implement `api/v1/journal.py` exposing REST endpoints.
5. Create `static/js/journal_view.js` rendering trade log table, equity curve, and mistake breakdown charts.

---

## 7. Verification & Acceptance Criteria
- $R$-multiple math verified: Long trade with Entry=2500, Exit=2600, SL=2450 yields exactly $+2.0R$; stopped out at 2450 yields $-1.0R$.
- Fyers tradebook CSV import parses 50 fills and generates 25 round-trip journal entries without schema errors.
- Paper trading order execution applies exact statutory Indian taxes (STT 0.1%, Brokerage ₹20, Stamp duty 0.015%) and adjusts virtual cash accurately.
- Trade with missing or inverted stop loss is rejected with descriptive validation error.
