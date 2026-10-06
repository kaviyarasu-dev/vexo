# NSE Quant Platform — Agent Execution Runbook

> **Purpose**: Ovvoru new conversation-layum enna prompt paste pananumnu exact-aa solludha user guide.
> **Enna apply aagum**: This entire project is split into 20 **phases**. Each phase runs in a **separate, fresh Antigravity conversation**. Copy-paste the prompt for that phase. Do not run two phases in the same conversation.

---

## GLOBAL RULES (Read Once, Follow Always)

Before pasting any phase prompt, remember:

1. **One Phase = One Fresh Conversation** — Never run two phases in the same chat.
2. **Use `/goal` slash command** — Type `/goal` before your prompt so the agent works autonomously until done.
3. **`plan/_work/` is FORBIDDEN** — The agent must never read or write to `plan/_work/`. It is an internal orchestrator scratchpad.
4. **After each phase ends** — Check that `plan/HANDOFF.md` has a new `STATUS: DONE` entry for that phase before starting the next.
5. **Phase 09 is a HARD GATE** — Do NOT start Phase 10, 12, 14, 15 until Phase 09's benchmark script passes all 5 gates.
6. **Phase 15 before Phase 14 and 12** — Corporate actions must be ingested before the backtester or screener runs.

---

## PHASE EXECUTION ORDER AT A GLANCE

```
Stage 1 (Sequential):  00A -> 00 -> 01 -> 02 -> 03
Stage 2 (Sequential):  04 -> 05 -> 06 -> 07 -> 08
Stage 3 (HARD GATE):   09  <- ALL 5 BENCHMARKS MUST PASS
Stage 4 (Sequential):  10 -> 11 -> 15 -> 12 -> 13 -> 14 -> 16 -> 17 -> 18
Cross-cutting:         19 (run last as final audit)
```

---

## STAGE 1: CORE FOUNDATION

### Conversation 1 — Phase 00A & 00: Canonical Contracts + Core Interfaces

```
/goal

You are implementing Phase 00A and Phase 00 of the NSE Quant Platform.

CONTEXT:
- Workspace root: d:\trading-app
- All authoritative specs are in plan/ folder
- NEVER read or write plan/_work/ — it is forbidden

TASK:
1. Read plan/00A_CONTRACTS_AND_CONVENTIONS.md completely.
2. Read plan/00_MASTER_ARCHITECTURE.md completely.
3. Implement exactly what the EXECUTION_CONTRACT section of plan/00_MASTER_ARCHITECTURE.md specifies under "produces":
   - core/__init__.py
   - core/interfaces.py  (all 15 canonical interface classes listed in 00A Section 1)
   - core/exceptions.py  (all exception types)
   - config/constants.py (all canonical timeframes, env defaults, rate limits)
4. Run the test command from the plan's definition_of_done section.
5. When all definition_of_done items pass, append a STATUS: DONE entry to plan/HANDOFF.md for Phase 00.

CRITICAL RULES:
- Interface names must match EXACTLY what 00A Section 1 specifies (e.g., ICandleReader, IBacktestEngine).
- No application logic in this phase. Abstract base classes and exception hierarchy ONLY.
- Do NOT invent any interface method signatures not present in 00A.
- Typed code only (use Python type hints and ABC).
```

SUCCESS CHECK: `python -c "import core.interfaces as ci; assert hasattr(ci, 'ICandleReader') and hasattr(ci, 'IBacktestEngine')"` exits with code 0.

---

### Conversation 2 — Phase 01: Settings, Vault & Fyers Auth Manager

```
/goal

You are implementing Phase 01 of the NSE Quant Platform.

CONTEXT:
- Workspace root: d:\trading-app
- Phase 00 is already complete (core/ folder exists)
- NEVER read or write plan/_work/

TASK:
1. Read plan/01_ENVIRONMENT_CONFIG_AND_AUTH.md completely.
2. Read these specific sections of plan/00A_CONTRACTS_AND_CONVENTIONS.md:
   - Section 1 (IAuthService interface)
   - Section 6 (Canonical Configuration Key Registry)
3. Implement exactly what the EXECUTION_CONTRACT "produces" section specifies:
   - config/settings.py     (Pydantic BaseSettings, all env keys from 00A Section 6)
   - services/vault.py      (OS Keyring integration; fallback to AES-256 encrypted data/.vault.enc)
   - services/auth_service.py (IAuthService implementation — dual-token lifecycle)
   - scripts/generate_token.py (one-shot Fyers token generation via PyFyers SDK)
4. Run the test command from the plan's definition_of_done section.
5. Append STATUS: DONE entry to plan/HANDOFF.md for Phase 01.

CRITICAL RULES:
- Tokens must NEVER be stored in plain .env. Use OS Keyring or the encrypted vault ONLY.
- The app must show a countdown timer when the 15-day refresh token is within 48 hours of expiry.
- A pre-flight session check must probe auth status at 15:40 IST before the daily sync.
- If unsure about any Fyers v3 endpoint, read plan/VERIFICATION_REPORT.md for verified facts.
```

