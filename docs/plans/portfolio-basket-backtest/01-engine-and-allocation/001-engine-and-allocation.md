# Plan 01-001: Multi-Asset Chronological Engine, Portfolio Broker & Position Sizing Engine

```yaml
EXECUTION_CONTRACT:
  depends_on: []
  reads:
    - "services/backtest/engine.py"
    - "services/backtest/cost_model.py"
    - "services/backtest/metrics.py"
    - "core/exceptions.py"
  produces:
    - "services/backtest/allocation.py"
    - "services/backtest/portfolio_broker.py"
    - "services/backtest/portfolio_engine.py"
    - "tests/unit/test_portfolio_backtest_engine.py"
  exposes:
    - "services.backtest.allocation.AllocationModel"
    - "services.backtest.allocation.EqualWeightAllocator"
    - "services.backtest.allocation.InverseATRAllocator"
    - "services.backtest.allocation.FixedAmountAllocator"
    - "services.backtest.portfolio_broker.PortfolioBroker"
    - "services.backtest.portfolio_engine.PortfolioEngine"
  must_not_modify:
    - "core/interfaces.py"
    - "db/connection.py"
  test_plan:
    - "pytest tests/unit/test_portfolio_backtest_engine.py -v"
  definition_of_done:
    - "PortfolioBroker accurately tracks shared cash, multi-symbol active lots, and closed trades with Indian statutory costs deducted"
    - "AllocationModel supports EQUAL_WEIGHT, INVERSE_ATR, and FIXED_AMOUNT with slot caps and cash guards"
    - "PortfolioEngine executes chronological bar-by-bar iteration across all universe assets without lookahead bias"
    - "Contention resolver prioritizes simultaneous signals by indicator strength (lowest RSI, highest ROC, highest volume)"
    - "Consolidated portfolio equity curve and true portfolio Sharpe, Sortino, Max Drawdown, and CAGR calculated"
  failure_modes_and_recovery:
    - "Cash insufficient for all candidate orders -> allocate available cash in ranked order, drop remaining orders without throwing error"
    - "Discontinuous trading dates across assets -> align timestamps on global union timeline, forward-fill missing non-trading bars"
  handoff:
    - "Provides core simulation engine for Plan 02-001 (API Endpoints & Universes Service)"
```

---

## 1. Goal & Scope / User Jobs Served
Establish the high-performance Python engine for simulating quantitative strategies across multi-asset stock baskets. Unlike single-stock engines that execute in isolation, `PortfolioEngine` synchronizes timeline progression across all universe stocks simultaneously, allocating from a shared cash pool, enforcing maximum concurrent open position limits, ranking competing signals, and accurately tracking cross-asset portfolio equity.

---

## 2. Architecture & SOLID Principles Application
- **Single Responsibility Principle (SRP):**
  - `allocation.py`: Computes target position quantity based on selected sizing model (Equal Weight, Inverse ATR, Fixed Amount) given available portfolio cash and slot limits.
  - `portfolio_broker.py`: Manages global portfolio cash, multi-symbol positions dictionary, lot-matching (FIFO), Indian tax deductions via `IndianEquityCostModel`, and daily portfolio valuation.
  - `portfolio_engine.py`: Synchronizes bar iteration across assets, resolves signal contention, triggers orders at next bar's OPEN price, and computes portfolio-level performance metrics.
- **Open/Closed Principle (OCP):**
  - Sizing models and ranking rules implement abstract interfaces allowing new sizing models (e.g. Risk Parity, Kelly Criterion) to be plugged in without modifying the broker.

---

## 3. Mathematical Specifications

### 3.1 Position Sizing Models
Let $C_{\text{avail}}$ be available unallocated cash, $N_{\text{max}}$ be max allowed positions, $N_{\text{open}}$ be current open positions, and $S_{\text{free}} = N_{\text{max}} - N_{\text{open}}$ be remaining slots.

1. **Equal Weight (`EQUAL_WEIGHT`):**
   $$\text{Target Capital per Slot} = \frac{C_{\text{avail}}}{S_{\text{free}}}$$
   $$\text{Qty} = \lfloor \frac{\text{Target Capital per Slot}}{\text{Price} \times (1 + \text{slippage})} \rfloor$$

2. **Volatility Adjusted (`INVERSE_ATR`):**
   Given 14-period Average True Range $\text{ATR}_i$ for asset $i$:
   $$\text{Weight}_i \propto \frac{1}{\text{ATR}_i}$$
   $$\text{Risk Budget} = \text{Portfolio Capital} \times \text{RiskPct}$$
   $$\text{Qty}_i = \lfloor \frac{\text{Risk Budget}}{2 \times \text{ATR}_i} \rfloor$$
   Capped by $\frac{C_{\text{avail}}}{S_{\text{free}}}$.

