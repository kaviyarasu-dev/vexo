# Plan 04-001: 1-Click Backtest Strategy Deploy to Paper Trading & Telemetry

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "01-engine-and-api/001-engine-and-api.md"
    - "02-chart-execution-and-overlays/001-chart-execution-and-overlays.md"
    - "03-terminal-dock-and-positions/001-terminal-dock-and-positions.md"
  reads:
    - "static/js/backtest_ui.js"
    - "static/js/paper_terminal_dock.js"
    - "services/backtest_service.py"
    - "services/paper_trading_service.py"
  produces:
    - "static/js/backtest_ui.js"
    - "services/paper_trading_service.py"
    - "api/routers/paper_trading.py"
    - "tests/integration/test_paper_trading_strategy_deploy.py"
  exposes:
    - "POST /api/v1/paper-trading/deploy-strategy"
    - "DELETE /api/v1/paper-trading/auto-strategies/{strategy_id}"
    - "BacktestUI.deployToPaperTrading()"
  must_not_modify:
    - "core/interfaces.py"
    - "db/connection.py"
  test_plan:
    - "pytest tests/integration/test_paper_trading_strategy_deploy.py -v"
  definition_of_done:
    - "Quant Backtest Studio includes a prominent '⚡ Deploy Strategy to Paper Trading' button"
    - "Clicking button posts strategy configuration to /api/v1/paper-trading/deploy-strategy"
    - "Active strategy appears in the 'Auto Strategies' tab of the Paper Trading Terminal Dock with status 'ACTIVE'"
    - "Background service evaluates candle signals and executes virtual market orders into paper_positions when triggers occur"
    - "Integration test verifies end-to-end deployment and signal execution"
  failure_modes_and_recovery:
    - "Strategy already deployed for same symbol -> update existing allocation or return friendly message"
  handoff:
    - "Completes the Paper Trading Terminal feature suite with full forward-testing capability"
```

---

## 1. Goal & Scope / User Jobs Served
Bridge historical quantitative backtesting with forward simulation. After optimizing a strategy in the Quant Backtest Studio, traders can deploy it to the live paper trading engine with a single click, allowing the algorithm to execute virtual trades automatically as new candles close.

---

## 2. Architecture & SOLID Principles Application
- **Single Responsibility Principle (SRP):**
  - `BacktestUI` triggers the deployment request with active parameters.
  - `PaperTradingService` manages automated strategy registrations in `paper_auto_strategies` and simulated execution.
- **Open/Closed Principle (OCP):**
  - Uses the existing `services/backtest_service.py` strategy instances (`_create_strategy_instance`) to evaluate bar signals.

---

## 3. UI/UX Specifications & Interaction Flow

### 3.1 Backtest Studio Deploy Button
In `static/js/backtest_ui.js`, add button inside the Studio header actions or Step 4 Sizing Rules card:
```html
<button type="button" class="btn-deploy-paper" id="btn-deploy-paper-strategy">
    ⚡ Deploy Strategy to Paper Trading
</button>
```

### 3.2 Auto Strategies Terminal Tab View
In `#dock-panel-strategies`:
- Table displaying:
  - `Strategy Name` (e.g. "RSI Reversal")
  - `Symbol` (e.g. "NSE:RELIANCE-EQ")
  - `Timeframe` (e.g. "1D")
  - `Allocated Capital` (₹1,00,000)
  - `Trades Executed`
  - `Status` (🟢 ACTIVE badge)
  - `Action` (Pause / Stop / Delete button)

---

## 4. Implementation Steps
1. Enhance `services/paper_trading_service.py`:
   - Add `register_auto_strategy(strategy_name, symbol, timeframe, parameters, capital)`.
   - Add `list_auto_strategies()`.
   - Add `stop_auto_strategy(strategy_id)`.
   - Add `evaluate_auto_strategies_on_candle(candle_df)` to trigger simulated order placement when an active strategy generates a BUY or SELL signal.
2. In `api/routers/paper_trading.py`:
   - Add `POST /api/v1/paper-trading/deploy-strategy`.
   - Add `GET /api/v1/paper-trading/auto-strategies`.
   - Add `DELETE /api/v1/paper-trading/auto-strategies/{strategy_id}`.
3. In `static/js/backtest_ui.js`:
   - Add the "⚡ Deploy Strategy to Paper Trading" button.
   - On click, send active strategy name, symbol, timeframe, and parameters to the deployment endpoint.
   - Show success notification toast with 1-click link to open the Paper Trading Terminal dock.
4. Create integration test `tests/integration/test_paper_trading_strategy_deploy.py`.

---

## 5. Verification & Acceptance Criteria
- Run `pytest tests/integration/test_paper_trading_strategy_deploy.py -v`.
- Verify deploying an RSI strategy registers row in `paper_auto_strategies`.
- Verify strategy appears in Terminal dock under "Auto Strategies".
- Verify stopping strategy changes status to `STOPPED` and ceases trade executions.