SUCCESS CHECK: `python scripts/generate_token.py --dry-run` exits code 0 and shows vault path (no secrets printed).

---

### Conversation 3 — Phase 02: DuckDB Schema & Concurrency Engine

```
/goal

You are implementing Phase 02 of the NSE Quant Platform.

CONTEXT:
- Workspace root: d:\trading-app
- Phase 00 and 01 are already complete
- NEVER read or write plan/_work/

TASK:
1. Read plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md completely.
2. Read these sections of plan/00A_CONTRACTS_AND_CONVENTIONS.md:
   - Section 3 (Canonical DB Schema Registry — all 9 tables + 2 adjusted views)
   - Section 8 (Process & Concurrency Architecture)
3. Implement exactly what the EXECUTION_CONTRACT "produces" section specifies:
   - db/__init__.py
   - db/connection.py    (single write connection + async writer queue; reader cursors)
   - db/migrations.py   (9 table DDLs + 2 dynamic adjusted views, schema_version table)
   - db/repositories.py (ICandleWriter, ICandleReader, ICheckpointRepository implementations)
4. Run the test command from the plan's definition_of_done section.
5. Append STATUS: DONE to plan/HANDOFF.md for Phase 02.

CRITICAL RULES:
- Single writer process — uvicorn workers=1 always.
- Read queries use conn.cursor() independent cursors — they do NOT acquire the writer lock.
- Raw tables (candles_1m_raw, candles_1d_raw) are append-only. Adjusted prices come from SQL VIEWs only.
- Use staging table + anti-join deduplication for bulk inserts (NOT PRIMARY KEY on hot table).
- All DuckDB migration SQL must be idempotent (CREATE TABLE IF NOT EXISTS, CREATE VIEW OR REPLACE).
```

SUCCESS CHECK: `pytest tests/integration/test_db_concurrency.py -v` — all tests pass, zero lock timeouts.

---

### Conversation 4 — Phase 03: Symbol Master & Universe Manager

```
/goal

You are implementing Phase 03 of the NSE Quant Platform.

CONTEXT:
- Workspace root: d:\trading-app
- Phase 00, 01, 02 are complete
- NEVER read or write plan/_work/

TASK:
1. Read plan/03_SYMBOL_MASTER_AND_UNIVERSE_MANAGER.md completely.
2. Read plan/00A_CONTRACTS_AND_CONVENTIONS.md Section 9 (Universe Definitions & Tier Arithmetic).
3. Implement exactly what the EXECUTION_CONTRACT "produces" section specifies:
   - scripts/fetch_symbol_master.py   (downloads Fyers NSE_CM.csv; parses columns; seeds symbols table)
   - scripts/fetch_nse_constituents.py (downloads Nifty 50/Next50/Midcap150/Smallcap250 CSVs from NSE)
   - services/symbol_service.py       (ISymbolRepository; tier classification; holiday calendar)
   - data/overrides/universe_override.json (empty template for manual constituent overrides)
4. Run the test command from the plan's definition_of_done section.
5. Append STATUS: DONE to plan/HANDOFF.md for Phase 03.

CRITICAL RULES:
- Tier arithmetic MUST be: Tier1=100, Tier2=150, Tier3=250. Total=500. Tier4=remaining EQ stocks.
- NO hand-typed constituent lists in code. Scripts fetch from official NSE URLs only.
- Holidays come from the fetched calendar, NOT hardcoded dates.
- Symbol master columns from plan/VERIFICATION_REPORT.md (Fyers NSE_CM.csv has no header row).
```

SUCCESS CHECK: `python scripts/fetch_symbol_master.py --dry-run` prints symbol count >= 1800 and tier breakdown.

---

## STAGE 2: INGESTION PIPELINE & UI

### Conversation 5 — Phase 04: RateGovernor & Historical Downloader

