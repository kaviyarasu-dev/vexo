# Technical Design Specification: Platform Automation & Engineering Backlog

**Document ID:** `2026-10-17-platform-automation-and-backlog-design`  
**Feature Slug:** `platform-automation-and-backlog`  
**Author:** Principal Financial AI Engineer & Senior Quantitative Researcher  
**Target Architecture:** APScheduler, DuckDB, FastAPI, Telegram Bot API, SMTP Notifier  
**Status:** Spec Approved / Ready for Plan Split  

---

## 1. Overview & Objective
This specification addresses all pending operational and automation backlog items documented in Section 7 of `AI_ROADMAP_AND_PENDING_AUDIT.md`:
1. Hardening the daily APScheduler incremental sync cron (`'45 15 * * 1-5' Asia/Kolkata`).
2. Integrating daily UDiFF Bhavcopy and Delivery % / FII-DII data into the Stock Screener.
3. Adding multi-channel alert settings UI (Telegram & Email) with encrypted credential storage.
4. Automating weekly DuckDB backups, restore drills, and price anomaly audits.
5. Tuning Gate 4 and executing the Phase 09 5-Gate Reliance Benchmark to 100% pass status.

---

## 2. Partitioned Plan Structure

```
+---------------------------------------------------------------------------------------------------+
| Plan 001: Daily APScheduler Hardening & Sync Cron                                                 |
| Target: services/scheduler_service.py, services/incremental_sync_service.py                       |
| Verify: pytest tests/unit/test_scheduler_timing.py tests/integration/test_missed_run_catchup.py    |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| Plan 002: External Data Bhavcopy & Screener Delivery Columns                                      |
| Target: scripts/fetch_bhavcopy_udiff.py, services/screener_service.py, static/js/screener_ui.js    |
| Verify: pytest tests/unit/test_screener_filters.py                                                |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| Plan 003: Multi-Channel Alert Notification Settings & Dispatchers                                 |
| Target: services/notifiers/, api/routers/alerts.py, static/js/alerts_ui.js, static/index.html     |
| Verify: pytest tests/integration/test_alert_dispatcher.py                                         |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| Plan 004: Weekly Anomaly Auditor & Automated Backup/Restore Drill                                 |
| Target: scripts/audit_anomalies.py, scripts/backup_restore_drill.py, services/scheduler_service.py  |
| Verify: pytest tests/integration/test_backup_restore_drill.py                                     |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| Plan 005: Phase 09 Hard Gate Benchmark Tuning & Final Report                                      |
| Target: scripts/run_m1_benchmark.py, db/migrations.py                                             |
| Verify: python scripts/run_m1_benchmark.py                                                         |
+---------------------------------------------------------------------------------------------------+
```
