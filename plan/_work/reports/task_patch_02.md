# Report: Patch 02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md

**Status**: Done  
**File Written**: `plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md`  
**Open Questions Count**: 0  

### Summary of Changes
- Added full EXECUTION CONTRACT with exact dependencies, test plan, Definition of Done, and failure recovery.
- Updated relational DDL schemas to match 00A Section 4: added `schema_version`, separated raw storage (`candles_1m_raw`, `candles_1d_raw`) from dynamic views (`candles_1m_adjusted`, `candles_1d_adjusted`), added `corporate_actions` and `adjustment_factors`, updated `download_checkpoints` to `earliest_ts` and `latest_ts` (`TIMESTAMP`).
- Resolved the 100M+ row PK dilemma: documented the ART index memory footprint and detailed the staging table + anti-join deduplication architecture as the primary high-throughput engine, with Phase 09 benchmark gate.
- Rewrote the concurrency section: decoupled read cursors (`conn.cursor()`) from the single write connection/queue.
- Enforced canonical interfaces (`ICandleReader`, `ICandleWriter`, `ISymbolRepository`, `ICheckpointRepository`).
