# Quant Platform Architectural Changelog

**Baseline Release**: Version 1.0.0 (Comprehensive Phased Architectural Upgrade)  
**Date**: 2026-10-05  
**Architect**: Senior Quant-Platform Architect  
**Scope**: Complete upgrade of existing plans (00 to 10) and authoring of new plans (00A, 11 to 19, 99, IMPLEMENTATION_ORDER, HANDOFF).

---

## 1. Summary of Major Architectural Upgrades

### 1.1. Empirical Fact Verification & Removal of Broken Assumptions
- **Rate Limit Redesign**:
  - *Previous Defect*: Plan 04 assumed a continuous download rate of 8 req/sec (480 req/min) and 10,000 req/day.
  - *Verified Fact*: Fyers API v3 strictly enforces 200 req/min (breaching >3 times/day triggers automated account block) and 100,000 req/day.
  - *Upgrade*: Replaced with a centralized `RateGovernor` maintaining a sustained target of 180 req/min (3.0 req/sec) with a 10 req/sec burst bucket and 90,000 req/day soft cap across 3 prioritized lanes.
- **End-of-History Condition**:
  - *Previous Defect*: Plan 04 stopped download on a single empty response or error. Fyers error `-300` occurs transiently on valid symbols, causing premature data truncation.
  - *Upgrade*: Downloader terminates a symbol's historical walk ONLY when BOTH $\ge 3$ consecutive empty chunks occur AND `chunk_start < listing_date`.
- **DuckDB Concurrency & Reader Decoupling**:
  - *Previous Defect*: Plan 00 and 02 required read queries to acquire a mutex lock alongside writes, stalling frontend chart loading during ingestion.
  - *Upgrade*: Writers use a dedicated write connection and asynchronous queue; API readers acquire lightweight non-blocking cursors (`conn.cursor()`) without acquiring the writer lock.
- **DuckDB 100M+ Row Index Scaling**:
  - *Previous Defect*: Placing a `PRIMARY KEY` on a 100M+ row table builds a heavy memory-resident ART index in DuckDB, degrading batch insertion throughput.
  - *Upgrade*: Designed a temporary staging table with anti-join deduplication (`WHERE NOT EXISTS`), maintaining Zone-Map sorted columnar data with Phase 09 benchmark verification.
- **NSE Session Alignment & UTC Offset Math**:
  - *Previous Defect*: Standard time-bucketing divided timestamps from UTC midnight (`00:00:00`), creating invalid 15m, 30m, and 1h bars in the Indian market.
  - *Upgrade*: Documented exact UTC offset ($09:15\text{ IST} - 05:30 = 03:45\text{ UTC}$) and configured DuckDB's `time_bucket(INTERVAL, timestamp, TIMESTAMP '2000-01-01 03:45:00')`.
- **Tier Arithmetic Inconsistency Fixed**:
  - *Previous Defect*: Plan 03 defined Tier 1 (100) + Tier 2 (Midcap 150 + Smallcap 250 = 400), and erroneously claimed "Tier 3 = remaining Nifty 500 constituents (~500 stocks)" ($100 + 400 + 500 = 1000$!).
  - *Upgrade*: Corrected to match official NSE index arithmetic: Tier 1 (100) + Tier 2 (Midcap 150) + Tier 3 (Smallcap 250) = Exactly Nifty 500 (500 stocks). Tier 4 covers remaining non-Nifty-500 equities.
- **Cron Expression Syntax**:
  - *Previous Defect*: Plan 06 contained invalid 6-field reversed cron `0 15 45 * * mon-fri`.
  - *Upgrade*: Standardized to valid 5-field cron `45 15 * * 1-5` (`Asia/Kolkata`).
- **Excel Row Ceiling Guard**:
  - *Previous Defect*: Plan 07 stated Excel limit as 1,048,576 without factoring in the header row.
  - *Upgrade*: Fixed ceiling to exactly 1,048,575 data rows (+ 1 header row = 1,048,576 total rows), returning HTTP 400 `EXCEL_ROW_LIMIT_EXCEEDED` on breach.

---

## 2. Granular Log of File Patches & Creational Additions

### `plan/00A_CONTRACTS_AND_CONVENTIONS.md` (NEW)
- Created the master single source of truth locking all conceptual interface signatures, 11 canonical timeframes, DDL schemas, API contracts, configuration keys, RateGovernor specs, concurrency rules, universe arithmetic, and NFR checklists.

