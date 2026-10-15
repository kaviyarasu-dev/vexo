# Plan 03-001: Options Lab UI: ΔOI Bar Chart, Net Greeks Dashboard & Interactive Pre-Expiry Payoff Simulator

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "01-001"
    - "02-001"
  reads:
    - "static/js/options_ui.js"
    - "static/css/theme.css"
    - "api/models/options_models.py"
    - "api/routers/options.py"
  produces:
    - "static/js/options_analytics.js"
    - "tests/integration/test_options_lab_ui_integration.py"
  exposes:
    - "window.OptionsAnalyticsController"
    - "window.OptionsUI.prototype.switchOptionsTab"
  must_not_modify:
    - "core/interfaces.py"
    - "db/connection.py"
  test_plan:
    - "pytest tests/integration/test_options_lab_ui_integration.py -v"
  definition_of_done:
    - "Hybrid Underlying Selector allows 1-click Quick Index chips (NIFTY, BANKNIFTY, FINNIFTY) and searchable dropdown across 180+ NSE F&O equities"
    - "Dedicated Open Interest Analytics Tab renders Strike-by-Strike Dual Bar Chart comparing Total Call/Put OI and Call/Put ΔOI"
    - "PCR Trend Indicator displays Total PCR, Change PCR, and Market Sentiment badge (BULLISH, BEARISH, NEUTRAL)"
    - "Major Call Resistance, Major Put Support, and Max Pain callout badges prominently highlight key structural strike levels"
    - "Persistent Strategy Net Greeks HUD displays both unit Greek decimals and lot-size adjusted INR rupee values (₹/point, ₹/day, ₹/1% IV shift)"
    - "Interactive SVG Payoff Simulator plots both Expiration Hockey-Stick curve and Black-Scholes Target Date (T+x) theoretical curve"
    - "Interactive Target Date (Days to Expiry) and IV Shock (±20%) sliders warp theoretical curve smoothly in real time without lag"
    - "Expanded 1-click strategy presets provide Bull Call/Put, Bear Call/Put, Straddle, Strangle, Iron Condor, Iron Butterfly"
    - "Automated integration test tests/integration/test_options_lab_ui_integration.py passes with 100% assertions"
  failure_modes_and_recovery:
    - "Option chain data empty or API failure -> display institutional error banner with retry button without clearing active strategy legs"
    - "Zero total open interest on illiquid stock -> display neutral PCR badge with illiquidity disclaimer notice"
  handoff:
    - "Fulfills the complete institutional Options & Greeks Lab experience on the quantitative roadmap"
```

---

## 1. Goal & Scope / User Jobs Served
Empower quantitative derivatives traders and options desks with a TradingView / Sensibull caliber analysis laboratory. Traders can visually inspect Open Interest walls and intraday shifts ($\Delta\text{OI}$), assemble multi-leg spreads with instant Net Strategy Greek risk exposure in Indian Rupees (₹), and simulate pre-expiration P&L decay through real-time Target Date and Implied Volatility sliders.

---

## 2. UI/UX Architecture & Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│  OPTIONS LAB HEADER                                                    │
│  [ NIFTY (25) ] [ BANKNIFTY (15) ] [ FINNIFTY (25) ]  [ 🔍 Search 180+ F&O ] │
│  Spot: ₹25,050.25 | Expiry: 17-OCT-2026 | PCR: 1.15 (NEUTRAL)          │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│  NAVIGATION SUBTABS                                                    │
│  [ 📊 Option Chain Matrix ]  [ 📈 Open Interest (ΔOI) ]  [ 📐 Strategy & Payoff ] │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│  TAB 2: OPEN INTEREST (ΔOI) ANALYTICS                                  │
│  [ Major Resistance: 25,200 CE ] [ Major Support: 24,900 PE ] [ Max Pain: 25,050 ]│
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Strike-by-Strike Dual Bar Chart:                                 │  │
│  │ Call OI (Red) vs. Put OI (Green) | Call ΔOI vs. Put ΔOI          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│  TAB 3: STRATEGY BUILDER, NET GREEKS HUD & PRE-EXPIRY PAYOFF SIMULATOR │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Strategy Presets: [Bull Call] [Bear Put] [Straddle] [Iron Condor]│  │
│  │ Active Legs Table: Strike | Type | Pos | Qty | Premium | IV      │  │
│  ├──────────────────────────────────────────────────────────────────┤  │
│  │ NET GREEKS HUD (INR & Coefficients):                             │  │
│  │ Δnet: +0.28 (+₹7.0/pt) | Γnet: +0.0004 | Θnet: -₹105/day | ν: +₹170/1%│  │
│  ├──────────────────────────────────────────────────────────────────┤  │
│  │ PRE-EXPIRATION SIMULATION SLIDERS:                               │  │
│  │ Target Date: [─────●─────] 2 Days to Expiry (T+2)                │  │
│  │ IV Shock:    [──────●────] +0% IV                                │  │
│  ├──────────────────────────────────────────────────────────────────┤  │
│  │ INTERACTIVE SVG PAYOFF CHART:                                    │  │
│  │ ─── Expiration P&L (Hockey stick)                                │  │
│  │ ─── Target Date P&L (Curved Black-Scholes today)                 │  │
│  │ Breakeven: ₹25,085 | Max Profit: ₹2,875 | Max Loss: -₹2,125       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Client Controller Interface Specification

```javascript
/**
 * OptionsAnalyticsController
 * Manages Open Interest dual bar charts, Net Strategy Greeks HUD,
 * pre-expiration payoff sliders, and hybrid F&O ticker discovery.
 */
class OptionsAnalyticsController {
  constructor(optionsUI) {
    this.ui = optionsUI;
    this.activeTab = 'chain'; // 'chain' | 'open_interest' | 'payoff'
    this.selectedSymbol = 'NSE:NIFTY50-INDEX';
    this.fyersChain = null;
    this.oiAnalysis = null;
    this.underlyings = [];
    this.activeLegs = [];
    this.targetDays = 2.0;
    this.ivShock = 0.0;
  }

  init();
  switchOptionsTab(tabName);
  async loadUnderlyings();
  async loadOpenInterestData(symbol);
  renderOIBarChart(oiData);
  renderNetGreeksHUD(greeksData);
  async updatePayoffSimulation();
  renderPreExpiryPayoffChart(payoffData);
  applyStrategyPreset(presetName);
}
```

---

## 4. Implementation Steps
1. Create `static/js/options_analytics.js` implementing `OptionsAnalyticsController` and hooking into `OptionsUI`.
2. Add necessary CSS styling in `static/css/theme.css`:
   - Dual Bar Chart container and styling for Call/Put OI and $\Delta\text{OI}$ bars.
   - Strategy Net Greeks persistent HUD grid.
   - Target Date and IV Shock sliders.
   - Interactive SVG payoff curve elements and Breakeven markers.
3. Update `static/js/options_ui.js` and `static/index.html` to register and load `options_analytics.js`.
4. Author comprehensive integration test `tests/integration/test_options_lab_ui_integration.py` verifying:
   - Script serving (200 OK) and controller interface exposure.
   - DOM elements for Underlyings picker, OI dual-bar chart, Net Greeks HUD, and Pre-Expiry Payoff sliders.
   - API contract validation for all options analytics endpoints.
   - Preset application without console exceptions.

---

## 5. Verification & Acceptance Criteria
- `pytest tests/integration/test_options_lab_ui_integration.py -v` passes 100%.
- Sliding Target Date and IV Shock sliders updates the theoretical curved line smoothly at 60 FPS.
- Zero regressions across the full repository test suite.
