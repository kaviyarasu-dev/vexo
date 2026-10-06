# Phase 08: Interactive Quant Charting Interface & Downloader Dashboard

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "plan/00_MASTER_ARCHITECTURE.md"
    - "plan/01_ENVIRONMENT_CONFIG_AND_AUTH.md"
    - "plan/07_FASTAPI_BACKEND_AND_QUANT_APIS.md"
  reads:
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#2-canonical-timeframe-list"
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#5-canonical-api-contract-registry"
  produces:
    - "static/index.html"
    - "static/css/theme.css"
    - "static/css/chart.css"
    - "static/js/chart_manager.js"
    - "static/js/api_client.js"
    - "static/js/search_modal.js"
    - "static/js/export_modal.js"
    - "static/js/downloader_drawer.js"
    - "static/js/auth_modal.js"
  exposes: []
  must_not_modify:
    - "plan/*"
    - "services/*"
    - "db/*"
  test_plan:
    unit_tests: "tests/unit/test_frontend_helpers.py"
    integration_tests: "tests/integration/test_static_asset_serving.py"
    contract_tests: "tests/contract/test_frontend_api_bindings.py"
    fixtures: "tests/fixtures/sample_candles.json"
    command: "pytest tests/integration/test_static_asset_serving.py -v"
  definition_of_done:
    - item: 1
      command: "curl -s http://localhost:8000/static/index.html | grep 'id=\"chart-container\"'"
      result: "Frontend shell loads successfully from FastAPI static mount."
    - item: 2
      command: "python -c 'from api.server import app; from fastapi.testclient import TestClient; c = TestClient(app); r = c.get(\"/\"); assert r.status_code == 200 and \"LightweightCharts\" in r.text'"
      result: "Root URL serves HTML dashboard with Lightweight Charts script tags embedded."
    - item: 3
      command: "pytest tests/contract/test_frontend_api_bindings.py"
      result: "ApiClient correctly parses 00A ApiResponse envelopes and handles EXCEL_ROW_LIMIT_EXCEEDED gracefully."
  failure_modes_and_recovery:
    - failure: "Crosshair desynchronization between candlestick and oscillator sub-panes"
      detection: "Time misalignment during mousemove event across stacked panes"
      recovery: "ChartManager subscribes each pane to a centralized timeScale coordinate mapper"
    - failure: "API cursor pagination infinite loop on historical pan"
      detection: "Repeated API calls dispatched for identical cursor timestamp"
      recovery: "Track last_requested_cursor; halt fetch when next_cursor is null or matches last_requested_cursor"
  handoff:
    - "TradingView Lightweight Charts interactive interface implemented."
    - "Simple Mode and Pro Mode operational."
    - "Downloader drawer and Re-Auth UI active."
    - "Ready for Phase 09 Milestone 1 empirical verification."
```

---

## 1. Goal & Scope
Build a sleek, institutional-grade web interface using TradingView's Lightweight Charts, vanilla CSS design system, and modular JavaScript adhering to the 00A Canonical Registry.

This phase delivers:
- Dual UX Modes: **Simple Mode** (uncluttered, plain-language labels, guided tooltips for beginners) and **Pro Mode** (multi-pane crosshair-synchronized charting with all 11 canonical timeframes, Session VWAP, and oscillators). Refer to Phase 11 for complete persona specifications.
- Glossary tooltips: Hovering technical terms (e.g. VWAP, RSI, %B) displays plain-language conceptual summaries. Refer to Phase 18 for glossary content registry.
- Informative empty states for symbols undergoing backfill or fresh system installs.
- Re-Authentication & Token Telemetry in the top navigation bar: live countdown to access token expiration, 15-day refresh countdown, and one-click re-auth modal.
- Backward historical pan with infinite scroll / lazy-loading utilizing backend `limit` and `cursor` parameters.
- Downloader Progress & Telemetry drawer (live SSE metrics, throughput, pause/resume).
- One-click Data Export modal supporting Parquet, CSV, and Excel with live row-count guards.

---

## 2. SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `ApiClient`: Responsible solely for HTTP REST calls, cursor pagination, and SSE stream subscription.
  - `ChartManager`: Responsible solely for initializing Lightweight Charts panes, series, indicator overlays, and crosshair sync.
  - `AuthModal`: Responsible solely for displaying token expiration states and triggering credential renewal.
  - `ExportModal`: Responsible solely for configuring date ranges, validating Excel row limits, and initiating downloads.
- **Open/Closed Principle (OCP)**:
  - Indicator renderers adhere to `register_indicator(name, renderer_fn)`. Adding new overlay types requires registering a new renderer function without touching pan/zoom event handlers.

---

## 3. UI/UX & Visual Aesthetics Specifications

### 3.1. Design System Tokens (`static/css/theme.css`)
- **Theme**: Institutional Bloomberg / TradingView dark theme:
  - Background Base: `#0B0E14` (Deep obsidian).
  - Card & Surface: `#151924` (Elevated dark navy).
  - Borders: `#2A2E39` (Subtle boundary line).
  - Bullish Accent: `#089981` (Emerald Green).
  - Bearish Accent: `#F23645` (Crimson Red).
  - Session VWAP: `#F5AC00` (Gold Amber).
  - Secondary Overlays: `#2962FF` (Electric Royal Blue), `#AB47BC` (Purple).
