# Feature Plan State: Trade Journal Analytics: Monthly Green/Red P&L Calendar, Time-of-Day Diagnostics & Multi-Broker Importers

- **Slug**: `journal-calendar-and-analytics`
- **Feature Name**: Trade Journal Analytics: Monthly Green/Red P&L Calendar, Time-of-Day Diagnostics & Multi-Broker Importers
- **Status**: ALL PLANS COMPLETED & VERIFIED [STATUS: DONE]
- **Parent Initiative**: Institutional Quantitative Trader Roadmap (Priority Tier P1)
- **Manifest**: `docs/plans/journal-calendar-and-analytics/manifest.json`

## Milestones & Plans
1. [DONE] Requirements Definition & User Alignment (/grill-me)
2. [DONE] Architecture & Mathematical Specification
3. [DONE] Plan Files & Manifest Creation (`docs/plans/journal-calendar-and-analytics/manifest.json`)
4. [DONE] Plan 01-001: Calendar Engine & Quantitative Diagnostics API
   - Task File: `01-calendar-and-diagnostics-api/001-calendar-and-diagnostics-api.md`
   - Gate: true
   - Verify: `pytest tests/unit/test_journal_calendar_engine.py tests/integration/test_journal_calendar_api.py -v` (PASSED: 7/7 tests)
5. [DONE] Plan 02-001: Multi-Broker Tradebook Import Engine (FYERS, Zerodha Console, Groww)
   - Task File: `02-multi-broker-importers/001-multi-broker-importers.md`
   - Gate: true
   - Verify: `pytest tests/unit/test_multi_broker_importers.py tests/integration/test_multi_broker_import_api.py -v` (PASSED: 10/10 tests)
6. [DONE] Plan 03-001: Journal Analytics UI: Monthly Green/Red Wall Calendar, Diagnostics Dashboard & Tabbed Workspace
   - Task File: `03-journal-analytics-ui/001-journal-analytics-ui.md`
   - Gate: true
   - Verify: `pytest tests/integration/test_journal_analytics_ui_integration.py -v` (PASSED: 5/5 tests)

## Execution Gate Order
- `01-001` (Core calendar aggregation, streak computation, session time-of-day analytics & REST router)
- `02-001` (Multi-broker tradebook CSV auto-detector, Zerodha Console & Groww parsers, FIFO trade reconciler)
- `03-001` (Interactive Wall Calendar UI, monthly KPI header, weekly summaries, time-of-day visual charts & tabbed journal workspace)
