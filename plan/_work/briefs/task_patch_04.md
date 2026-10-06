# Task Brief: Patch 04_HISTORICAL_DOWNLOADER_ENGINE.md

**Target File**: `plan/04_HISTORICAL_DOWNLOADER_ENGINE.md` (ONLY this file may be modified)  
**Allowed Read Set**:
- `plan/00A_CONTRACTS_AND_CONVENTIONS.md`
- `plan/04_HISTORICAL_DOWNLOADER_ENGINE.md`
- `plan/VERIFICATION_REPORT.md`

**Objective**:
Upgrade `04_HISTORICAL_DOWNLOADER_ENGINE.md` to enterprise quant architecture standards:
1. Add mandatory EXECUTION CONTRACT block at top.
2. Redesign the rate limiting around the shared Global RateGovernor:
   - Hard limits: 10/sec burst, 200/min cap, 100,000/day.
   - Target rate: 180 req/min (3.0 req/sec), 90,000 req/day soft cap.
   - Priority lanes: Lane 1 (Interactive) > Lane 2 (Incremental Sync) > Lane 3 (Historical Backfill).
3. Recompute ALL request budgets and time estimates with complete arithmetic shown:
   - Chunk sizes: 100 calendar days for 1m, 366 calendar days for 1D.
   - Nifty 500 (500 stocks) 1m backfill: $500 \times 19 = 9,500$ reqs ($\sim 53$ min at 180 req/min).
   - All active stocks (2,000 stocks) 1D backfill: $2,000 \times 15 = 30,000$ reqs ($\sim 167$ min).
   - Total Day 1: $39,500$ reqs (well under 90,000 daily budget).
   - Daily sync: 2,500 reqs ($\sim 14$ min).
4. Replace flawed "empty response = end of history" rule:
   - Must encounter $\ge 3$ consecutive empty chunks AND `chunk_start < listing_date`.
5. Map complete error taxonomy: `-300`, `429`, `-353`, `-339`, `-16`, `401`, `5xx`.
6. Enforce canonical interfaces: `IMarketDataProvider`, `ICandleWriter`, `ICheckpointRepository`.
7. Keep file under 400 lines.

**Acceptance Self-Test**:
- Begins with EXECUTION CONTRACT.
- Rate limits strictly use 180/min target under 200/min cap; old 8 req/sec assumption completely removed.
- All request counts and time calculations show exact arithmetic.
- Error taxonomy and robust stop condition fully detailed.
