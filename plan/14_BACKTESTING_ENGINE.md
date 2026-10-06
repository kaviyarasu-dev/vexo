# Phase 14: Institutional Backtesting Engine & Realistic Indian Cost Model

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "plan/00_MASTER_ARCHITECTURE.md"
    - "plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md"
    - "plan/05_RESAMPLING_AND_QUANT_METRICS_ENGINE.md"
    - "plan/10_EDGE_CASES_RISKS_AND_MAINTENANCE.md"
  reads:
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#1-canonical-interface-registry"
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#4-canonical-database-schema-registry"
    - "plan/VERIFICATION_REPORT.md#28-indian-equity-transaction-costs--taxes"
  produces:
    - "services/backtest_service.py"
    - "services/backtest/cost_model.py"
    - "services/backtest/engine.py"
    - "services/backtest/metrics.py"
    - "services/backtest/monte_carlo.py"
    - "api/v1/backtest.py"
    - "static/js/backtest_view.js"
  exposes:
    - "IBacktestEngine"
  must_not_modify:
    - "plan/*"
    - "core/rate_governor.py"
  test_plan:
    unit_tests: "tests/unit/test_indian_cost_model.py tests/unit/test_backtest_metrics.py"
    integration_tests: "tests/integration/test_backtest_execution.py"
    contract_tests: "tests/contract/test_lookahead_prevention.py"
    fixtures: "tests/fixtures/sample_strategy_series.json"
    command: "pytest tests/unit/test_indian_cost_model.py tests/contract/test_lookahead_prevention.py -v"
  definition_of_done:
    - item: 1
      command: "python -c 'from services.backtest.cost_model import IndianEquityCostModel; m = IndianEquityCostModel(); fees = m.compute_fees(buy_val=100000, sell_val=105000, trade_type=\"DELIVERY\"); assert fees.stt == 205.0 and fees.brokerage == 40.0'"
      result: "Cost model correctly computes statutory Indian taxes: STT 0.1% both sides, brokerage capped at ₹20/order, GST 18%, Stamp duty 0.015%."
    - item: 2
      command: "pytest tests/contract/test_lookahead_prevention.py -k test_deliberate_lookahead_fails"
      result: "Deliberate lookahead test fixture peeking at bar t close for bar t fill is detected and rejected with LookaheadBiasError."
    - item: 3
      command: "python -c 'from services.backtest_service import BacktestService; from db.connection import get_db; s = BacktestService(get_db()); r = s.run_backtest(config={\"strategy\": \"SMA_CROSS\", \"symbol\": \"NSE:RELIANCE-EQ\"}); assert \"data_version_hash\" in r and \"survivorship_bias_warning\" in r'"
      result: "Backtest report includes cryptographic data-version hash, random seed, and mandatory survivorship bias warning."
  failure_modes_and_recovery:
    - failure: "Custom Python strategy attempts unauthorized disk/network I/O"
      detection: "Sandbox security audit raises SecurityViolationError via AST validator"
      recovery: "Reject strategy script immediately; display exact offending syntax in UI console"
    - failure: "Strategy generates fill price worse than bar High or Low"
      detection: "Assertion error in engine fill validator"
      recovery: "Clamp fill price strictly within [Low, High] of the fill bar; add configured slippage penalty"
  handoff:
    - "IBacktestEngine operational with Indian statutory cost model."
    - "Anti-lookahead validation and Monte Carlo analysis verified."
    - "Ready for Phase 15 corporate actions and external data engine."
