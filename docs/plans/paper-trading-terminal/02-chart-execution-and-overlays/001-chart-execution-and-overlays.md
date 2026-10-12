# Plan 02-001: Chart Quick Execution Floating Bar & Visual Price Lines

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "01-engine-and-api/001-engine-and-api.md"
  reads:
    - "static/js/chart.js"
    - "static/index.html"
    - "static/css/theme.css"
  produces:
    - "static/js/chart_paper_trade.js"
    - "static/css/paper_trade.css"
    - "static/index.html"
  exposes:
    - "window.chartPaperTradeManager"
    - "window.chartPaperTradeManager.placeQuickOrder(side, qty)"
    - "window.chartPaperTradeManager.renderPositionLines(symbol)"
  must_not_modify:
    - "services/backtest_service.py"
    - "db/connection.py"
  test_plan:
    - "powershell -Command \"Invoke-WebRequest -Uri http://localhost:8000/static/js/chart_paper_trade.js -UseBasicParsing | Select-Object -Property StatusCode\""
    - "pytest tests/integration/test_static_asset_serving.py -v"
  definition_of_done:
    - "Floating Quick Trade bar renders on top-right of chart with [ BUY ₹LTP ], Quantity Stepper, and [ SELL ₹LTP ]"
    - "Clicking Buy or Sell immediately fires POST /api/v1/paper-trading/orders with active symbol and LTP"
    - "Horizontal price lines render for Entry (Blue line), Target (Green dashed line), and Stop Loss (Red dashed line) on chart series"
    - "Execution markers (Green arrow up for BUY, Red arrow down for SELL) render on candlestick chart series"
    - "Floating P&L badge updates in real time as price ticks move"
  failure_modes_and_recovery:
    - "API error or server offline -> Show toast notification with error detail and reset button state"
  handoff:
    - "Feeds order events and position changes to Plan 03 (Terminal Dock)"
```

---

## 1. Goal & Scope / User Jobs Served
Provide a TradingView-identical chart execution experience where traders can place orders directly from the chart canvas, adjust quantities with steppers, and visualize their open position levels (Entry, Take-Profit, and Stop-Loss) as persistent horizontal lines directly over price candles.

---

## 2. Architecture & SOLID Principles Application
- **Single Responsibility Principle (SRP):**
  - `chart_paper_trade.js` manages DOM creation for the floating order widget, communication with `/api/v1/paper-trading/`, and rendering Lightweight Charts price lines (`createPriceLine`).
  - `paper_trade.css` isolates styles for order buttons, stepper, order ticket modal, and position badges without polluting `theme.css`.
- **Open/Closed Principle (OCP):**
  - Uses Lightweight Charts `ISeriesApi.createPriceLine()` API allowing multiple order line overlays without mutating core candlestick logic.

---

## 3. UI/UX Specifications & Visual Design

### 3.1 Floating Quick Trade Bar Markup
```html
<div class="chart-quick-trade-bar" id="chart-quick-trade-bar">
    <button type="button" class="quick-trade-btn quick-buy-btn" id="btn-quick-buy">
        <span class="btn-side-lbl">BUY</span>
        <span class="btn-price-lbl font-mono" id="quick-buy-price">₹--</span>
    </button>
    <div class="quick-qty-stepper">
        <button type="button" class="qty-step-btn" id="btn-qty-minus">-</button>
        <input type="number" id="quick-trade-qty" class="qty-input font-mono" value="50" min="1" step="1">
        <button type="button" class="qty-step-btn" id="btn-qty-plus">+</button>
    </div>
    <button type="button" class="quick-trade-btn quick-sell-btn" id="btn-quick-sell">
        <span class="btn-side-lbl">SELL</span>
        <span class="btn-price-lbl font-mono" id="quick-sell-price">₹--</span>
    </button>
    <button type="button" class="quick-settings-btn" id="btn-quick-order-ticket" title="Advanced Order Ticket (SL / TP / Order Types)">
        ⚙️
    </button>
</div>
```

### 3.2 Visual Chart Overlays (Lightweight Charts Primitives)
- **Entry Price Line:**
  - Color: `#2962FF` (Royal Blue), Solid 2px, Label: `Entry: ₹2,850.00 (50 Qty)`.
- **Take-Profit (Target) Line:**
  - Color: `#089981` (Teal Green), Dashed line (Style: 2), Label: `Target: ₹2,950.00 (+₹5,000)`.
- **Stop-Loss Line:**
  - Color: `#F23645` (Vibrant Red), Dashed line (Style: 2), Label: `Stop Loss: ₹2,800.00 (-₹2,500)`.
- **Live Candle Markers:**
  - Green `arrowUp` below bar for Buy fills.
  - Red `arrowDown` above bar for Sell fills.

---

## 4. Implementation Steps
1. Create `static/css/paper_trade.css` with dark-themed, glassmorphic styling for `.chart-quick-trade-bar`, buttons, inputs, and order ticket modals.
2. Link `static/css/paper_trade.css` and `static/js/chart_paper_trade.js` in `static/index.html`.
3. Implement `ChartPaperTradeManager` in `static/js/chart_paper_trade.js`:
   - Initialize and mount quick trade bar to `.chart-container`.
   - Update quick buy/sell prices whenever live candles or hover updates occur.
   - Listen to Buy/Sell clicks, prompt confirmation or execute instant order.
   - Manage price line instances via `candleSeries.createPriceLine()` and remove them on position square-off.
4. Hook into symbol switch events: when user changes symbol in top search or clicks another stock, update active paper lines to match that stock's active position.

---

## 5. Verification & Acceptance Criteria
- Verify quick trade widget floats correctly at top-right of the chart without obscuring the OHLC HUD.
- Verify clicking BUY executes order and draws blue entry line and green target line.
- Verify changing stock symbol smoothly clears previous lines and displays lines for the new symbol (if positions exist).
