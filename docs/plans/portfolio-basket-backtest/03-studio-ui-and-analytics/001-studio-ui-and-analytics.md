# Plan 03-001: Backtest Studio Dual-Mode Switcher, Portfolio Analytics & Asset Contribution Breakdown UI

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "01-001"
    - "02-001"
  reads:
    - "static/js/backtest_ui.js"
    - "static/css/theme.css"
    - "api/models/portfolio_backtest_models.py"
    - "api/routers/backtest.py"
  produces:
    - "static/js/portfolio_backtest_ui.js"
    - "tests/integration/test_portfolio_studio_ui_integration.py"
  exposes:
    - "window.PortfolioBacktestController"
    - "window.BacktestUI.prototype.switchMode"
  must_not_modify:
    - "core/interfaces.py"
    - "db/connection.py"
  test_plan:
    - "pytest tests/integration/test_portfolio_studio_ui_integration.py -v"
  definition_of_done:
    - "Backtest Studio features a seamless Dual-Mode Switcher: [ Single Asset ] <-> [ Portfolio Basket ]"
    - "Portfolio Basket mode provides 1-click Universe chips (NIFTY 50, NIFTY NEXT 50, NIFTY MIDCAP 150, Custom Basket) with constituent count badges"
    - "Configurator exposes Max Concurrent Positions (slots), Sizing Model (Equal Weight, Inverse ATR, Fixed ₹), and Signal Contention Ranking Policy"
    - "Consolidated Portfolio Equity Curve and NIFTY 50 Benchmark Buy & Hold curves render via Lightweight Charts with underwater Drawdown sub-pane"
    - "Asset Contribution Breakdown Table displays Symbol, Trades, Win Rate %, Net P&L ₹, Gross Alpha %, with visual performance bars"
    - "Consolidated Trade Ledger shows chronological trades across all basket symbols with symbol badges, duration, fees, and P&L"
    - "Automated integration test tests/integration/test_portfolio_studio_ui_integration.py passes with 100% assertions"
  failure_modes_and_recovery:
    - "Lightweight Charts container resize glitch on tab change -> invoke resizeCharts() with requestAnimationFrame observer"
    - "Network failure or 500 error from backend -> display institutional alert banner with retry button without losing form inputs"
  handoff:
    - "Completes Milestone 3 and fulfills the full user experience of Portfolio / Multi-Stock Basket Backtesting"
```

---

## 1. Goal & Scope / User Jobs Served
Empower quantitative traders and portfolio managers with an intuitive, institutional-grade visual interface for multi-asset strategy evaluation. The Studio seamlessly toggles between single-stock deep dives and multi-asset basket backtests, rendering portfolio equity curves, benchmark alpha, cross-asset risk metrics, monthly return heatmaps, and asset-by-asset alpha contribution tables.

---

## 2. UI/UX Architecture & Layout

### 2.1 Dual-Mode Switcher
Positioned in the header of `BacktestUI`:
```html
<div class="studio-mode-switcher" id="studio-mode-switcher">
  <button type="button" class="mode-toggle-btn active" data-mode="single">📊 Single Asset</button>
  <button type="button" class="mode-toggle-btn" data-mode="portfolio">🧺 Portfolio Basket</button>
</div>
```

### 2.2 Portfolio Basket Configurator Controls
When `Portfolio Basket` mode is active:
1. **Universe Selection Card**:
   - Preset chips: `NIFTY 50 (50)`, `NIFTY NEXT 50 (50)`, `NIFTY MIDCAP 150 (150)`, `Custom Basket`.
   - Custom search input for dynamically adding/removing NSE tickers.
2. **Portfolio Risk & Allocation Card**:
   - **Max Concurrent Positions (Slots)**: Stepper or number input (1 to 50, default 10).
   - **Allocation Model**:
     - `Equal Weight (1/N)`
     - `Inverse ATR (Volatility Adjusted)`
     - `Fixed Rupee Amount (₹ / Slot)`
   - **Contention Ranking Metric**:
     - `Auto (Strategy Default)`
     - `RSI Deepest Oversold (Ascending)`
     - `Momentum ROC 10-day (Descending)`
     - `Volume Surge Ratio (Descending)`
   - **Individual Stop Loss % & Take Profit %**

### 2.3 Analytics & Visualization Tabs
1. **Portfolio Overview & KPIs**:
   - Total Net Profit (₹), true Portfolio CAGR %, Sharpe Ratio, Sortino Ratio, Max Drawdown %, Cash Drag / Exposure Ratio %, Total Statutory Taxes (₹).
2. **Equity Curve & Benchmark Comparison**:
   - Primary line: Portfolio Equity (Teal `#00E676`).
   - Benchmark line: NIFTY 50 Index (Blue `#2962FF`).
   - Secondary pane: Underwater Drawdown % curve (Coral `#FF5252`).