```

---

## 1. Goal & User Jobs Served
Build a deterministic, event-driven backtesting engine that simulates systematic equity strategies against historical NSE data with realistic Indian transaction costs and zero lookahead bias adhering to the 00A Canonical Registry.

### Core User Jobs:
1. **Test (Beginner)**: "Let me test a simple moving average or RSI rule on Reliance over the last 3 years without writing code to see if it would have made money."
2. **Test (Quant Expert)**: "Let me write custom Python vectorized logic, test portfolio rebalancing across the Nifty 100, calculate walk-forward decay, and see exact after-tax returns after deducting STT, exchange charges, and slippage."
3. **Intellectual Honesty**: "Show me the real impact of trading costs. If a strategy looks profitable before fees but loses money after taxes, I need to know before risking capital."

---

## 2. SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `IndianEquityCostModel`: Solely responsible for calculating statutory brokerage, STT, exchange fees, SEBI charges, GST, and stamp duty.
  - `BacktestEngine`: Implements `IBacktestEngine`, solely responsible for bar iteration, signal evaluation, and fill execution.
  - `PerformanceCalculator`: Solely responsible for computing CAGR, Sharpe, Drawdown, and statistical metrics.
- **Open/Closed Principle (OCP)**:
  - Strategy implementations adhere to the `IStrategy` interface (`on_bar(bar, context) -> Signal`). Adding a new strategy requires creating a strategy class without modifying the simulation engine.
- **Dependency Inversion Principle (DIP)**:
  - The backtest engine consumes market data through `ICandleReader` querying `candles_1d_adjusted` or `candles_1m_adjusted`.

---

## 3. Verified Indian Equity Statutory Cost Model

Every simulated trade is subject to the exact statutory tax and broker fee structure verified in `VERIFICATION_REPORT.md`:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        INDIAN STATUTORY COST MODEL                     │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Brokerage (FYERS):                                                  │
│    - Delivery: Min(₹20, 0.3% of order value) per executed order        │
│    - Intraday: Min(₹20, 0.03% of order value) per executed order       │
│                                                                        │
│ 2. Securities Transaction Tax (STT):                                   │
│    - Delivery: 0.1% on Buy Value AND 0.1% on Sell Value                │
│    - Intraday: 0.025% on Sell Value only (0% on Buy Value)             │
│                                                                        │
│ 3. Exchange Transaction Charges (NSE Cash):                            │
│    - 0.00297% of total trade turnover (Buy + Sell)                    │
│                                                                        │
│ 4. SEBI Turnover Fee:                                                  │
│    - ₹10 per Crore (0.0001% of turnover) on Buy and Sell               │
│                                                                        │
│ 5. Goods & Services Tax (GST):                                         │
│    - 18% levied on: (Brokerage + Exchange Charges + SEBI Fee)          │
│                                                                        │
│ 6. Stamp Duty (Indian Stamp Act, Buy Side Only):                       │
│    - Delivery: 0.015% of Buy Value                                     │
│    - Intraday: 0.003% of Buy Value                                     │
│                                                                        │
│ 7. Slippage Model (Configurable):                                      │
│    - Default: 5.0 bps (0.05%) on fill price                            │
└────────────────────────────────────────────────────────────────────────┘
```

### Mathematical Example: Round-Trip Delivery Trade
- Buy 100 shares @ ₹2,500 = ₹250,000.
- Sell 100 shares @ ₹2,600 = ₹260,000.
- Gross P&L: ₹10,000.
- Costs Deducted:
  - Brokerage: ₹20 (Buy) + ₹20 (Sell) = ₹40.00.
  - STT: $0.1\% \times 250,000\text{ (₹250)} + 0.1\% \times 260,000\text{ (₹260)} = \mathbf{₹510.00}$.
  - Exchange Fee ($0.00297\%$): $₹7.43 + ₹7.72 = \mathbf{₹15.15}$.
  - SEBI Fee ($0.0001\%$): $₹0.25 + ₹0.26 = \mathbf{₹0.51}$.
  - GST ($18\%$ on $40 + 15.15 + 0.51 = 55.66$): $\mathbf{₹10.02}$.
  - Stamp Duty ($0.015\%$ on Buy): $\mathbf{₹37.50}$.
  - Slippage ($0.05\%$ each way): $₹125 + ₹130 = \mathbf{₹255.00}$.
- **Total Friction**: $\mathbf{₹868.18}$ (~8.7% of gross profit!).
- **Net P&L**: $\mathbf{₹9,131.82}$.

---

## 4. Anti-Lookahead Enforcement & Test Fixtures

### 4.1. Execution Timeline
To guarantee zero lookahead bias:
1. **Signal Generation**: Evaluated strictly at the **CLOSE** of bar $t$ using data up to timestamp $t$.
2. **Order Execution / Fill**: Fills strictly at the **OPEN** of bar $t+1$:
   $$\text{Fill Price} = \text{Open}_{t+1} \times (1 \pm \text{Slippage})$$
3. A strategy cannot peek into bar $t+1$'s High, Low, or Close to decide bar $t$'s order.

