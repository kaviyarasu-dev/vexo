# Report: Patch 04_HISTORICAL_DOWNLOADER_ENGINE.md

**Status**: Done  
**File Written**: `plan/04_HISTORICAL_DOWNLOADER_ENGINE.md`  
**Open Questions Count**: 0  

### Summary of Changes
- Added full EXECUTION CONTRACT with exact dependencies, test plan, Definition of Done, and failure recovery.
- Redesigned rate limiting around the shared Global RateGovernor: replaced the broken 8 req/sec assumption with the verified 180 req/min target (under the 200/min cap), 10 req/sec burst ceiling, and 90,000 req/day soft cap, organized into 3 priority lanes.
- Recomputed all request budgets with exact arithmetic: Nifty 500 1m backfill = 9,500 reqs (~53 min); All active stocks 1D backfill = 30,000 reqs (~2.8 hrs); Total initial ingestion = 39,500 reqs completed in ~3.7 hours on Day 1. Daily sync = 2,500 reqs (~14 min).
- Replaced naive "empty response = end of history" rule with robust check requiring BOTH $\ge 3$ consecutive empty chunks AND `chunk_start < listing_date`.
- Mapped full Fyers error taxonomy (`-300`, `429`, `-353`, `-339`, `-16`, `401`, `5xx`).
- Enforced canonical interfaces: `IMarketDataProvider`, `ICandleWriter`, `ICheckpointRepository`.