```
/goal

You are implementing Phase 04 of the NSE Quant Platform.

CONTEXT:
- Workspace root: d:\trading-app
- Phases 00-03 are complete
- NEVER read or write plan/_work/

TASK:
1. Read plan/04_HISTORICAL_DOWNLOADER_ENGINE.md completely.
2. Read plan/00A_CONTRACTS_AND_CONVENTIONS.md Section 7 (Global RateGovernor Specification).
3. Implement exactly what the EXECUTION_CONTRACT "produces" section specifies:
   - core/rate_governor.py          (global token-bucket: 10/s burst, 180/min sustained, 90000/day cap; 3 priority lanes)
   - services/downloader_service.py  (IMarketDataProvider; calendar chunker; resumable checkpoint walk)
   - scripts/run_initial_backfill.py (entry point for full historical download)
4. Run the test command from the plan's definition_of_done section.
5. Append STATUS: DONE to plan/HANDOFF.md for Phase 04.

CRITICAL RULES:
- Fyers limit: 200 req/min hard cap. Our target: 180 req/min. NEVER exceed 200.
- End-of-history stop condition: ONLY when (>= 3 consecutive empty chunks) AND (chunk_start < listing_date).
- Error -300 is TRANSIENT — retry with backoff, do NOT treat as permanent stop.
- All Fyers calls go THROUGH the RateGovernor — never bypass it.
- Chunk sizes: 100 calendar days for 1m; 366 calendar days for 1D.
```

SUCCESS CHECK: `python scripts/run_initial_backfill.py --symbol NSE:RELIANCE-EQ --dry-run` prints request budget math and exits without API calls.

---

### Conversation 6 — Phase 05: Resampling & Indicators Engine

```
/goal

You are implementing Phase 05 of the NSE Quant Platform.

CONTEXT:
- Workspace root: d:\trading-app
- Phases 00-04 are complete
- NEVER read or write plan/_work/

TASK:
1. Read plan/05_RESAMPLING_AND_QUANT_METRICS_ENGINE.md completely.
2. Read plan/00A_CONTRACTS_AND_CONVENTIONS.md Section 2 (Canonical Timeframe List with IST session rules).
3. Implement exactly what the EXECUTION_CONTRACT "produces" section specifies:
   - services/resampling_service.py  (IResamplingService; DuckDB time_bucket with origin '2000-01-01 03:45:00')
   - services/indicators/            (IIndicator: SMA, EMA, RSI, VWAP, Bollinger, MACD, ATR, SuperTrend)
   - tests/fixtures/golden_candles/  (golden fixture files for all 11 canonical timeframes)
4. Run the test command from the plan's definition_of_done section.
5. Append STATUS: DONE to plan/HANDOFF.md for Phase 05.

CRITICAL RULES:
- IST opens at 09:15 IST = 03:45 UTC. DuckDB origin MUST be TIMESTAMP '2000-01-01 03:45:00'.
- Zero-volume bars: flag with is_zero_volume=TRUE — do NOT drop them.
- All resampling reads from candles_1m_adjusted VIEW, not raw table.
- Session stub bar counts (09:15-15:30): 30m=13, 1h=7, 2h=4, 4h=2.
- Golden fixture tests must cover all 11 timeframes: 1m, 3m, 5m, 10m, 15m, 30m, 1h, 2h, 4h, 1D, 1W.
```

SUCCESS CHECK: `pytest tests/unit/test_resampling_golden_fixtures.py -v` — all 11 timeframe fixtures pass.

---

### Conversation 7 — Phase 06: Daily Scheduler & Incremental Sync

```
/goal

You are implementing Phase 06 of the NSE Quant Platform.

CONTEXT:
- Workspace root: d:\trading-app
- Phases 00-05 are complete
- NEVER read or write plan/_work/

TASK:
1. Read plan/06_DAILY_INCREMENTAL_UPDATE_AND_SCHEDULER.md completely.
2. Read plan/00A_CONTRACTS_AND_CONVENTIONS.md Section 7 (RateGovernor Lane 3 budget for background sync).
3. Implement exactly what the EXECUTION_CONTRACT "produces" section specifies:
   - services/scheduler_service.py   (APScheduler cron: '45 15 * * 1-5' Asia/Kolkata; missed-run catchup on startup)
   - services/trading_calendar.py    (holiday lookup from DuckDB market_holidays table)
4. Run the test command from the plan's definition_of_done section.
5. Append STATUS: DONE to plan/HANDOFF.md for Phase 06.

CRITICAL RULES:
- Cron expression: '45 15 * * 1-5' with timezone='Asia/Kolkata'. 5-field only. No UTC cron.
- Pre-flight auth probe runs at 15:40 IST. If auth fails, scheduler enters FAILED_AUTH standby.
- On startup, if last sync missed > 0 market days, run catchup silently in the background.
- Daily sync budget: ~2,500 requests, completes in ~13.9 min at 180 req/min.
```