### 4.2. Deliberate Lookahead Test Fixture (`tests/contract/test_lookahead_prevention.py`)
- Test constructs an adversarial strategy that intentionally queries `bar.next.close` or attempts to fill orders on bar $t$ using bar $t$'s closing price.
- **Assertion**: The engine must detect the invalid timestamp sequence and raise `LookaheadBiasError`. Test passes only when the adversarial strategy is successfully caught and rejected.

---

## 5. Quantitative Performance Metrics & Robustness

### 5.1. Performance Metrics Suite
- **CAGR (Compound Annual Growth Rate)**:
  $$\text{CAGR} = \left(\frac{V_{\text{final}}}{V_{\text{initial}}}\right)^{1 / \text{Years}} - 1$$
- **Sharpe Ratio** (Risk-Free Rate: 6.5% standard RBI Repo Rate):
  $$\text{Sharpe} = \frac{\mu_{R} - R_f}{\sigma_{R}} \times \sqrt{250}$$
- **Sortino Ratio**: Penalizes downside volatility only ($\sigma_{\text{downside}}$).
- **Maximum Drawdown (MDD)**: Peak-to-trough equity decline.
- **Profit Factor & Expectancy**:
  $$\text{Expectancy} = (\text{Win Rate} \times \text{Avg Win}) - (\text{Loss Rate} \times \text{Avg Loss})$$
- **Market Exposure %**: Percentage of total trading days holding open positions.

### 5.2. Robustness Testing: Monte Carlo & Walk-Forward
1. **Monte Carlo Simulation**:
   - Resamples trade P&L series with replacement across 1,000 iterations.
   - Computes 95% Confidence Interval for Max Drawdown and Probability of Ruin.
2. **Walk-Forward Analysis**:
   - Splitting history into In-Sample (optimization) and Out-of-Sample (validation) windows to detect curve fitting and parameter decay.

### 5.3. Reproducibility & Governance
Every generated backtest report contains:
- `data_version_hash`: SHA-256 hash of the DuckDB candle table partition utilized.
- `random_seed`: Integer seed for Monte Carlo simulations.
- `survivorship_bias_warning`: Mandatory disclosure banner.

---

## 6. Interface Contract (`core/interfaces.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class BacktestConfig:
    strategy_name: str
    symbol: str
    timeframe: str = "1D"
    start_date: str = "2020-01-01"
    end_date: str = "2023-12-31"
    initial_capital: float = 1000000.0  # ₹10 Lakhs
    trade_type: str = "DELIVERY"        # "DELIVERY" or "INTRADAY"
    parameters: Dict[str, Any] = None
    slippage_bps: float = 5.0

@dataclass
class BacktestResult:
    cagr: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    win_rate: float
    profit_factor: float
    total_trades: int
    gross_pnl: float
    net_pnl: float
    total_taxes_and_fees: float
    equity_curve: List[Dict[str, Any]]
    data_version_hash: str
    survivorship_bias_warning: str

class IBacktestEngine(ABC):
    @abstractmethod
    def run_backtest(self, config: BacktestConfig) -> BacktestResult:
        """Executes simulation with Indian cost model and anti-lookahead rules."""
        pass
```

---

## 7. Implementation Steps
1. Create `services/backtest/cost_model.py` implementing `IndianEquityCostModel` with verified statutory rates.
2. Create `services/backtest/engine.py` (`IBacktestEngine`) with bar-by-bar event simulation.
3. Create `services/backtest/metrics.py` computing CAGR, Sharpe, Sortino, Drawdown.
4. Create `services/backtest/monte_carlo.py` running 1,000 resampled simulations.
5. Create `api/v1/backtest.py` exposing `POST /api/v1/backtest/run`.
6. Create `static/js/backtest_view.js` rendering equity curves, drawdown sub-charts, and fee breakdowns.

---

## 8. Verification & Acceptance Criteria
- Indian cost model matches the manual calculation test vector within ₹0.01 precision.
- Lookahead test passes: deliberate lookahead triggers `LookaheadBiasError`.
- Simulating a 5-year daily SMA crossover on RELIANCE executes in $< 1.5\text{ seconds}$.
- Every backtest response includes `data_version_hash`, fee itemization, and survivorship warning.
