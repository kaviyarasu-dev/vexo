# Plan 03-001: Real-Time Positions & Orders Terminal Dock, Trailing SL, and P&L Ticker

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "01-engine-and-api/001-engine-and-api.md"
    - "02-chart-execution-and-overlays/001-chart-execution-and-overlays.md"
  reads:
    - "static/index.html"
    - "static/css/paper_trade.css"
    - "static/js/chart_paper_trade.js"
  produces:
    - "static/js/paper_terminal_dock.js"
    - "static/css/paper_trade.css"
    - "static/index.html"
  exposes:
    - "window.paperTerminalDock"
    - "window.paperTerminalDock.refreshPositions()"
    - "window.paperTerminalDock.closePosition(positionId)"
    - "window.paperTerminalDock.resetAccount()"
  must_not_modify:
    - "services/backtest_service.py"
    - "db/connection.py"
  test_plan:
    - "powershell -Command \"Invoke-WebRequest -Uri http://localhost:8000/static/js/paper_terminal_dock.js -UseBasicParsing | Select-Object -Property StatusCode\""
    - "pytest tests/integration/test_static_asset_serving.py -v"
  definition_of_done:
    - "Collapsible terminal dock renders at the bottom of the chart workspace with Positions, Orders, Fills History, and Auto Strategies tabs"
    - "Real-time P&L ticker updates every 2 seconds or on candle tick with green/red badges"
    - "1-Click 'Square Off' button closes any position and plays a micro-animation confirming execution"
    - "Account Header shows Virtual Balance (₹10,00,000), Margin Utilized, and Reset Account button"
    - "Positions table lists Symbol, Side, Qty, Avg Price, LTP, P&L (₹), P&L (%), and Trailing SL"
  failure_modes_and_recovery:
    - "Network disconnection -> Show amber reconnection badge in dock header without crashing layout"
  handoff:
    - "Provides positions and terminal dock ready for algorithmic strategy triggers from Plan 04"
```

---

## 1. Goal & Scope / User Jobs Served
Provide a comprehensive bottom terminal interface that acts as the trader's command center for monitoring all open positions, trailing stop losses, order statuses, tax deductions, and portfolio margin usage with a 1-click square-off mechanism.

---

## 2. Architecture & SOLID Principles Application
- **Single Responsibility Principle (SRP):**
  - `paper_terminal_dock.js` coordinates tab switching, table rendering, polling/WebSocket quote updates, and user action triggers (Square Off, Risk Edit, Reset Account).
- **Interface Segregation Principle (ISP):**
  - Keeps order placement logic in `chart_paper_trade.js` while terminal monitoring and bulk closing live in `paper_terminal_dock.js`.

---

## 3. UI/UX Specifications & Terminal Layout

### 3.1 Terminal Dock HTML Structure
```html
<div class="paper-trading-dock" id="paper-trading-dock">
    <!-- Dock Header Bar -->
    <div class="paper-dock-header">
        <div class="dock-header-left">
            <span class="dock-title-icon">💼</span>
            <span class="dock-title">Paper Trading Terminal</span>
            <div class="dock-tabs">
                <button class="dock-tab active" data-dock-tab="positions">Positions <span id="dock-positions-count" class="badge-pill">0</span></button>
                <button class="dock-tab" data-dock-tab="orders">Orders <span id="dock-orders-count" class="badge-pill">0</span></button>
                <button class="dock-tab" data-dock-tab="history">Fills History</button>
                <button class="dock-tab" data-dock-tab="strategies">Auto Strategies <span id="dock-strat-count" class="badge-pill">0</span></button>
            </div>
        </div>
        <div class="dock-header-right">
            <div class="account-metric-pill">
                <span class="metric-lbl">Virtual Cash:</span>
                <span class="metric-val font-mono" id="dock-cash-val">₹10,00,000.00</span>
            </div>
            <div class="account-metric-pill">
                <span class="metric-lbl">Total Unrealized P&L:</span>
                <span class="metric-val font-mono" id="dock-pnl-val">₹0.00</span>
            </div>
            <button type="button" class="btn-dock-action" id="btn-dock-reset-account" title="Reset Account Balance to ₹10,00,000">
                🔄 Reset
            </button>
            <button type="button" class="btn-dock-toggle" id="btn-dock-toggle-view" title="Collapse / Expand Terminal">
                ▼
            </button>
        </div>
    </div>

    <!-- Dock Content Body -->
    <div class="paper-dock-body" id="paper-dock-body">
        <!-- Subpanel 1: Positions -->
        <div class="dock-panel active" id="dock-panel-positions">
            <table class="paper-table" id="table-paper-positions">
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Type</th>
                        <th>Side</th>
                        <th class="text-right">Qty</th>
                        <th class="text-right">Avg Entry (₹)</th>
                        <th class="text-right">LTP (₹)</th>
                        <th class="text-right">Unrealized P&L (₹)</th>
                        <th class="text-right">P&L (%)</th>
                        <th class="text-center">Stop Loss</th>
                        <th class="text-center">Target</th>
                        <th class="text-center">Action</th>
                    </tr>
                </thead>
                <tbody><!-- Dynamic rows --></tbody>
            </table>
        </div>

        <!-- Subpanel 2: Orders -->
        <div class="dock-panel hidden" id="dock-panel-orders">...</div>

        <!-- Subpanel 3: Fills History -->
        <div class="dock-panel hidden" id="dock-panel-history">...</div>

        <!-- Subpanel 4: Auto Strategies -->
        <div class="dock-panel hidden" id="dock-panel-strategies">...</div>
    </div>
</div>
```

---

## 4. Implementation Steps
1. Insert the `#paper-trading-dock` container markup below `#chart-subpanes-container` in `static/index.html`.
2. Add terminal styling in `static/css/paper_trade.css`:
   - Dark theme styling (`#131722` background, `#2a2e39` borders).
   - Responsive table layout with font-mono metrics.
   - Collapse/expand smooth CSS transition.
3. Implement `PaperTerminalDock` in `static/js/paper_terminal_dock.js`:
   - Tab switching between Positions, Orders, Fills History, and Auto Strategies.
   - Periodic 2-second polling of `/api/v1/paper-trading/positions` and `/api/v1/paper-trading/account`.
   - Calculate live mark-to-market using active symbol quotes.
   - Wire 1-Click "Square Off" button to `DELETE /api/v1/paper-trading/positions/{positionId}/close`.
   - Wire "Reset Account" button to `POST /api/v1/paper-trading/account/reset`.
4. Trigger cross-component event notifications:
   - When an order is placed in `chart_paper_trade.js`, notify `paperTerminalDock.refreshPositions()`.
   - When a position is closed in `paperTerminalDock`, notify `chartPaperTradeManager.clearPositionLines()`.

---

## 5. Verification & Acceptance Criteria
- Verify terminal dock mounts smoothly at bottom of chart.
- Verify clicking tabs correctly toggles panels.
- Verify placing a trade in Chart Quick Trade bar immediately appears as a row in the Positions table.
- Verify clicking "Square Off" closes the trade, removes the row, updates virtual cash, and clears chart price lines.
- Verify clicking "Reset" restores virtual cash to ₹10,00,000.
