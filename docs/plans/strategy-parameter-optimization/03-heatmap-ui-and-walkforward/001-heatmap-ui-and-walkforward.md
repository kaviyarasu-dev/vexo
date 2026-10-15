# Plan 03-001: Optimization Studio UI: 2D Heatmap Grid, Metric Switcher & Walk-Forward HUD

## 1. Execution Contract
```yaml
execution_contract:
  plan_id: "03-001"
  name: "Optimization Studio UI: 2D Heatmap Grid, Metric Switcher & Walk-Forward HUD"
  feature: "strategy-parameter-optimization"
  depends_on:
    - "01-001"
    - "02-001"
  reads:
    - "static/index.html"
    - "static/css/theme.css"
    - "static/js/backtest_ui.js"
    - "api/routers/backtest.py"
  produces:
    - "static/js/backtest_optimization_ui.js"
    - "tests/integration/test_parameter_optimization_ui_integration.py"
  exposes:
    - "Subtab #btn-backtest-tab-optimize (Backtest Studio)"
    - "Interactive 2D Heatmap SVG Canvas (#opt-heatmap-svg)"
    - "Stability HUD Card (#opt-stability-hud)"
    - "Walk-Forward Side-by-Side Table (#opt-walk-forward-table)"
    - "1-Click Deploy Button (#btn-apply-optimal-params)"
  must_not_modify:
    - "static/js/options_analytics.js"
    - "static/js/chart_drawings.js"
    - "static/js/journal_analytics.js"
  test_plan:
    integration_tests: "pytest tests/integration/test_parameter_optimization_ui_integration.py -v"
    command: "pytest tests/integration/test_parameter_optimization_ui_integration.py -v"
  definition_of_done:
    - "Backtest Studio contains a dedicated '#btn-backtest-tab-optimize' subtab navigation"
    - "Interactive 2D color heatmap renders with dynamic color gradient and metric switching (Sharpe, P&L, Max DD, Win Rate)"
    - "Hover tooltips on heatmap cells display exact parameters, trade count, and returns"
    - "Stability HUD badge accurately displays 3x3 Plateau Score and Overfitting Warning"
    - "Walk-Forward comparison table renders In-Sample vs Out-of-Sample performance with WFE ratio"
    - "Clicking 'Apply Optimal Parameters' updates Backtest Studio inputs and triggers backtest verification"
    - "Full test suite passes with zero regressions"
  failure_modes_and_recovery:
    - "Optimization in progress: Displays glowing spinner and disables run button"
    - "No trades in grid: Displays graceful warning state without breaking layout"
  handoff:
    next_plan: "END_OF_FEATURE"
    requires: "All 3 plans verified and passing"
```

---

## 2. Goal & Scope / User Jobs Served
This phase delivers the frontend user experience for parameter optimization within Backtest Studio:
- **Subtab Navigation**: Adds `⚡ Parameter Optimization & Walk-Forward` subtab alongside Single-Stock and Portfolio Basket backtests.
- **2D Color Heatmap Matrix**:
  - Dynamically rendered SVG matrix with continuous color interpolation (Deep Green for peak, Neutral Slate for median, Rose Red for drawdown).
  - Metric switcher buttons: `Sharpe Ratio`, `Net Realized P&L (₹)`, `Max Drawdown %`, `Win Rate %`.
  - Interactive cell inspection: Hover shows floating tooltip; click highlights cell and updates preview.
- **Stability & Walk-Forward HUD**:
  - 3x3 Plateau Stability Index badge (`ROBUST_PLATEAU` with green glow / `FRAGILE_CLIFF` with red warning alert).
  - Walk-Forward side-by-side performance cards: In-Sample vs. Out-of-Sample metrics with Walk-Forward Efficiency ($WFE$).
- **1-Click Workflow Closure**:
  - `⚡ Apply Optimal Parameters to Backtest` button transfers the best parameter settings to the Single-Stock Backtest tab, allowing immediate forward execution or full trade review.

---

## 3. Architecture & SOLID Principles Application
- **Controller-View Pattern**:
  - `BacktestOptimizationController` in `static/js/backtest_optimization_ui.js` encapsulates all optimization state, presets fetching, range inputs, SVG heatmap rendering, and event binding.
  - Non-intrusively hooks into `window.backtestUI` to populate single-stock parameters when "Apply" is clicked.
- **Design System Consistency**:
  - Reuses `--bg-surface`, `--border-color`, `#10b981` (emerald green), `#f43f5e` (rose red), and `#38bdf8` (sky blue accent) in `static/css/theme.css`.

---

## 4. UI Component Specifications

### 4.1 Subtab Bar Navigation in `#view-backtest`
```html
<div class="subtabs-bar" id="backtest-subtabs-nav">
    <button class="backtest-subtab active" id="btn-backtest-tab-single" data-subtab="single">📈 Single-Stock Backtest</button>
    <button class="backtest-subtab" id="btn-backtest-tab-portfolio" data-subtab="portfolio">🧺 Portfolio Basket Studio</button>
    <button class="backtest-subtab" id="btn-backtest-tab-optimize" data-subtab="optimize">⚡ Parameter Optimization & Walk-Forward</button>
</div>
```

### 4.2 Optimization Workspace Panel (`#backtest-optimize-panel`)
- **Control Bar**:
  - Strategy selector (synchronized with backtest studio).
  - Param 1 Range: Min, Max, Step.
  - Param 2 Range: Min, Max, Step.
  - Walk-Forward Split Slider (50% to 90%, default 70%).
  - `⚡ Run Optimization Grid` button.
- **Heatmap Card**:
  - Header with Metric Switcher: `Sharpe Ratio` | `Net P&L (₹)` | `Max Drawdown %` | `Win Rate %`.
  - SVG Matrix container `#opt-heatmap-svg` with axis labels and color legend.
- **Analytics & Walk-Forward HUD**:
  - 3x3 Plateau Stability Card: Score %, classification badge, and cliff warning.
  - Walk-Forward Card: In-Sample vs. Out-of-Sample comparison table with $WFE$ ratio.
  - Action footer: `⚡ Apply Optimal Parameters to Backtest`.

---

## 5. Implementation Steps
1. Create `static/js/backtest_optimization_ui.js`:
   - Implement `BacktestOptimizationController`:
     - `init()`, `bindSubtabs()`, `loadPresets()`, `bindPresetRanges()`, `runOptimization()`, `renderHeatmap()`, `renderStabilityHUD()`, `renderWalkForwardHUD()`, `applyOptimalParams()`.
2. Update `static/index.html`:
   - Add `#backtest-subtabs-nav` to Backtest Studio.
   - Inject `#backtest-optimize-panel`.
   - Register `<script src="/static/js/backtest_optimization_ui.js"></script>`.
3. Add CSS styling to `static/css/theme.css`:
   - Styles for heatmap grid, SVG cells, color legend, metric switcher, stability badges, and split slider.
4. Author comprehensive integration test `tests/integration/test_parameter_optimization_ui_integration.py`.

---

## 6. Verification & Acceptance Criteria
- `pytest tests/integration/test_parameter_optimization_ui_integration.py -v` passes 100%.
- Heatmap renders seamlessly across all 5 strategies.
- 1-Click Apply correctly transfers parameters to `BacktestUI`.
- Full repository test suite passes with zero regressions.