SUCCESS CHECK: `pytest tests/unit/test_scheduler_cron.py -v` — cron fires only on weekdays, skips holidays.

---

### Conversation 8 — Phase 07: FastAPI Backend & Exporters

```
/goal

You are implementing Phase 07 of the NSE Quant Platform.

CONTEXT:
- Workspace root: d:\trading-app
- Phases 00-06 are complete
- NEVER read or write plan/_work/

TASK:
1. Read plan/07_FASTAPI_BACKEND_AND_QUANT_APIS.md completely.
2. Read plan/00A_CONTRACTS_AND_CONVENTIONS.md Section 4 (API Contract Registry).
3. Implement exactly what the EXECUTION_CONTRACT "produces" section specifies:
   - api/__init__.py
   - api/routers/candles.py     (GET /api/v1/candles with limit + cursor pagination)
   - api/routers/symbols.py     (GET /api/v1/symbols/search)
   - api/routers/export.py      (GET /api/v1/export/excel and /parquet — streaming responses)
   - api/routers/health.py      (GET /health and /ready)
   - services/export_service.py (IDataExporter — Excel capped at 1,048,575 data rows)
   - main.py                    (FastAPI app, uvicorn workers=1, structured logging middleware)
4. Run the test command from the plan's definition_of_done section.
5. Append STATUS: DONE to plan/HANDOFF.md for Phase 07.

CRITICAL RULES:
- ALL responses use standard envelope: {data, meta, error{code, message, correlation_id}}.
- Excel ceiling: exactly 1,048,575 data rows (+ 1 header = 1,048,576 total). Return HTTP 400 EXCEL_ROW_LIMIT_EXCEEDED if breached.
- Parquet: COPY TO writes to data/exports/tmp_{uuid}.parquet; stream via FileResponse; delete with BackgroundTask.
- Cursor pagination: opaque base64-encoded offset.
- uvicorn must start with workers=1 — single process, single DuckDB writer.
```

SUCCESS CHECK: `curl http://localhost:8000/health` returns `{"status":"ok"}`.

---

### Conversation 9 — Phase 08: TradingView Chart UI & Dashboard

```
/goal

You are implementing Phase 08 of the NSE Quant Platform.

CONTEXT:
- Workspace root: d:\trading-app
- Phases 00-07 are complete. FastAPI backend is running.
- NEVER read or write plan/_work/

TASK:
1. Read plan/08_FRONTEND_CHARTING_AND_DASHBOARD.md completely.
2. Read plan/00A_CONTRACTS_AND_CONVENTIONS.md Section 4 (API endpoint shapes the frontend calls).
3. Implement exactly what the EXECUTION_CONTRACT "produces" section specifies:
   - static/index.html               (main SPA shell)
   - static/css/theme.css            (dark-mode design tokens, Simple/Pro mode classes)
   - static/js/app.js                (mode switcher, router, state manager)
   - static/js/chart.js              (TradingView Lightweight Charts; candlestick + volume; cursor pagination)
   - static/js/symbol_search.js      (debounced search dropdown)
   - static/js/auth_modal.js         (token expiry countdown; re-auth modal)
   - static/js/download_progress.js  (per-symbol download status dashboard)
4. Run the test command from the plan's definition_of_done section.
5. Append STATUS: DONE to plan/HANDOFF.md for Phase 08.

CRITICAL RULES:
- Use TradingView Lightweight Charts library (NOT a TradingView Pro clone).
- Simple mode: hide technical indicators, show only price + volume, plain-language labels.
- Pro mode: all indicators, raw data access, export buttons visible.
- Historical pan: use cursor pagination — lazy-load older candles on left scroll.
- Token expiry countdown in header: shows "Session expires in Xh Ym". Clicking opens re-auth modal.
```

SUCCESS CHECK: Open `http://localhost:8000` in browser — chart loads for RELIANCE in < 5 seconds, Simple/Pro toggle works.

---

## STAGE 3: MANDATORY SCALING GATE

### Conversation 10 — Phase 09: Milestone 1 Reliance Verification (HARD GATE)

