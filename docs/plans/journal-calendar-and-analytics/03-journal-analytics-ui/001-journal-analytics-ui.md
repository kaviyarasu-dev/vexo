# Plan 03-001: Journal Analytics UI: Monthly Green/Red Wall Calendar, Diagnostics Dashboard & Tabbed Workspace

## 1. Execution Contract
```yaml
execution_contract:
  plan_id: "03-001"
  name: "Journal Analytics UI: Monthly Green/Red Wall Calendar & Diagnostics Dashboard"
  feature: "journal-calendar-and-analytics"
  depends_on:
    - "01-001"
    - "02-001"
  reads:
    - "static/index.html"
    - "static/css/theme.css"
    - "static/js/journal_ui.js"
    - "api/routers/journal.py"
  produces:
    - "static/js/journal_analytics.js"
    - "tests/integration/test_journal_analytics_ui_integration.py"
  exposes:
    - "Subtab #journal-tab-calendar (Monthly P&L Wall Calendar)"
    - "Subtab #journal-tab-diagnostics (Quantitative Diagnostics)"
    - "Subtab #journal-tab-trades (Enhanced Trade Ledger)"
    - "Subtab #journal-tab-mistakes (Psychological Mistake Cloud)"
  must_not_modify:
    - "static/js/options_analytics.js"
    - "static/js/portfolio_backtest_ui.js"
    - "static/js/chart_drawings.js"
  test_plan:
    integration_tests: "pytest tests/integration/test_journal_analytics_ui_integration.py -v"
    command: "pytest tests/integration/test_journal_analytics_ui_integration.py -v"
  definition_of_done:
    - "Journal workspace features a responsive subtab bar switching between Calendar, Diagnostics, Trades, and Mistakes"
    - "Monthly Wall Calendar renders complete 7-day grid with month navigation, weekly total bars, and 6 monthly KPI badges"
    - "Date cells display Net ₹ P&L with vibrant green/red styling and click-to-filter interaction into the trade ledger"
    - "Quantitative Diagnostics tab renders Time-of-Day, Long/Short, and Duration visual breakdown cards"
    - "Enhanced import modal displays broker auto-detection feedback badge and file drag-and-drop support"
    - "Full test suite passes with zero regressions across all 313 existing tests"
  failure_modes_and_recovery:
    - "Month with no trades: Displays empty calendar grid with graceful 'No trades executed in this month' state"
    - "Offline / network error: Renders subtle warning banner without breaking existing UI components"
  handoff:
    next_plan: "END_OF_FEATURE"
    requires: "All 3 plans verified and passing"
```

---

## 2. Goal & Scope / User Jobs Served
The final phase brings the backend calendar and diagnostics APIs into a modern, institutional frontend user interface.
- **Tabbed Journal Navigation**: Reorganizes `#view-journal` into 4 dedicated subtabs (`📅 P&L Wall Calendar`, `📊 Quantitative Diagnostics`, `📜 Detailed Trade Log`, `🧠 Behavioral Mistake Cloud`).
- **Interactive Monthly Wall Calendar**:
  - Month Switcher (`◄ Prev Month`, `Next Month ►`, `October 2026`).
  - Monthly KPI Top Bar: Net Realized P&L, Win Days / Loss Days, Win Day %, Max Winning Streak, Max Losing Streak, Avg Win Day vs Avg Loss Day.
  - Interactive Date Cells: Day number, Net ₹ amount, Win/Loss trade ratio (`2W 1L`), and hover tooltips.
  - Weekly Summary Column: Weekly P&L and total trades on the right edge of each calendar row.
  - Click-to-Filter: Clicking any calendar day filters the Trade Ledger directly to that date.
- **Quantitative Diagnostics Dashboard**:
  - Horizontal visual comparison bars for Morning (09:15-10:30) vs. Midday (10:30-13:00) vs. Afternoon (13:00-15:30).
  - Direction breakdown (Long vs. Short).
  - Duration breakdown (Intraday vs. Swing).
- **Multi-Broker Import Modal**:
  - Auto-detection indicator badge (FYERS, Zerodha Console, Groww) updating dynamically upon CSV file selection.

---

## 3. Architecture & SOLID Principles Application
- **Controller-View Pattern**:
  - `JournalAnalyticsController` encapsulated in `static/js/journal_analytics.js` hooks into existing `JournalUI`.
  - Manages calendar month state, date rendering, diagnostics visualization, and modal workflows.
- **Design System Consistency**:
  - Reuses `--bg-surface`, `--border-color`, `--accent-color`, `#10b981` (emerald green for wins), and `#f43f5e` (rose red for losses) in `static/css/theme.css`.

---

## 4. UI Component Specifications

### 4.1 Subtab Bar Navigation
```html
<div class="subtabs-bar" id="journal-subtabs-nav">
    <button class="journal-subtab active" data-subtab="calendar">📅 P&L Wall Calendar</button>
    <button class="journal-subtab" data-subtab="diagnostics">📊 Quantitative Diagnostics</button>
    <button class="journal-subtab" data-subtab="trades">📜 Detailed Trade Log</button>
    <button class="journal-subtab" data-subtab="mistakes">🧠 Behavioral Mistake Cloud</button>
</div>
```

### 4.2 Wall Calendar Grid
- 7 columns for days of the week (Mon through Sun) + 1 column for `Weekly Total`.
- Grid cells with `.calendar-day-cell`, `.cell-win` (green glow/tint), `.cell-loss` (red glow/tint), `.cell-even`, `.cell-empty`.

---

## 5. Implementation Steps
1. Create `static/js/journal_analytics.js` implementing `JournalAnalyticsController`:
   - `init()`, `bindSubtabs()`, `switchSubtab()`, `loadCalendarMonth(year, month)`, `renderCalendar()`, `loadDiagnostics()`, `renderDiagnostics()`, `filterTradesByDate(date)`.
2. Update `static/index.html`:
   - Inject subtabs navigation bar into `#view-journal`.
   - Add `#journal-calendar-panel`, `#journal-diagnostics-panel`.
   - Wrap trade table into `#journal-trades-panel` and mistake cloud into `#journal-mistakes-panel`.
   - Register `<script src="/static/js/journal_analytics.js"></script>`.
3. Add CSS classes to `static/css/theme.css` for calendar grid, day cells, weekly bars, and diagnostic meters.
4. Author comprehensive integration test `tests/integration/test_journal_analytics_ui_integration.py`.

---

## 6. Verification & Acceptance Criteria
- `pytest tests/integration/test_journal_analytics_ui_integration.py -v` passes 100%.
- Month navigation seamlessly updates calendar cells and weekly summaries.
- Clicking any date cell successfully isolates trades executed on that date in the trade ledger.
- Full test suite passes with zero regressions across all 313 existing tests.
