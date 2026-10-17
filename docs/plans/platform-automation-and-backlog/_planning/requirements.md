# Requirements & Architecture Specification: Platform Automation & Pending Engineering Backlog

**Feature Slug:** `platform-automation-and-backlog`  
**Target Platform:** NSE Quant Platform (`d:\trading-app`)  
**Status:** Spec Approved  

---

## Code findings

1. **APScheduler Daily Sync (`services/scheduler_service.py`):**
   - Configured with `Asia/Kolkata` timezone.
   - Pre-flight auth probe runs at 15:40 IST; daily incremental sync at 15:45 IST; option chain snapshot at 15:35 IST.
   - Requires verification that single-writer DuckDB process handles scheduled sync without locking out UI read queries.

2. **External Data & Screener Enrichment (`scripts/fetch_bhavcopy_udiff.py`, `fetch_delivery_data.py`):**
   - Scripts exist for downloading daily UDiFF Bhavcopy and delivery % / FII-DII flows.
   - Currently not wired into the daily post-market scheduler cron (16:00 IST).
   - Screener table in `static/js/screener_ui.js` lacks Delivery % and Institutional net flow columns.

3. **Multi-Channel Alert Dispatchers (`services/notifiers/`):**
   - `telegram_notifier.py` and `email_notifier.py` exist in `services/notifiers/`.
   - UI lacks an Alert Notification Settings modal to configure Telegram Bot Token / Chat ID and SMTP credentials.

4. **Maintenance Automation (`scripts/audit_anomalies.py`, `backup_restore_drill.py`):**
   - Anomaly auditor flags price jumps $> 25\%$ unrecorded in corporate actions.
   - Backup/restore drill script verifies DuckDB `.duckdb` snapshot integrity in `data/backups/`.
   - Requires automated weekly trigger registration in `services/scheduler_service.py`.

5. **Milestone 1 Reliance Benchmark (`scripts/run_m1_benchmark.py`):**
   - Benchmark script tests 5 scaling gates:
     - Gate 1: Rate limit soak (180 req/min, 0 429s) -> PASS.
     - Gate 2: Timestamp convention (03:45 UTC = 09:15 IST) -> PASS.
     - Gate 3: Split adjustment correctness (2.0 ratio) -> PASS.
     - Gate 4: DuckDB PK vs Staging scaling (1.18M rows/sec, query latency tuning to <= 200ms).
     - Gate 5: Disk size (12.2 bytes/candle <= 15 bytes) -> PASS.

---

## Decisions

- **D1:** Group all Section 7 backlog tasks into a dedicated 5-part plan suite under `docs/plans/platform-automation-and-backlog/`.
- **D2:** Sizing is **L (Large)** (~60 turns).
- **D3:** Gate 4 query tuning: optimize index on `candles_1m_raw(symbol, timestamp)` to ensure query latency stays consistently below 200ms across 10M rows.
- **D4:** All notification credentials (Telegram token, SMTP password) must be stored encrypted using OS Keyring or AES-256 vault, never in plaintext.

---

## Assumptions

- **A1:** Telegram Bot API and SMTP endpoints are reachable during live notification dispatch.
- **A2:** NSE UDiFF Bhavcopy daily releases occur by 16:30 IST on trading days.