> **WARNING**: Do NOT proceed to Phase 10, 12, 14, or 15 until all 5 gates below show PASSED.

```
/goal

You are implementing Phase 09 of the NSE Quant Platform — the MANDATORY SCALING GATE.

CONTEXT:
- Workspace root: d:\trading-app
- Phases 00-08 are complete. The app is running end-to-end for RELIANCE.
- NEVER read or write plan/_work/

TASK:
1. Read plan/09_MILESTONE_1_RELIANCE_VERIFICATION.md completely.
2. Implement the benchmark script:
   - scripts/run_m1_benchmark.py  (runs all 5 gates; writes results to artifacts/m1_benchmark_results.json)
3. Run the benchmark against NSE:RELIANCE-EQ and verify ALL 5 gates pass:
   GATE 1: 30-min rate-limit soak test — zero HTTP 429 errors AND rate <= 180 req/min.
   GATE 2: Timestamp alignment — first 1m candle = 03:45:00 UTC (09:15:00 IST).
   GATE 3: Split probe — cont_flag=0 vs cont_flag=1 price ratio matches known split within 0.1%.
   GATE 4: DuckDB 100M row benchmark — staging anti-join insert >= 25,000 rows/sec; range query <= 200ms.
   GATE 5: Disk size — measured bytes per candle <= 15 bytes.
4. Write gate results to artifacts/m1_benchmark_results.json.
5. Update plan/OPEN_QUESTIONS.md — mark OQ-01 through OQ-05 as VERIFIED or still UNVERIFIED.
6. Append STATUS: DONE (or BLOCKED with gate failures listed) to plan/HANDOFF.md for Phase 09.

CRITICAL RULES:
- If ANY gate fails, STOP. Do not proceed.
- Record the exact measured numbers in artifacts/m1_benchmark_results.json (not estimates).
```

SUCCESS CHECK: `cat artifacts/m1_benchmark_results.json` shows `"overall_status": "PASSED"` with all 5 gates `"pass": true`.

---

## STAGE 4: ADVANCED QUANT ENGINES

### Conversation 11 — Phase 10: Edge Cases & Maintenance

```
/goal

You are implementing Phase 10 of the NSE Quant Platform.
PREREQUISITE: Verify artifacts/m1_benchmark_results.json shows "overall_status": "PASSED" before writing any code.

CONTEXT:
- Workspace root: d:\trading-app
- NEVER read or write plan/_work/

TASK:
1. Read plan/10_EDGE_CASES_RISKS_AND_MAINTENANCE.md completely.
2. Implement exactly what the EXECUTION_CONTRACT "produces" section specifies:
   - services/maintenance_service.py  (corporate action anomaly audit; weekly Parquet snapshot; DB VACUUM + ANALYZE)
   - scripts/backup_restore_drill.py  (weekly backup to data/backups/; restore verification drill)
   - scripts/audit_anomalies.py       (flags symbols with > 25% single-day price move vs corporate_actions table)
3. Run all definition_of_done commands.
4. Append STATUS: DONE to plan/HANDOFF.md for Phase 10.
```

---

### Conversation 12 — Phase 11: Simple/Pro UX Mode Controller

```
/goal

You are implementing Phase 11 of the NSE Quant Platform.
PREREQUISITE: Phase 09 gate must be PASSED.

CONTEXT:
- Workspace root: d:\trading-app
- NEVER read or write plan/_work/

TASK:
1. Read plan/11_PERSONAS_AND_SIMPLE_PRO_UX.md completely.
2. Implement exactly what the EXECUTION_CONTRACT "produces" section specifies:
   - static/js/ux_mode_controller.js   (mode state machine; localStorage persistence; event bus)
   - static/js/translation_registry.js (plain-language label dictionary — Simple vs Pro)
   - static/js/onboarding_tour.js       (4-step guided first-scan tour for Beginner users)
3. Run all definition_of_done commands (time-to-first-chart < 5s gate; <= 2 clicks to scan gate).
4. Append STATUS: DONE to plan/HANDOFF.md for Phase 11.
```

---

### Conversation 13 — Phase 15: Corporate Actions Engine (MUST COME BEFORE 12 & 14)

