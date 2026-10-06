# Task Brief: Patch 06_DAILY_INCREMENTAL_UPDATE_AND_SCHEDULER.md

**Target File**: `plan/06_DAILY_INCREMENTAL_UPDATE_AND_SCHEDULER.md` (ONLY this file may be modified)  
**Allowed Read Set**:
- `plan/00A_CONTRACTS_AND_CONVENTIONS.md`
- `plan/06_DAILY_INCREMENTAL_UPDATE_AND_SCHEDULER.md`
- `plan/VERIFICATION_REPORT.md`

**Objective**:
Upgrade `06_DAILY_INCREMENTAL_UPDATE_AND_SCHEDULER.md` to enterprise quant architecture standards:
1. Add mandatory EXECUTION CONTRACT block at top.
2. Recompute daily sync timing under RateGovernor:
   - 2,500 total requests (500 1m + 2,000 1D).
   - At 180 req/min, sync finishes in exactly $\approx 13.9$ minutes.
3. Fix invalid cron syntax: standard 5-field `45 15 * * 1-5` (`Asia/Kolkata`).
4. Add missed-run catch-up logic: on application startup, evaluate if previous trading session's EOD sync was missed; execute catch-up if market is closed.
5. Ingest holidays via Phase 03 automated script / `market_holidays` table.
6. Formalize token-expired alert state: pre-flight probe at 15:40 IST; set `job_logs.status = 'FAILED_AUTH'` on refresh failure and notify user without crashing.
7. Use `latest_ts` (`TIMESTAMP`) from `download_checkpoints` and idempotently re-fetch the current day to ensure finalized closing settlement.
8. Keep file under 400 lines.

**Acceptance Self-Test**:
- Begins with EXECUTION CONTRACT.
- Valid 5-field cron expression specified (`45 15 * * 1-5`).
- Sync duration mathematically derived ($2,500 / 180 \approx 13.9$ min).
- Missed-run catch-up and token-expired state machines fully described.
