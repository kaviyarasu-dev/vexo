# Plan 04-001: Patterns, Strategy Tester Dock & Options Studies Suite

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - 01-modal-shell-and-catalog/001-modal-ui-and-catalog.md
    - 02-indicators-and-oscillators/001-subpanes-and-indicators.md
    - 03-volume-profiles-and-market-profiles/001-volume-profiles.md
  reads:
    - static/js/chart.js
    - services/backtest_service.py
    - services/options_service.py
    - static/js/backtest_ui.js
    - static/js/options_ui.js
  produces:
    - static/js/chart_patterns.js
    - static/js/strategy_tester_dock.js
    - static/js/chart_options_overlay.js
    - services/pattern_recognition_service.py
    - api/routers/patterns.py
  exposes:
    - window.applyChartPattern(patternId)
    - window.applyChartStrategy(strategyId)
    - window.applyChartOptionsStudy(studyId)
  must_not_modify:
    - plan/_work/
    - data/market_data.duckdb
  test_plan:
    - python -m pytest tests/unit/test_pattern_recognition.py
    - node -e "/* DOM test for chart markers, strategy tester dock, and options overlays */"
  definition_of_done:
    - "Selecting any Candlestick Pattern (e.g. Bullish Engulfing, Hammer, Doji) scans active candles and renders crisp badge markers above/below corresponding bars"
    - "Hovering over a pattern badge displays an educational tooltip showing sentiment, confirmation rules, and historical accuracy"
    - "Selecting a Strategy (e.g. SMA Cross, RSI Reversal, Supertrend) computes trades, places Buy/Sell execution arrows on the chart, and reveals the Strategy Tester summary dock at the bottom"
    - "Clicking 'Deep Dive in Backtest Lab' navigates directly to the Backtest tab with current parameters pre-filled"
    - "Selecting Options studies renders Max Pain as horizontal benchmark line, PCR as sub-pane oscillator, and Strike OI as right-hand distribution"
    - "Traders can save active multi-indicator setups to 'My scripts' and load institutional presets from 'Editors picks'"
  failure_modes_and_recovery:
    - "Symbol is not optionable: Suppress options studies gracefully with a notification 'Options metrics available for F&O underlying symbols only'"
    - "Heavy candle history (>5000 bars): Execute pattern scanning asynchronously via Web Worker or vectorized backend endpoint"
  handoff:
    - "Complete integration connecting the TradingView modal to the full charting suite"