- **Typography**: Inter for UI labels, Roboto Mono for candle coordinates and OHLC price readouts (guarantees zero horizontal jitter during crosshair movement).

---

## 4. Dual UX Modes: Simple vs Pro Mode

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [Logo] NSE Quant App  | [Search: Ctrl+K]  | Mode: [ Simple | ● Pro ]  | 🔑 Token: 07h 45m│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ PRO MODE TOPBAR: [1m|3m|5m|10m|15m|30m|1h|2h|4h|1D|1W] | Overlays: [VWAP|EMA|BB] | [Export]│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ MAIN CANDLESTICK PANE (Height: 70%)                                                    │
│  - Candles + Session VWAP (Gold) + 20 EMA (Cyan)                                       │
│  - Vertical dashed markers at 09:15 and 15:30 IST session boundaries                   │
│  - Crosshair HUD: O: 2580.0 | H: 2585.5 | L: 2578.0 | C: 2584.2 | VWAP: 2582.1         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ VOLUME SUB-PANE (Height: 15%)                                                          │
│  - Color-coded Volume bars synced to candle direction                                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ OSCILLATOR SUB-PANE (Height: 15% - Collapsible)                                        │
│  - RSI(14) with 70/30 bands OR MACD Line + Signal + Histogram                          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Simple Mode Experience**:
  - Hides oscillator sub-pane; displays single Candlestick + Volume pane.
  - Simplified timeframes: `1D`, `1W`, `1h`, `15m`.
  - Indicators labeled in plain English: "Intraday Average Price" (VWAP), "Trend Line" (20 EMA).
  - Hovering any technical label displays a beginner glossary tooltip.
- **Pro Mode Experience**:
  - Enables full 3-pane stacked layout with synchronized crosshairs.
  - Exposes all 11 canonical timeframes (`1m` through `1W`).
  - Full institutional indicator suite with parameter customization modals.

---

## 5. Technical Capabilities for Quant Traders

### 5.1. Cursor-Based Lazy-Loading on Historical Pan
When the user pans left toward the start of rendered candles:
1. `timeScale().subscribeVisibleLogicalRangeChange()` detects proximity to the left boundary ($< 50$ bars remaining).
2. `ApiClient.fetchCandles()` calls:
   `GET /api/v1/candles?symbol=...&timeframe=5m&limit=1000&cursor={earliest_timestamp}`.
3. API returns the preceding 1,000 candles and `next_cursor`.
4. `ChartManager` prepends new bars seamlessly without viewport jump or flickering.

### 5.2. Re-Authentication UI & Token Countdown
In top navigation bar:
- Badge shows live countdown: `🔑 Token: 07h 42m`.
- Color transitions:
  - $> 2\text{ hours}$: Green (`#089981`).
  - $30\text{m to } 2\text{ hours}$: Amber (`#F5AC00`).
  - $< 30\text{m}$ or Expired: Pulsing Red (`#F23645`).
- Clicking badge opens `AuthModal`:
  - Shows access token status and 15-day refresh window days remaining.
  - "Quick Refresh" button executes `POST /api/v1/auth/refresh`.
  - If 15-day window has expired, displays "Login via Browser" button opening OAuth flow.

### 5.3. Quant Data Export Dialog
- Formats:
  - **Apache Parquet**: Badged as "(Recommended for Python / Backtesting)".
  - **CSV**: Universal compatibility.
  - **Excel (.xlsx)**: With live row estimation.
- If selected date range exceeds 1,048,575 rows:
  - Excel radio button is disabled with explanatory warning tooltip:
    `"Excel row ceiling exceeded (1,048,575 rows). Please select Parquet or CSV."`

### 5.4. Downloader Telemetry Drawer
- Slides out from right edge:
  - Overall progress bar (Total NSE stocks completed / remaining).
  - Current symbol being processed and chunk range.
  - RateGovernor throughput: `Speed: 178 req/min (3.0 req/s)`.
  - Daily quota remaining: `Requests today: 39,500 / 90,000`.
  - Pause / Resume controls.

---

## 6. Implementation Steps
1. Create `static/css/theme.css` and `static/css/chart.css` containing dark theme tokens and responsive layouts.
2. Implement `static/js/api_client.js` with cursor pagination and SSE stream handlers.
3. Implement `static/js/chart_manager.js` wrapping Lightweight Charts:
   - Synchronizes crosshairs across Candlestick, Volume, and RSI sub-panes.
   - Implements Simple Mode vs Pro Mode pane toggles.
4. Implement `static/js/search_modal.js` handling `Ctrl+K` debounced symbol search.
5. Implement `static/js/export_modal.js` with 1,048,575 Excel row limit safety.
6. Implement `static/js/auth_modal.js` and live countdown timer.
7. Assemble `static/index.html`.

---

## 7. Verification & Acceptance Criteria
- Chart loads in $< 300\text{ ms}$ with smooth 60fps pan and zoom.
- Switching between Simple Mode and Pro Mode instantly toggles sub-panes and indicator complexity without losing viewport state.
- Moving the crosshair moves coordinates simultaneously across price, volume, and oscillator panes with synchronized time readouts.
- Panning back to the left edge triggers background API fetch using `cursor`; new candles prepend without layout distortion.
- Clicking "Export" with > 1,048,575 rows disables Excel export and presents clear tooltip guidance.
- Token countdown updates every minute; clicking opens re-auth modal with accurate expiry details.
