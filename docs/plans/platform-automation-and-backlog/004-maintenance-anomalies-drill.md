# Plan 004: Weekly Anomaly Auditor & Automated Backup/Restore Drill

## Goal
Schedule weekly DuckDB integrity backups, automated restore drills with checksum verification, and corporate action price anomaly audits:
1. Verify DuckDB single-process backup and restore logic in `scripts/run_backup_drill.py`.
2. Verify corporate action price and volume anomaly detection in `scripts/audit_anomalies.py`.
3. Register Sunday 02:00 IST weekly maintenance jobs in `services/scheduler_service.py`.
4. Execute automated backup/restore drill test suite.

## Read first
- `trading-app/scripts/audit_anomalies.py`
- `trading-app/scripts/run_backup_drill.py`
- `trading-app/services/integrity_auditor.py`
- `trading-app/services/scheduler_service.py`

## Steps

### Step 1: Verify DuckDB backup and restore drill execution
- Inspect `scripts/run_backup_drill.py`.
- Verify `run_drill()` creates a point-in-time database snapshot using DuckDB `EXPORT DATABASE` or direct file copy.
- Verify restore verification by attaching the snapshot in scratch mode, comparing row count hashes, and cleaning up temporary files.

### Step 2: Verify corporate action price anomaly detection
- Inspect `services/integrity_auditor.py` and `scripts/audit_anomalies.py`.
- Ensure `run_audit()` checks for:
  - Unadjusted single-day price jumps exceeding 40% without an associated corporate action.
  - Zero-volume trading days during active market sessions.
  - Negative High-Low spread corruptions (`high < low`).
- Output results to `job_logs` table in DuckDB.

### Step 3: Register weekly maintenance jobs in scheduler
- In `services/scheduler_service.py`, add weekly cron job:
  - Sunday 02:00 IST: `run_weekly_maintenance()` triggering both backup drill and anomaly scan.
- Ensure the job executes without acquiring blocking locks on active readers.

### Step 4: Run automated backup/restore drill test suite
- Execute integration tests validating snapshot creation, schema verification, and scratch database cleanup.
- Ensure all tests pass cleanly.

## Do not touch
- `trading-app/data/db/nse_quant.duckdb`
- `trading-app/db/connection.py`

## Acceptance
Run:
```bash
.\.venv\Scripts\pytest.exe tests/integration/test_backup_restore_drill.py tests/unit/test_integrity_auditor.py
```
All tests must pass with exit code 0.

## If blocked
Write exact error trace and attempted fixes to `docs/plans/platform-automation-and-backlog/BLOCKED.md` and stop.

## Report back
Provide test execution output confirming automated backup restore drill and anomaly scan.