3. **Asset Contribution Breakdown Table**:
   - Displays a breakdown of how each symbol in the basket contributed to the overall portfolio return.
   - Sortable columns: Symbol, Trade Count, Win Rate %, Net P&L (₹), Alpha Contribution (%).
   - Visual mini-bar showing positive (green) vs negative (red) impact.
4. **Monthly Returns Heatmap**:
   - 12-column grid (Jan - Dec) across backtest years with colored gradients.
5. **Consolidated Combined Trades Ledger**:
   - Unified chronological list of all trades taken across all universe stocks with search filter and symbol badges.

---

## 3. Domain Contracts & Client Controller Interface

```javascript
/**
 * PortfolioBacktestController Interface Specification
 */
class PortfolioBacktestController {
  constructor(backtestUI) {
    this.ui = backtestUI;
    this.activeMode = 'single'; // 'single' | 'portfolio'
    this.selectedUniverse = 'NIFTY_50';
    this.customSymbols = [];
    this.portfolioResult = null;
  }

  /**
   * Initializes mode switcher and binds universe selection listeners.
   */
  init();

  /**
   * Switches active mode between 'single' and 'portfolio'.
   * @param {'single' | 'portfolio'} mode
   */
  switchMode(mode);

  /**
   * Fetches available universes from /api/v1/backtest/portfolio/universes
   * and renders preset chips.
   */
  async loadUniverses();

  /**
   * Collects portfolio configuration inputs and executes portfolio backtest.
   * Calls POST /api/v1/backtest/portfolio/run.
   */
  async runPortfolioBacktest();

  /**
   * Renders the portfolio equity curve and benchmark comparison on Lightweight Charts.
   * @param {Array<{time: string, value: number}>} portfolioCurve
   * @param {Array<{time: string, value: number}>} benchmarkCurve
   */
  renderPortfolioCharts(portfolioCurve, benchmarkCurve);

  /**
   * Populates the Asset Contribution Breakdown table.
   * @param {Array<{symbol: string, trade_count: number, win_rate: number, net_pnl: number, alpha_contribution_pct: number}>} contributions
   */
  renderAssetContributionTable(contributions);

  /**
   * Populates the combined chronological trade ledger.
   * @param {Array<Object>} trades
   */
  renderPortfolioTradeLedger(trades);
}
```

---

## 4. Implementation Steps
1. Create `static/js/portfolio_backtest_ui.js` implementing `PortfolioBacktestController` and hooking into `BacktestUI`.
2. Add necessary CSS styles for the mode switcher, universe chips, and asset contribution table in `static/css/theme.css`.
3. Update `static/js/backtest_ui.js` and `static/index.html` to register and load `portfolio_backtest_ui.js`.
4. Author comprehensive integration test `tests/integration/test_portfolio_studio_ui_integration.py` verifying:
   - DOM elements for mode switcher, universe chips, slot inputs, and asset contribution table exist.
   - API endpoints serving status (200 OK) and contract validity.
   - Seamless toggling between single and portfolio mode without errors.

---

## 5. Verification & Acceptance Criteria
- Run `pytest tests/integration/test_portfolio_studio_ui_integration.py -v` (100% pass).
- Switching between Single Asset and Portfolio Basket updates the UI cleanly without console errors.
- Running a 10-stock Nifty 50 basket renders the complete equity curve, KPI cards, and asset contribution table.
- All existing 251 tests continue to pass with zero regressions.