3. **Fixed Amount (`FIXED_AMOUNT`):**
   $$\text{Target Capital} = \min(C_{\text{avail}}, \text{FixedAmountConfig})$$
   $$\text{Qty} = \lfloor \frac{\text{Target Capital}}{\text{Price} \times (1 + \text{slippage})} \rfloor$$

### 3.2 Signal Contention Ranking Policy
On date $t$, if $K$ stocks trigger BUY signals where $K > S_{\text{free}}$:
- **Mean Reversion Strategies (RSI, Bollinger):** Rank ascending by RSI value (lowest RSI = deepest oversold).
- **Trend Following Strategies (SMA Cross, Supertrend, MACD):** Rank descending by Rate of Change ($\text{ROC}_{10}$) or Volume Surge Ratio ($\frac{V_t}{\text{SMA}_{20}(V)}$).
- Select top $S_{\text{free}}$ candidate stocks for fill; drop remaining candidates.

### 3.3 Daily Portfolio Valuation
On each calendar date $t$:
$$\text{Portfolio Value}_t = \text{Cash}_t + \sum_{i \in \text{Open Holdings}} \left( \text{Qty}_i \times \text{Close}_{i, t} \right)$$
$$\text{Cash Drag / Exposure Ratio}_t = \frac{\sum_{i} (\text{Qty}_i \times \text{Close}_{i, t})}{\text{Portfolio Value}_t}$$

---

## 4. Domain Contracts & Service Interfaces

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd

@dataclass
class PortfolioPosition:
    symbol: str
    entry_date: str
    entry_price: float
    qty: int
    cost_basis: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

@dataclass
class PortfolioTrade:
    trade_id: str
    symbol: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    qty: int
    gross_pnl: float
    statutory_costs: float
    net_pnl: float
    return_pct: float
    holding_period_days: int
    exit_reason: str

class AllocationModel(ABC):
    @abstractmethod
    def calculate_quantity(
        self,
        symbol: str,
        price: float,
        atr: Optional[float],
        available_cash: float,
        remaining_slots: int,
        portfolio_value: float,
        slippage_rate: float
    ) -> int:
        """Computes integer share quantity to buy adhering to sizing constraints."""
        pass

class PortfolioBroker:
    def __init__(self, initial_cash: float, cost_model, slippage_bps: float = 5.0):
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.cost_model = cost_model
        self.slippage_rate = slippage_bps / 10000.0
        self.open_positions: Dict[str, PortfolioPosition] = {}
        self.closed_trades: List[PortfolioTrade] = []
        self.equity_history: List[Dict] = []

    def can_open_slot(self, max_positions: int) -> bool:
        return len(self.open_positions) < max_positions

    def execute_buy(self, symbol: str, date: str, raw_price: float, qty: int, sl: Optional[float], tp: Optional[float]) -> bool:
        ...

    def execute_sell(self, symbol: str, date: str, raw_price: float, reason: str) -> Optional[PortfolioTrade]:
        ...

    def update_valuation(self, date: str, current_prices: Dict[str, float]) -> float:
        ...

class PortfolioEngine:
    def __init__(self, broker: PortfolioBroker, allocator: AllocationModel, max_positions: int = 10):
        self.broker = broker
        self.allocator = allocator
        self.max_positions = max_positions

    def run(
        self,
        universe_data: Dict[str, pd.DataFrame],
        strategy_signals: Dict[str, pd.DataFrame],
        ranking_metric: str = "AUTO"
    ) -> Dict:
        """Executes chronological bar-by-bar portfolio simulation across universe."""
        ...
```

---

## 5. Implementation Steps
1. Create `services/backtest/allocation.py` defining `AllocationModel`, `EqualWeightAllocator`, `InverseATRAllocator`, and `FixedAmountAllocator`.
2. Create `services/backtest/portfolio_broker.py` managing multi-asset positions, FIFO trade matching, `IndianEquityCostModel` statutory charges, and daily MTM equity snapshots.
3. Create `services/backtest/portfolio_engine.py`:
   - Aligns date indices of all universe assets.
   - Executes bar-by-bar chronological loop.
   - Enforces zero lookahead bias: fills pending orders at next bar's OPEN with slippage.
   - Resolves signal contention by ranking indicator values.
   - Generates consolidated portfolio metrics (CAGR, Sharpe, Sortino, Max Drawdown, Monthly Matrix, Asset Contributions).
4. Author comprehensive test suite in `tests/unit/test_portfolio_backtest_engine.py`.

---

## 6. Verification & Acceptance Criteria
- `pytest tests/unit/test_portfolio_backtest_engine.py -v` passes with 100% coverage.
- Max positions cap strictly honored under heavy signal contention.
- Zero cash overdraft (Cash never drops below ₹0.00).
- PAIR-wise trade matching verifies every round-trip trade contains entry price, exit price, duration, fees, and net profit.
- Exposure / Cash Drag ratio correctly calculated across every bar.
