# Report: Patch 06_DAILY_INCREMENTAL_UPDATE_AND_SCHEDULER.md

**Status**: Done  
**File Written**: `plan/06_DAILY_INCREMENTAL_UPDATE_AND_SCHEDULER.md`  
**Open Questions Count**: 0  

### Summary of Changes
- Added full EXECUTION CONTRACT with exact dependencies, test plan, Definition of Done, and failure recovery.
- Recomputed sync duration under RateGovernor Lane 2: 2,500 total daily requests (500 1m + 2,000 1D) at 180 req/min finishes in exactly $\approx 13.9$ minutes.
- Fixed cron expression to valid 5-field syntax: `45 15 * * 1-5` (`Asia/Kolkata`).
- Added missed-run catch-up state machine on application launch when market is closed.
- Sourced market holidays from Phase 03 automated script and DuckDB `market_holidays` table.
- Detailed pre-flight probe at 15:40 IST: token refresh failure transitions `job_logs` to `FAILED_AUTH` and alerts user in UI without crashing.
- Checkpoints utilize `latest_ts` (`TIMESTAMP`) with idempotent day re-fetch to capture settled closing prints.