### `plan/00_MASTER_ARCHITECTURE.md` (UPGRADED)
- Added mandatory EXECUTION CONTRACT block.
- Updated 20-phase roadmap and expanded directory layout to include screener, alerts, backtest, options, journal, and compliance.
- Fixed concurrency section 4.2: read cursors operate independently from writer queue.
- Replaced retired interface variants with 00A canonical names.

### `plan/01_ENVIRONMENT_CONFIG_AND_AUTH.md` (UPGRADED)
- Added mandatory EXECUTION CONTRACT block.
- Formulated full dual-token lifecycle: daily access token (valid until 06:00 AM IST) and 15-day static refresh token.
- Secure credential management: PIN and tokens stored in OS Keyring or encrypted vault (`data/.vault.enc`), never in plain `.env`.
- Added automated pre-flight session check at 15:40 IST and 15-day re-login reminders.

### `plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md` (UPGRADED)
- Added mandatory EXECUTION CONTRACT block.
- Added `schema_version`, separated raw storage (`candles_1m_raw`, `candles_1d_raw`) from dynamic views (`candles_1m_adjusted`, `candles_1d_adjusted`), added `corporate_actions` and `adjustment_factors`.
- Updated `download_checkpoints` to use `earliest_ts` and `latest_ts` (`TIMESTAMP`).
- Formulated staging table anti-join deduplication architecture for 100M+ rows.
- Rewrote concurrency architecture decoupling read cursors from single write connection.

### `plan/03_SYMBOL_MASTER_AND_UNIVERSE_MANAGER.md` (UPGRADED)
- Added mandatory EXECUTION CONTRACT block.
- Fixed tier arithmetic: Tier 1 (100) + Tier 2 (150) + Tier 3 (250) = 500 (Nifty 500).
- Specified automated script fetching from official NSE constituent CSVs, with local fallback JSON files; zero hand-typed constituent data.
- Configured Fyers `NSE_CM.csv` column format (no header, 0-indexed columns).

### `plan/04_HISTORICAL_DOWNLOADER_ENGINE.md` (UPGRADED)
- Added mandatory EXECUTION CONTRACT block.
- Redesigned rate limiting around the shared Global RateGovernor (180 req/min target, 10 req/s burst, 90,000 req/day cap across 3 priority lanes).
- Recomputed all request math with arithmetic shown: Nifty 500 1m backfill = 9,500 reqs (~53 min); All active stocks 1D backfill = 30,000 reqs (~2.8 hrs); Total Day 1 initial backfill = 39,500 reqs. Daily sync = 2,500 reqs (~14 min).
- Replaced naive stop rule with robust condition ($\ge 3$ consecutive empty chunks AND `chunk_start < listing_date`).
- Mapped upstream error taxonomy (`-300`, `429`, `-353`, `-339`, `-16`, `401`, `5xx`).

### `plan/05_RESAMPLING_AND_QUANT_METRICS_ENGINE.md` (UPGRADED)
- Added mandatory EXECUTION CONTRACT block.
- Formalized IST session alignment ($09:15\text{ IST} - 05:30 = 03:45\text{ UTC}$) with DuckDB `origin` parameter (`TIMESTAMP '2000-01-01 03:45:00'`).
- Detailed session stub bar counts for 30m (13 bars), 1h (7 bars), 2h (4 bars), 4h (2 bars).
- Query source defaults to `candles_1m_adjusted` dynamic view.
- Added explicit zero-volume bar policy (`is_zero_volume = TRUE`, volume = 0, previous close).
- Golden fixture test plan covering all 11 canonical timeframes.

### `plan/06_DAILY_INCREMENTAL_UPDATE_AND_SCHEDULER.md` (UPGRADED)
- Added mandatory EXECUTION CONTRACT block.
- Recomputed daily sync timing: 2,500 requests at 180 req/min completes in $\approx 13.9$ minutes.
- Fixed cron expression to valid 5-field syntax: `45 15 * * 1-5` (`Asia/Kolkata`).
- Added missed-run catchup logic on application startup when market is closed.
- Sourced market holidays from Phase 03 automated script / DuckDB table.
- Added 15:40 IST pre-flight probe and `FAILED_AUTH` graceful standby state machine.