```
/goal

You are implementing Phase 15 of the NSE Quant Platform.
PREREQUISITE: Phase 09 gate PASSED. Phase 15 MUST complete before Phase 12 (Screener) and Phase 14 (Backtesting).

CONTEXT:
- Workspace root: d:\trading-app
- NEVER read or write plan/_work/

TASK:
1. Read plan/15_CORPORATE_ACTIONS_AND_EXTERNAL_DATA.md completely.
2. Read plan/00A_CONTRACTS_AND_CONVENTIONS.md Section 3 (corporate_actions and adjustment_factors DDLs).
3. Implement exactly what the EXECUTION_CONTRACT "produces" section specifies:
   - services/corporate_actions_service.py  (ICorporateActionRepository; cumulative factor computation)
   - scripts/fetch_bhavcopy.py              (UDiFF NSE bhavcopy daily CSV; politeness: 1 req / 3s)
   - scripts/fetch_delivery_data.py         (NSE delivery % and FII/DII data)
4. Run all definition_of_done commands (split factor test; factor recomputation < 15ms gate).
5. Append STATUS: DONE to plan/HANDOFF.md for Phase 15.

CRITICAL RULES:
- Raw candles MUST NEVER be modified. Adjustment factors live in adjustment_factors table only.
- NSE scraping: 1 request per 3 seconds maximum. Respect retry-after headers.
```

---

### Conversation 14 — Phase 12: Screener Engine

```
/goal

You are implementing Phase 12 of the NSE Quant Platform.
PREREQUISITE: Phase 15 (Corporate Actions) must be DONE before starting this phase.

CONTEXT:
- Workspace root: d:\trading-app
- NEVER read or write plan/_work/

TASK:
1. Read plan/12_SCREENER_ENGINE.md completely.
2. Read plan/00A_CONTRACTS_AND_CONVENTIONS.md Section 1 (IScreenerService interface).
3. Implement exactly what the EXECUTION_CONTRACT "produces" section specifies:
   - services/screener_service.py    (IScreenerService; filter AST builder; DuckDB query compiler)
   - api/routers/screener.py         (POST /api/v1/screener/run; GET /api/v1/screener/templates)
   - data/screener_templates.json    (3 pre-built templates: volume spike, 52-week high, RSI oversold)
   - static/js/screener_ui.js        (filter builder UI; saved scans; one-click to chart)
4. Run all definition_of_done commands (< 2s Nifty 500 scan gate).
5. Append STATUS: DONE to plan/HANDOFF.md for Phase 12.

CRITICAL RULES:
- All screener price filters run on candles_1d_adjusted VIEW — never raw prices.
- If fundamental data unavailable (check OQ-06 result in OPEN_QUESTIONS.md), show "Fundamentals unavailable — import CSV" message in UI gracefully.
- "as of" date must be clearly shown on every scan result.
```

---

### Conversation 15 — Phase 13: Watchlists & Multi-Channel Alerts

```
/goal

You are implementing Phase 13 of the NSE Quant Platform.
PREREQUISITE: Phase 12 (Screener) must be DONE.

CONTEXT:
- Workspace root: d:\trading-app
- NEVER read or write plan/_work/

TASK:
1. Read plan/13_ALERTS_AND_WATCHLISTS.md completely.
2. Read plan/00A_CONTRACTS_AND_CONVENTIONS.md Section 7 (RateGovernor Lane 2 — alert quote budget).
3. Implement exactly what the EXECUTION_CONTRACT "produces" section specifies:
   - services/alert_service.py       (IAlertService; alert state machine; dedupe window 15 min)
   - services/notifiers/             (in_app.py, telegram_notifier.py, email_notifier.py)
   - api/routers/alerts.py           (CRUD for alerts and watchlists)
   - static/js/alerts_ui.js          (alert badge; quiet hours indicator)
4. Run all definition_of_done commands.
5. Append STATUS: DONE to plan/HANDOFF.md for Phase 13.

CRITICAL RULES:
- Alert quote checks share global RateGovernor (Lane 2: <= 2 req/min for 50-symbol batches).
- Quiet hours: 23:00-08:00 IST — no notifications fired (queued until 08:00).
- On token expiry: alerts suspend, show "Session expired — alerts paused" banner.
```

---

### Conversation 16 — Phase 14: Backtesting Engine & Indian Cost Model

