# Plan 001: Daily APScheduler Hardening & Sync Cron

## Goal
Harden and verify the automated daily scheduler for incremental market data sync:
1. Verify APScheduler cron configuration for Asia/Kolkata timezone.
2. Verify pre-flight authentication probe at 15:40 IST before sync execution.
3. Verify incremental sync job execution at 15:45 IST respecting RateGovernor Lane 3 budget.
4. Verify missed-run catchup logic executed on application startup.

## Read first
- `trading-app/services/scheduler_service.py`
- `trading-app/services/incremental_sync_service.py`
- `trading-app/services/trading_calendar.py`

## Steps

### Step 1: Verify scheduler cron configuration and timezone alignment
- Inspect `services/scheduler_service.py`.
- Ensure jobs use 5-field cron with `timezone=pytz.timezone('Asia/Kolkata')`:
  - 15:40 IST: `pre_flight_probe`
  - 15:45 IST: `daily_sync`
  - 15:35 IST: `option_snapshot`
- Ensure no UTC cron expressions are used.

### Step 2: Validate pre-flight authentication probe
- In `services/scheduler_service.py`, verify `pre_flight_auth_probe()` checks token validity.
- If token has expired or is invalid, set scheduler state to `FAILED_AUTH` standby and log an alert.
- If token is valid, verify it transitions to `READY_FOR_SYNC`.

### Step 3: Verify missed-run catchup logic
- In `services/scheduler_service.py`, verify `check_missed_runs()`.
- Compare last completed sync date in `download_checkpoints` against dynamic trading calendar from `services/trading_calendar.py`.
- If missed market days $> 0$, trigger incremental catchup in the background without blocking server startup.

### Step 4: Run automated scheduler test suite
- Execute unit and integration tests covering timing, timezone alignment, and missed-run catchup.
- Ensure all tests pass cleanly.

## Do not touch
- `trading-app/core/security.py`
- `trading-app/api/routers/auth.py`

## Acceptance
Run:
```bash
.\.venv\Scripts\pytest.exe tests/unit/test_scheduler_timing.py tests/integration/test_missed_run_catchup.py
```
All tests must pass with exit code 0.

## If blocked
Write exact error trace and attempted fixes to `docs/plans/platform-automation-and-backlog/BLOCKED.md` and stop.

## Report back
Provide test execution output confirming accurate IST cron scheduling and missed-run catchup.