### `plan/07_FASTAPI_BACKEND_AND_QUANT_APIS.md` (UPGRADED)
- Added mandatory EXECUTION CONTRACT block.
- Added `limit` and `cursor` pagination parameters to `/api/v1/candles`.
- Enforced standard 00A response envelope and error envelope with correlation IDs.
- Corrected Parquet export flow: DuckDB `COPY TO PARQUET` writes to scratch file `data/exports/tmp_{uuid}.parquet`, streamed via FastAPI `FileResponse` with background task cleanup.
- Stated exact Excel data ceiling of 1,048,575 data rows.
- Embedded export metadata (source, survivorship bias disclosure, adjustment status, personal license).

### `plan/08_FRONTEND_CHARTING_AND_DASHBOARD.md` (UPGRADED)
- Added mandatory EXECUTION CONTRACT block.
- Integrated Simple Mode vs Pro Mode UI toggle (referencing Phase 11).
- Added glossary tooltips and beginner empty states (referencing Phase 18).
- Implemented Token Lifecycle & Re-Auth UI in top navbar with live countdown timer and quick-refresh modal.
- Connected historical pan lazy-loading to backend `limit` and `cursor` parameters.

### `plan/09_MILESTONE_1_RELIANCE_VERIFICATION.md` (UPGRADED)
- Added mandatory EXECUTION CONTRACT block.
- Established the Five Quantitative Scaling Readiness Gates:
  1. Rate-Limit 30-minute soak gate (zero 429s, $\le 180$ req/min).
  2. Timestamp convention gate (UTC 03:45 market open, pure DATE for 1D).
  3. Corporate action adjustment correctness probe (settling OQ-01).
  4. DuckDB PK vs Staging anti-join scaling benchmark at 100M rows (settling OQ-03).
  5. Empirical disk size and query latency gate (measured bytes/candle $\le 15$ bytes, 5m query $\le 25$ ms).

### `plan/10_EDGE_CASES_RISKS_AND_MAINTENANCE.md` (UPGRADED)
- Added mandatory EXECUTION CONTRACT block.
- Formulated Corporate-Action Integrity Audit detecting single-bar price moves $> 25\%$ and cross-referencing against the official `corporate_actions` table.
- Added automated weekly Parquet snapshot export and restore verification drill (`scripts/run_backup_drill.py`) using an isolated scratch database.
- Formalized reversible schema migrations with rollback procedures (`scripts/rollback_migration.py`).
- Detailed storage compaction (post-sync `CHECKPOINT;`, weekly `VACUUM;`).

### `plan/11_PERSONAS_AND_SIMPLE_PRO_UX.md` (NEW)
- Detailed Persona A (Beginner) and Persona B (Quant Trader) user journeys and jobs.
- Designed Simple Mode vs Pro Mode UI with component visibility matrix and plain-language translation dictionary (`config/ux_translations.json`).
- Set measurable UX target gates: Time-to-first-chart $< 5$s, Clicks-to-first-scan $\le 2$ clicks, mode switching $< 50$ms.

### `plan/12_SCREENER_ENGINE.md` (NEW)
- Multi-factor technical and volume screener engine.
- Settled OQ-06: defined local CSV import fallback for fundamental data (`data/fundamentals_latest.csv`) with graceful UI degradation when absent.
- Included 3 canonical pre-built templates: "Volume Surge Alert", "52-Week High Breakout", "RSI Oversold Bounce".
- Engineered vectorized DuckDB SQL window query delivering full Nifty 500 scan in $< 2.0$ seconds.

### `plan/13_ALERTS_AND_WATCHLISTS.md` (NEW)
- Detailed rule typology: price thresholds, Session VWAP crosses, RSI extremes, volume surges, screener matches.
- Multi-channel delivery: in-app toast, Telegram bot webhook, SMTP email.
- Defined production operational safeguards: alert state machine, 15-minute cooldown deduplication, quiet hours (23:00 to 08:00 IST), and token expiry pause.
- Formulated RateGovernor integration: 50-symbol quote batching via Lane 2 consuming $\le 2$ req/min.