```
/goal

You are implementing Phase 14 of the NSE Quant Platform.
PREREQUISITE: Phase 15 (Corporate Actions) must be DONE. Backtest runs on adjusted prices ONLY.

CONTEXT:
- Workspace root: d:\trading-app
- NEVER read or write plan/_work/

TASK:
1. Read plan/14_BACKTESTING_ENGINE.md completely.
2. Read plan/VERIFICATION_REPORT.md section on Indian statutory costs (verified rates and effective dates).
3. Implement exactly what the EXECUTION_CONTRACT "produces" section specifies:
   - services/backtest_service.py    (IBacktestEngine; event loop; anti-lookahead enforcement)
   - services/cost_model.py          (Indian statutory costs: STT, exchange charges, SEBI fee, GST, stamp duty)
   - services/monte_carlo.py         (1000 run Monte Carlo; reproducible seed + data-version SHA-256 hash)
   - api/routers/backtest.py         (POST /api/v1/backtest/run; GET /api/v1/backtest/results/{id})
   - static/js/backtest_ui.js        (no-code rule builder wizard; results dashboard with survivorship warning)
4. Run all definition_of_done commands (anti-lookahead fixture MUST fail; cost model precision gate).
5. Append STATUS: DONE to plan/HANDOFF.md for Phase 14.

CRITICAL RULES:
- Signal on bar t CLOSE; fill on bar t+1 OPEN. Non-negotiable.
- A deliberate lookahead test fixture MUST exist and MUST fail (proves the guard works).
- Every report and export MUST show a survivorship bias warning banner.
- Cost rates come from plan/VERIFICATION_REPORT.md ONLY — never invent rates.
```

---

### Conversation 17 — Phase 16: Options Chain Module

```
/goal

You are implementing Phase 16 of the NSE Quant Platform.
PREREQUISITE: Phase 06 (Scheduler) must be DONE.

CONTEXT:
- Workspace root: d:\trading-app
- NEVER read or write plan/_work/

TASK:
1. Read plan/16_OPTIONS_MODULE.md completely.
2. Read plan/00A_CONTRACTS_AND_CONVENTIONS.md Section 7 (RateGovernor options snapshot budget).
3. Implement exactly what the EXECUTION_CONTRACT "produces" section specifies:
   - services/options_service.py     (daily 15:35 IST option chain snapshot; Black-Scholes Greeks)
   - api/routers/options.py          (GET /api/v1/options/chain; /greeks; /payoff; /maxpain)
   - static/js/options_ui.js         (chain table; multi-leg payoff builder; Max Pain chart)
4. Run all definition_of_done commands.
5. Append STATUS: DONE to plan/HANDOFF.md for Phase 16.

CRITICAL RULES:
- "No history before collection start date" banner MUST appear permanently on the options module.
- Black-Scholes risk-free rate: use RBI 91-day T-bill rate. Default 6.5% per VERIFICATION_REPORT — configurable via RBI_RISK_FREE_RATE env key.
- Missed day gap: show "Data unavailable for [date]" clearly — do not interpolate.
```

---

### Conversation 18 — Phase 17: Trade Journal & Paper Trading

```
/goal

You are implementing Phase 17 of the NSE Quant Platform.
PREREQUISITE: Phase 14 (Backtesting Engine) must be DONE.

CONTEXT:
- Workspace root: d:\trading-app
- NEVER read or write plan/_work/

TASK:
1. Read plan/17_JOURNAL_AND_PAPER_TRADING.md completely.
2. Implement exactly what the EXECUTION_CONTRACT "produces" section specifies:
   - services/journal_service.py     (IJournalService; R-multiple calculation; equity curve builder)
   - services/paper_trading.py       (simulated fills using Phase 14 cost model + 5 bps slippage)
   - api/routers/journal.py          (CRUD for journal entries; CSV import; export)
   - static/js/journal_ui.js         (equity curve chart; R-multiple histogram; mistake tag cloud)
3. Run all definition_of_done commands.
4. Append STATUS: DONE to plan/HANDOFF.md for Phase 17.

CRITICAL RULES:
- R-multiple: R = (Exit - Entry) / (Entry - Stop Loss). Store raw inputs separately.
- Paper trading fills reuse services/cost_model.py from Phase 14 — do not duplicate cost logic.
- "Cost of Mistakes" summary: group tagged trades by mistake type, show total P&L impact.
```

---

### Conversation 19 — Phase 18: Beginner Learning Layer

