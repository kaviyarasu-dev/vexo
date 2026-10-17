# Plan 002: External Data Bhavcopy & Screener Delivery Columns

## Goal
Ingest daily UDiFF Bhavcopy automatically, compute Delivery % and FII/DII institutional activity, and expose them as filterable columns in the Stock Screener backend and UI:
1. Verify and wire UDiFF Bhavcopy ingestion in `scripts/fetch_bhavcopy_udiff.py`.
2. Extend DuckDB screener query in `services/screener_service.py` to support `delivery_pct` and `fii_dii_net`.
3. Add Delivery % filter sliders and table columns in `static/js/screener_ui.js`.
4. Verify screener test suite with new columns.

## Read first
- `trading-app/scripts/fetch_bhavcopy_udiff.py`
- `trading-app/services/external_data_service.py`
- `trading-app/services/screener_service.py`
- `trading-app/static/js/screener_ui.js`

## Steps

### Step 1: Wire UDiFF Bhavcopy ingestion pipeline
- Inspect `scripts/fetch_bhavcopy_udiff.py` and `services/external_data_service.py`.
- Ensure `fetch_udiff_bhavcopy(date_str)` handles standard NSE UDiFF CSV formats, parsing `TckrSymb`, `OpnPric`, `HghPric`, `LwPric`, `ClsPric`, `TtlTradgVol`, and `DlvryQty`.
- Calculate `delivery_pct = (DlvryQty / TtlTradgVol) * 100.0` and store in `candles_1d_raw` or auxiliary delivery table.

### Step 2: Extend DuckDB screener query for delivery and institutional metrics
- In `services/screener_service.py`, update `scan_universe()` SQL query.
- Add optional filter predicates:
  - `delivery_pct >= :min_delivery_pct`
  - `delivery_pct <= :max_delivery_pct`
- Include `delivery_pct` and `fii_dii_net` in the returned JSON records.

### Step 3: Update screener frontend UI controls
- In `static/js/screener_ui.js`, add a Delivery % filter slider and input box in the filter controls panel.
- Add a "Delivery %" column header and cell formatter displaying color-coded tags (>60% highlighted in green).

### Step 4: Run automated screener test suite
- Execute screener unit tests verifying filtering by delivery percentage and institutional net flows.
- Ensure all tests pass cleanly.

## Do not touch
- `trading-app/services/backtest/engine.py`
- `trading-app/api/routers/auth.py`

## Acceptance
Run:
```bash
.\.venv\Scripts\pytest.exe tests/unit/test_screener_filters.py tests/integration/test_screener_execution.py
```
All tests must pass with exit code 0.

## If blocked
Write exact error trace and attempted fixes to `docs/plans/platform-automation-and-backlog/BLOCKED.md` and stop.

## Report back
Provide test execution output confirming Bhavcopy parsing and screener delivery filtering.