### `plan/14_BACKTESTING_ENGINE.md` (NEW)
- Integrated verified statutory Indian equity cost model: Fyers Brokerage (Oct 2024), STT (Delivery: 0.1% both sides, Intraday: 0.025% sell side), Exchange charges (0.00297%), SEBI fees (₹10/crore), GST (18%), Stamp Duty (0.015% delivery buy, 0.003% intraday buy), and configurable slippage.
- Enforced strict anti-lookahead architecture: signal on bar $t$ Close, execution on bar $t+1$ Open, with a dedicated adversarial lookahead test fixture that must trigger a test failure.
- Included full quant metrics suite (CAGR, Sharpe, Sortino, Max Drawdown, Expectancy), Monte Carlo resampling (1,000 iterations), and walk-forward analysis.
- Embedded reproducibility standards: data-version SHA-256 hash, seed, and mandatory survivorship bias warning.

### `plan/15_CORPORATE_ACTIONS_AND_EXTERNAL_DATA.md` (NEW)
- Detailed corporate-action adjustment engine: cumulative price and volume multipliers stored in `adjustment_factors` and applied dynamically via SQL views (`candles_1d_adjusted`, `candles_1m_adjusted`).
- Solved the recomputation problem: new corporate actions recompute factors in $< 15$ ms without re-downloading raw candles.
- Formulated external NSE data ingestion: UDiFF Common Bhavcopy, delivery quantity and percentage, FII/DII net flows, bulk/block deals.
- Detailed scraping governance, cookie bootstrap, politeness rate limit ($\le 1$ req / 3s), and local fallback imports.

### `plan/16_OPTIONS_MODULE.md` (NEW)
- Designed daily 15:35 IST forward snapshot collection into `option_chain_snapshots` with mandatory UI banner and missed-day gap integrity rules.
- Implemented quantitative options metrics: Open Interest distribution, PCR by Volume and OI, and exact Max Pain strike optimization formula.
- Engineered analytical Black-Scholes Greeks engine (Delta, Gamma, Theta, Vega) using verified RBI risk-free rate (6.5%).
- Formulated interactive multi-leg payoff diagram builder (Spreads, Straddles, Condors).

### `plan/17_JOURNAL_AND_PAPER_TRADING.md` (NEW)
- Detailed trade journal architecture: manual entry, external CSV tradebook import (Fyers, Zerodha), and FIFO execution matching.
- Derived exact $R$-multiple mathematical formulation ($R = \frac{\text{Gain}}{R_{\text{risk}}}$).
- Formulated behavioral mistake tagging (FOMO, Revenge Trading, Oversized Position) with "Cost of Mistakes" analytics.
- Engineered paper-trading execution simulator reusing Phase 14's statutory Indian cost model and 5 bps slippage.

### `plan/18_BEGINNER_LEARNING_LAYER.md` (NEW)
- Standardized educational three-part schema: Plain Definition, Everyday Analogy, Risk Warning ("How this can lose you money").
- Compiled comprehensive glossary registry (`config/glossary.json`) covering all platform metrics and statutory concepts.
- Designed contextual popover tooltip system triggered by `data-glossary` DOM attributes.
- Built interactive 4-step guided first-scan onboarding tour.

### `plan/19_COMPLIANCE_AND_SAFETY.md` (NEW)
- Formulated statutory SEBI "Not Investment Advice" disclaimers complying with SEBI (Research Analysts) Regulations 2014, with standardized placement across UI footers, backtests, and export headers.
- Analyzed SEBI's Retail Algorithmic Trading Framework (Static IP, Algo ID, 10 OPS limit, 2FA) and established an architectural hard gate preventing order execution.
- Detailed cryptographic secret isolation (OS Keyring, AES-256 vault, automated log redaction).
- Formulated Fyers EULA data licensing compliance (personal non-commercial use only; prohibition of commercial data redistribution).

### `plan/99_FEATURE_TRACEABILITY.md` (NEW)
- Master matrix mapping every user job to phase, priority, and Definition of Done test command.
- Explicit registry of cut items (order execution, multi-tenancy, custom charting canvas, etc.) with technical justifications.

### `plan/IMPLEMENTATION_ORDER.md` (NEW)
- Linear execution order, global dependency graph, scaling gates, and parallel tracks.
- Instructs implementing agents to ignore `/plan/_work/`.

### `plan/HANDOFF.md` (NEW)
- Master tracking ledger skeleton for implementing coding agents.