```
/goal

You are implementing Phase 18 of the NSE Quant Platform.
PREREQUISITE: Phase 11 (Simple/Pro UX) must be DONE.

CONTEXT:
- Workspace root: d:\trading-app
- NEVER read or write plan/_work/

TASK:
1. Read plan/18_BEGINNER_LEARNING_LAYER.md completely.
2. Implement exactly what the EXECUTION_CONTRACT "produces" section specifies:
   - data/glossary.json              (each entry: {term, simple_definition, everyday_analogy, risk_caution})
   - static/js/glossary.js           (contextual tooltip engine — shows on hover/tap of highlighted terms)
   - static/js/guided_tutorial.js    (4-step first-scan onboarding tour — shown once to new users)
3. Run all definition_of_done commands.
4. Append STATUS: DONE to plan/HANDOFF.md for Phase 18.

CRITICAL RULES:
- Every glossary entry must have all 3 fields: simple_definition, everyday_analogy, risk_caution.
- Tour is skippable at any step. Progress stored in localStorage.
- Tooltips appear in Simple mode ONLY — hidden in Pro mode.
- No glossary entry should give investment advice — factual descriptions only.
```

---

## CROSS-CUTTING PHASE

### Conversation 20 — Phase 19: Compliance, Security & Safety Audit (FINAL)

```
/goal

You are implementing Phase 19 of the NSE Quant Platform — the final compliance and security audit.
PREREQUISITE: All phases 00-18 must be DONE.

CONTEXT:
- Workspace root: d:\trading-app
- NEVER read or write plan/_work/

TASK:
1. Read plan/19_COMPLIANCE_AND_SAFETY.md completely.
2. Implement exactly what the EXECUTION_CONTRACT "produces" section specifies:
   - core/security.py           (export metadata verifier; order execution hard gate: always returns 403)
   - core/logging_config.py     (RedactingFormatter — redacts API tokens, secrets, 4-digit PINs)
   - scripts/audit_security.py  (scans entire repo for plaintext secrets)
   - config/legal_notices.json  (SEBI "Not Investment Advice" disclaimer text)
3. Run ALL definition_of_done commands.
4. Fix any secrets found in the audit scan before marking DONE.
5. Append STATUS: DONE to plan/HANDOFF.md for Phase 19.

CRITICAL RULES:
- ORDER EXECUTION ENDPOINT MUST NOT EXIST. Any order-routing request returns HTTP 403 "Order execution is out of scope."
- SEBI disclaimer must appear on: home screen, every backtest report, every screener result, every export file.
- RedactingFormatter must cover: Fyers API key, app secret, 4-digit PIN.
- All exports must include Fyers personal non-commercial license in metadata.
```

FINAL SUCCESS CHECK: `python scripts/audit_security.py` returns zero findings. `pytest tests/ -v` — full suite passes.

---

## QUICK REFERENCE: STATUS TRACKING

After each conversation, verify in `plan/HANDOFF.md`:

| Conversation | Phase | Key Artifact | Success Check |
|---|---|---|---|
| 1 | 00A + 00 | core/interfaces.py | 15 interfaces importable |
| 2 | 01 | services/vault.py | No secrets in plain .env |
| 3 | 02 | db/migrations.py | 9 tables + 2 views created |
| 4 | 03 | services/symbol_service.py | Tier counts: 100+150+250=500 |
| 5 | 04 | core/rate_governor.py | Dry-run prints budget math |
| 6 | 05 | services/resampling_service.py | All 11 timeframe fixtures pass |
| 7 | 06 | services/scheduler_service.py | Cron fires only on weekdays |
| 8 | 07 | main.py | /health returns {"status":"ok"} |
| 9 | 08 | static/js/chart.js | Chart loads < 5 seconds |
| **10** | **09** | **artifacts/m1_benchmark_results.json** | **"overall_status": "PASSED" — 5/5 gates** |
| 11 | 10 | scripts/backup_restore_drill.py | Backup + restore completes |
| 12 | 11 | static/js/ux_mode_controller.js | Mode toggle works |
| **13** | **15** | **services/corporate_actions_service.py** | **Factor recomputation < 15ms** |
| 14 | 12 | services/screener_service.py | Nifty 500 scan < 2 seconds |
| 15 | 13 | services/alert_service.py | Alert fires; quiet hours respected |
| 16 | 14 | services/backtest_service.py | Lookahead fixture FAILS as expected |
| 17 | 16 | services/options_service.py | Options chain snapshot collected |
| 18 | 17 | services/journal_service.py | R-multiple math correct |
| 19 | 18 | data/glossary.json | All 3 fields per entry |
| 20 | 19 | scripts/audit_security.py | Zero secrets found |

---

*Keep this file open as a reference tab while running each coding session.*
*All authoritative specs are in the `plan/` folder — this file is just the user's execution guide.*