```

## 1. Goal & Scope / User Jobs Served
Bring the full power of TradingView's `Patterns`, `Strategies`, `Options`, and `Personal/Community` categories into the platform.
1. **Patterns**: Visual pattern recognition for price action traders without manual scanning.
2. **Strategies**: Instant feedback loop between visual chart signals and quantitative backtest metrics.
3. **Options**: Derivatives context (Max Pain, PCR, OI distribution) directly on equity charts.
4. **Personal/Community**: Template library allowing users to save their favorite workspaces and load institutional setups.

## 2. Architecture & SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `chart_patterns.js`: Pattern scanning, badge marker generation, and educational tooltip hover interactions.
  - `strategy_tester_dock.js`: Handles trade signal markers and the bottom strategy performance dock.
  - `chart_options_overlay.js`: Bridges options analytics with the chart price coordinates.
- **Dependency Inversion Principle (DIP)**:
  - Strategy dock connects to `IBacktestEngine` backend service via existing API contracts without duplication.

## 3. Mathematical & Algorithmic Specifications

### 3.1 Candlestick Pattern Rules
1. **Bullish Engulfing**:
   - Bar $i-1$: Bearish candle ($\text{Close}_{i-1} < \text{Open}_{i-1}$).
   - Bar $i$: Bullish candle ($\text{Close}_i > \text{Open}_i$).
   - Body condition: $\text{Open}_i \le \text{Close}_{i-1}$ and $\text{Close}_i \ge \text{Open}_{i-1}$.
2. **Bearish Engulfing**:
   - Bar $i-1$: Bullish candle ($\text{Close}_{i-1} > \text{Open}_{i-1}$).
   - Bar $i$: Bearish candle ($\text{Close}_i < \text{Open}_i$).
   - Body condition: $\text{Open}_i \ge \text{Close}_{i-1}$ and $\text{Close}_i \le \text{Open}_{i-1}$.
3. **Hammer**:
   - Lower shadow: $\text{Low} \le \min(\text{Open}, \text{Close}) - 2 \times |\text{Close} - \text{Open}|$.
   - Upper shadow: $\text{High} \le \max(\text{Open}, \text{Close}) + 0.2 \times |\text{Close} - \text{Open}|$.
   - Preceding short-term downtrend.
4. **Doji**:
   - Body condition: $|\text{Close} - \text{Open}| \le 0.1 \times (\text{High} - \text{Low})$.

### 3.2 Strategy Tester Dock
- On strategy selection, dispatches to `/api/v1/backtest/run`.
- Renders:
  - Buy Markers: Shape `'arrowUp'`, position `'belowBar'`, color `'#089981'`, text `'BUY'`.
  - Sell Markers: Shape `'arrowDown'`, position `'aboveBar'`, color `'#F23645'`, text `'SELL'`.
  - Strategy Tester Dock: Collapsible HUD docked at bottom showing `Net Profit (₹)`, `Win Rate (%)`, `Profit Factor`, `Max Drawdown (%)`, and `Total Trades`.

### 3.3 Options Studies on Chart
- **Max Pain**:
  $$\text{Cumulative Payout}(S) = \sum_{\text{Calls}} \max(0, S - K) \times \text{OI}_K + \sum_{\text{Puts}} \max(0, K - S) \times \text{OI}_K$$
  $$\text{Max Pain} = \arg\min_S \text{Cumulative Payout}(S)$$
- **Put-Call Ratio (PCR)**:
  $$\text{PCR} = \frac{\sum \text{Put Open Interest}}{\sum \text{Call Open Interest}}$$

## 4. Domain Contracts & Service Interfaces
```javascript
// static/js/chart_patterns.js
class PatternRecognitionEngine {
    scan(candles, enabledPatterns = []) {
        // returns array of marker objects { time, position, color, shape, text, tooltip }
    }
}

// static/js/strategy_tester_dock.js
class StrategyTesterDock {
    runAndDisplay(strategyId, symbol, timeframe, candles) { ... }
    closeDock() { ... }
}
```

## 5. Implementation Steps
1. Create `services/pattern_recognition_service.py` with vectorized pattern scanner for Engulfing, Hammer, Doji, Morning/Evening Star, Double Top/Bottom.
2. Create `api/routers/patterns.py` with `POST /api/v1/studies/patterns` returning timestamped markers.
3. Create `static/js/chart_patterns.js` rendering Lightweight Charts markers and educational tooltips.
4. Create `static/js/strategy_tester_dock.js` implementing the bottom dock HUD with performance statistics.
5. Create `static/js/chart_options_overlay.js` rendering Max Pain benchmark line and Strike OI histogram.
6. Connect `study_dialog.js` to dispatch:
   - Patterns -> `applyChartPattern()`
   - Strategies -> `applyChartStrategy()`
   - Options -> `applyChartOptionsStudy()`
   - My Scripts / Community -> Load/Save multi-indicator bundles in `localStorage`.

## 6. Verification & Acceptance Criteria
- Selecting "Bullish engulfing" marks every valid engulfing candle on the chart with a green `BE` marker.
- Hovering over a pattern marker reveals the pattern description tooltip.
- Selecting "SMA Crossover Strategy" renders green buy and red sell arrows on crossover bars and opens the Strategy Tester dock with win rate and P&L.
- Selecting "Max Pain" draws a dotted cyan horizontal benchmark line at the active strike price.
- Saving a setup to "My scripts" stores it and allows 1-click reapplication on any stock chart.
