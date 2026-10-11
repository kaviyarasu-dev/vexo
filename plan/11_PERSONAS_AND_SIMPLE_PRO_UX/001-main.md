# Phase 11: User Personas, Journeys & Simple/Pro UX Architecture

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "plan/00_MASTER_ARCHITECTURE.md"
    - "plan/08_FRONTEND_CHARTING_AND_DASHBOARD.md"
  reads:
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#1-canonical-interface-registry"
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#2-canonical-timeframe-list"
  produces:
    - "static/js/ux_mode_controller.js"
    - "static/js/onboarding_tour.js"
    - "static/css/modes.css"
    - "config/ux_translations.json"
  exposes: []
  must_not_modify:
    - "plan/*"
    - "services/*"
    - "db/*"
  test_plan:
    unit_tests: "tests/unit/test_ux_translations.py"
    integration_tests: "tests/integration/test_mode_switching.py"
    contract_tests: "tests/contract/test_ux_config.py"
    fixtures: "config/ux_translations.json"
    command: "pytest tests/unit/test_ux_translations.py tests/contract/test_ux_config.py -v"
  definition_of_done:
    - item: 1
      command: "python -c 'import json; d = json.load(open(\"config/ux_translations.json\")); assert \"vwap\" in d and \"rsi\" in d'"
      result: "Translation dictionary maps all technical indicators to plain-language labels and glossary tooltips."
    - item: 2
      command: "pytest tests/integration/test_mode_switching.py"
      result: "Switching UX mode from Simple to Pro and back preserves chart viewport and symbol selection without reloading page."
    - item: 3
      command: "python -c 'import json; d = json.load(open(\"config/ux_translations.json\")); assert all(\"plain_label\" in v and \"beginner_summary\" in v for v in d.values())'"
      result: "100% of indicators and timeframes possess verified beginner-friendly explanations."
  failure_modes_and_recovery:
    - failure: "User local preference corruption resets mode"
      detection: "localStorage.getItem('quant_app_mode') returns invalid string"
      recovery: "Default safely to 'simple' mode and display onboarding prompt"
    - failure: "Technical indicator leaks into Simple Mode without plain translation"
      detection: "Unmapped technical acronym detected in Simple Mode DOM"
      recovery: "Translation helper falls back to humanized string and logs missing translation key"
  handoff:
    - "Simple Mode and Pro Mode controller operational."
    - "Plain-language translation registry compiled."
    - "Ready for Phase 12 screener engine implementation."
```

---

## 1. User Jobs & Persona Architecture
This application is designed specifically for two distinct personas operating over the exact same underlying market data. Features that serve neither persona are cut from scope.

```
                    [ Unified NSE Equity Database (DuckDB) ]
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
   [ Persona A: Beginner ]                              [ Persona B: Quant ]
   "Help me find and understand                         "Give me clean raw data, fast
   quality stocks with low risk."                       screeners, and honest backtests."
            │                                                     │
   [ Simple Mode Interface ]                            [ Pro Mode Interface ]
   - Plain-English labels                               - Multi-pane charts & crosshairs
   - 1-click curated scans                              - Custom SQL & script hooks
   - Glossary tooltips                                  - Zero-copy Parquet exports
   - Risk-first alerts                                  - Full Indian tax/fee backtest
