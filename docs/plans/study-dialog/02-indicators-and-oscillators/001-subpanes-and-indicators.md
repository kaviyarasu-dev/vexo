# Plan 02-001: Dynamic Sub-Panes & Technical Indicators Execution Engine

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - 01-modal-shell-and-catalog/001-modal-ui-and-catalog.md
  reads:
    - static/js/chart.js
    - services/indicators/momentum.py
    - services/indicators/volatility.py
    - services/indicators/vwap.py
  produces:
    - static/js/chart_studies.js
    - services/indicators/trend.py
    - services/indicators/oscillators.py
  exposes:
    - window.activeStudiesManager.addStudy(studyId, inputs)
    - window.activeStudiesManager.removeStudy(instanceId)
    - window.activeStudiesManager.toggleVisibility(instanceId)
  must_not_modify:
    - plan/_work/
    - data/market_data.duckdb
  test_plan:
    - python -m pytest tests/unit/test_indicators_extended.py
    - node -e "/* DOM test for dynamic chart sub-pane creation & time synchronization */"
  definition_of_done:
    - "Clicking an overlay indicator (SMA, EMA, VWAP, Bollinger Bands, Supertrend) adds it to main candlestick pane"
    - "Clicking an oscillator (RSI, MACD, Stochastic) dynamically generates a synchronized sub-pane below the main chart"
    - "Each active study displays an indicator HUD legend with current numerical value, hide/show eye toggle, settings gear, and remove button"
    - "Removing the last indicator in a sub-pane cleanly collapses and destroys the pane without layout gaps"
    - "Time scale and crosshair motion are 100% synchronized across all panes"
  failure_modes_and_recovery:
    - "Window resize or container zoom: Trigger handleResize on all sub-charts with requestAnimationFrame"
    - "Lightweight Charts v4 canvas recreation: Maintain persistent Series references in an ActiveStudiesMap"
  handoff:
    - "Exposes pane management architecture and series binding interfaces for Volume Profile in plan 03-001"
```

## 1. Goal & Scope / User Jobs Served
Enable seamless, multi-pane technical charting. Traders can add multiple overlay indicators (Moving Averages, Bollinger Bands, Supertrend) to the main price chart and stack multiple technical oscillator sub-panes (RSI 14, MACD 12-26-9, Stochastic Oscillator) with real-time synchronized crosshairs, legends, and independent y-axis scaling.

## 2. Architecture & SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `chart_studies.js`: Manages chart panes, series creation, calculation dispatch, and legend HUD state.
  - `trend.py` & `oscillators.py`: Pure quantitative calculation routines without UI side effects.
- **Liskov Substitution Principle (LSP)**:
  - All indicator classes adhere to `IIndicator` contract (`name()`, `required_columns()`, `compute()`).
- **Interface Segregation Principle (ISP)**:
  - Separate rendering paths for `OverlayStudy` (draws on main chart series) and `SubPaneStudy` (draws in dedicated sub-pane).

## 3. Mathematical & Core Logic Specifications
1. **Exponential Moving Average (EMA)**:
   $$\text{EMA}_t = \text{Close}_t \times \alpha + \text{EMA}_{t-1} \times (1 - \alpha), \quad \alpha = \frac{2}{\text{Period} + 1}$$
2. **Bollinger Bands**:
   $$\text{Middle} = \text{SMA}_{20}(\text{Close}), \quad \text{Upper} = \text{Middle} + (2 \times \sigma), \quad \text{Lower} = \text{Middle} - (2 \times \sigma)$$
3. **Supertrend ($N=10$, Multiplier=$3.0$)**:
   $$\text{Basic Upper} = \frac{\text{High} + \text{Low}}{2} + (3 \times \text{ATR}_{10})$$
   $$\text{Basic Lower} = \frac{\text{High} + \text{Low}}{2} - (3 \times \text{ATR}_{10})$$
   Flips trend when Close breaches the trailing stop level.
4. **Relative Strength Index (RSI 14)**:
   Wilder's smoothed average gain over average loss, oscillating between 0 and 100 with baseline levels at 30 and 70.
5. **MACD (12, 26, 9)**:
   $$\text{MACD Line} = \text{EMA}_{12} - \text{EMA}_{26}, \quad \text{Signal Line} = \text{EMA}_9(\text{MACD Line}), \quad \text{Histogram} = \text{MACD Line} - \text{Signal Line}$$
6. **Stochastic Oscillator (%K, %D)**:
   $$\%K = \frac{\text{Close} - \text{LowestLow}_{14}}{\text{HighestHigh}_{14} - \text{LowestLow}_{14}} \times 100, \quad \%D = \text{SMA}_3(\%K)$$

## 4. Domain Contracts & Service Interfaces
```javascript
// static/js/chart_studies.js
class ActiveStudiesManager {
    constructor(mainChart, mainContainer) { ... }
    addStudy(studyId, customInputs = {}) { ... }
    removeStudy(instanceId) { ... }
    toggleVisibility(instanceId) { ... }
    updateInputs(instanceId, newInputs) { ... }
    recalculateAll(candles) { ... }
    syncTimeScale(sourceRange) { ... }
}
```

## 5. Implementation Steps
1. Create `services/indicators/trend.py` implementing Supertrend and Multi-EMA indicators.
2. Create `services/indicators/oscillators.py` implementing Stochastic and Momentum oscillators.
3. Build `static/js/chart_studies.js`:
   - Implement `ActiveStudiesManager` singleton.
   - Implement dynamic sub-pane DOM scaffolding (`#study-subpanes-container`).
   - Implement crosshair synchronization across all sub-panes.
   - Implement indicator HUD legend overlay on each pane with Eye (hide/show), Gear (parameters modal), and `✕` (remove).
4. Integrate with `study_dialog.js`: Clicking "Add" in the modal dispatches to `window.activeStudiesManager.addStudy(studyId)`.
5. Add parameter configuration modal for updating periods, colors, and line widths.

## 6. Verification & Acceptance Criteria
- Adding SMA 20, SMA 50, and Bollinger Bands renders three cleanly colored lines on the main candle chart.
- Adding RSI creates a 120px sub-pane below the main chart with 70 and 30 dashed threshold lines.
- Adding MACD creates another 120px sub-pane with dual lines and colored histogram bars.
- Hovering crosshair over any pane synchronously updates the crosshair and legend values across all panes.
- Clicking `✕` on RSI removes the sub-pane and restores chart canvas height with 0 layout distortion.