```

### 1.1. Persona A: The Aspiring Indian Investor / Beginner
- **Profile**: Retail market participant, knows basic company names (Reliance, Tata, Infosys), intimidated by complex charting indicators, seeks guidance on risk and trend direction.
- **Core User Jobs**:
  1. *Find*: "Show me large, liquid companies that are near their 52-week highs or oversold without requiring me to write complex formulas."
  2. *Analyze*: "Explain whether the current price is considered high or low compared to today's average trading price."
  3. *Monitor*: "Alert me when a stock crosses a major support level or spikes in volume."
- **Key Constraints**: Zero jargon, no unexplained acronyms, risk warnings displayed prominently.

### 1.2. Persona B: The Quantitative Trader / Research Analyst
- **Profile**: Systematic trader, writes Python/Pandas scripts, runs backtests, demands high-fidelity tick/1m data, tests statistical edges.
- **Core User Jobs**:
  1. *Find*: "Scan 500 stocks across custom multi-factor criteria (RSI, VWAP distance, volume Z-scores) in under 2 seconds."
  2. *Analyze*: "Inspect synchronized multi-pane charts across multiple timeframes with exact IST session alignment."
  3. *Test*: "Backtest an intraday or swing strategy with exact Indian statutory taxes (STT, stamp duty, SEBI fees, GST) and verify slippage."
  4. *Export*: "Stream millions of rows directly into Parquet files for Jupyter notebook workflows."
- **Key Constraints**: Local data ownership, sub-millisecond query speed, zero lookahead bias, zero survivorship distortion.

---

## 2. SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `UxModeController`: Manages client-side mode transitions, visibility classes, and layout adaptations.
  - `TranslationRegistry`: Manages technical-to-plain text translation mappings.
  - `OnboardingTour`: Coordinates interactive user walkthroughs for first-time visitors.
- **Open/Closed Principle (OCP)**:
  - Mode configurations adhere to component visibility registries. Adding a new widget requires defining its visibility matrix entry without modifying existing layout handlers.

---

## 3. Simple Mode vs Pro Mode Specification

### 3.1. Component Visibility Matrix
| UI Component / Feature | Simple Mode | Pro Mode | Rationale |
|---|---|---|---|
| **Main Candlestick Pane** | Visible (Full Width) | Visible (70% Height) | Both users need primary price visualization. |
| **Volume Sub-Pane** | Simple Volume Bars | Volume + 20-period MA | Beginners only need trade activity; quants need volume moving average. |
| **Oscillator Sub-Pane (RSI/MACD)** | **Hidden** | **Visible (15% Height)** | Oscillators confuse beginners; essential for systematic momentum analysis. |
| **Timeframe Switcher** | `1D`, `1W`, `1h`, `15m` | Full 11 Canonical Timeframes | Beginners do not trade 1-minute noise; quants require micro-timeframes. |
| **Session VWAP Overlay** | Labeled "Intraday Average" | Labeled "Session VWAP" | Removes jargon while preserving mathematical utility. |
| **Technical Indicators Menu** | Top 3 Simple Presets | Full Indicator Suite + Config | Prevents cognitive overload. |
| **Data Export Modal** | CSV & Excel (with warnings) | **Apache Parquet**, CSV, Excel | Parquet is recommended for data scientists; unnecessary for beginners. |
| **Screener Filters** | 1-Click Cards ("Safe Giants") | Multi-Factor Query Builder | Beginners use curated templates; quants construct custom formulas. |
| **Backtest Execution** | No-Code Wizard | Script Hook + Parameter Grids | Simple backtesting wizard for beginners; granular parameters for quants. |

### 3.2. Plain-Language Translation Dictionary (`config/ux_translations.json`)
```json
{
  "vwap": {
    "pro_label": "Session VWAP",
    "plain_label": "Intraday Average Price",
    "beginner_summary": "The average price weighted by trade volume today. Prices above this line indicate buyers are currently in control.",
    "risk_tip": "Buying far above the average price increases your risk of buying at the top."
  },
  "rsi": {
    "pro_label": "RSI (14)",
    "plain_label": "Momentum Meter (Speed of Price Moves)",
    "beginner_summary": "Measures how fast a stock is rising or falling on a scale of 0 to 100. Over 70 indicates potentially overheated; under 30 indicates heavily sold.",
    "risk_tip": "Oversold does not guarantee an immediate bounce. In strong downtrends, prices can stay oversold for weeks."
  },
  "bollinger_bands": {
    "pro_label": "Bollinger Bands (20, 2)",
    "plain_label": "Normal Price Range Tunnel",
    "beginner_summary": "An envelope showing where prices trade 95% of the time. Prices touching the outer bands are at statistical extremes.",
    "risk_tip": "When bands contract tightly, an explosive price breakout in either direction is usually imminent."
  }
}
```

---

## 4. Measurable UX Target Gates
- **Time-to-First-Chart (Beginner Target)**:
  - A first-time user launching the application lands on a clean Simple Mode chart of `NSE:RELIANCE-EQ` with live data in **$< 5.0\text{ seconds}$**.
- **Clicks-to-First-Scan (Beginner Target)**:
  - From the homepage, a user discovers and executes a pre-built scan ("Nifty 50 High-Volume Leaders") in **$\le 2\text{ clicks}$**.
- **Mode Switching Latency**:
  - Toggling between Simple Mode and Pro Mode reconfigures the DOM in **$< 50\text{ ms}$** without triggering full page reloads or disconnecting active Server-Sent Event (SSE) streams.

---

## 5. Guided First-Scan Onboarding Tour
When a user launches the application for the first time:
1. **Welcome Modal**: Asks one simple question: *"How do you trade?"*
   - Option A: *"I'm learning / I prefer simple charts and clear explanations."* $\rightarrow$ Sets Simple Mode, launches guided tour.
   - Option B: *"I'm an experienced trader or quant researcher."* $\rightarrow$ Sets Pro Mode, opens full multi-pane chart with shortcuts guide (`Ctrl+K`).
2. **Interactive 3-Step Simple Tour**:
   - Step 1: Highlights the Search Bar (`Ctrl+K`) to find any NSE stock.
   - Step 2: Points to the "Intraday Average Price" line explaining what above/below means.
   - Step 3: Demonstrates the 1-Click Screener button to find today's active stocks.
3. User can toggle modes at any time via the topbar toggle `[ Simple | ● Pro ]`.

---

## 6. Implementation Steps
1. Create `config/ux_translations.json` compiling plain-language translations and glossary entries for all indicators and timeframes.
2. Create `static/css/modes.css` defining visibility utility classes (`.mode-simple-only`, `.mode-pro-only`, `.mode-adaptive`).
3. Implement `static/js/ux_mode_controller.js`:
   - Reads/writes active mode from `localStorage`.
   - Listens to mode toggle switch and updates DOM classes.
   - Attaches hover listeners for glossary tooltips in Simple Mode.
4. Implement `static/js/onboarding_tour.js` handling first-time visitor setup.

---

## 7. Verification & Acceptance Criteria
- Loading `index.html` with empty `localStorage` initializes in Simple Mode and prompts the welcome modal.
- Switching to Pro Mode reveals the oscillator sub-pane, exposes 1m/3m timeframes, and changes indicator labels to technical abbreviations.
- In Simple Mode, hovering the "Intraday Average Price" label displays a tooltip with plain-language explanation and risk warning.
- Clicking a 1-click screener card updates the table with filtered stocks in $\le 2\text{ clicks}$.
- Automated browser integration test verifies mode switching completes in $< 50\text{ ms}$ without JavaScript errors.
