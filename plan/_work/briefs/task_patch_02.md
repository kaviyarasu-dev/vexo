# Task Brief: Patch 02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md

**Target File**: `plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md` (ONLY this file may be modified)  
**Allowed Read Set**:
- `plan/00A_CONTRACTS_AND_CONVENTIONS.md`
- `plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md`
- `plan/VERIFICATION_REPORT.md`

**Objective**:
Upgrade `02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md` to enterprise quant architecture standards:
1. Add mandatory EXECUTION CONTRACT block at top.
2. Update schema DDLs to match 00A Section 4:
   - Add `schema_version` table for versioned migrations.
   - Separate raw storage (`candles_1m_raw`, `candles_1d_raw`) from dynamic views (`candles_1m_adjusted`, `candles_1d_adjusted`).
   - Add `corporate_actions` and `adjustment_factors` tables.
   - Update `download_checkpoints` to use `earliest_ts` and `latest_ts` as `TIMESTAMP` (not date).
3. Primary Key & Index Strategy on 100M+ Rows:
   - Detail DuckDB ART index memory/slowdown implications.
   - Specify staging table + anti-join deduplication as the high-throughput design.
   - Schedule benchmark gate in Phase 09.
4. Concurrency Architecture:
   - Rewrite concurrency section: ONE dedicated write connection with queue/mutex; API reads acquire independent cursors (`conn.cursor()`) without the write lock.
5. Standardize interfaces: `ICandleReader`, `ICandleWriter`, `ISymbolRepository`, `ICheckpointRepository`.
6. Keep file under 400 lines.

**Acceptance Self-Test**:
- Begins with EXECUTION CONTRACT.
- All DDL definitions match 00A Section 4 exactly.
- Staging table + anti-join dedupe documented alongside PK index benchmark.
- Concurrency model explicitly decouples read cursors from writer lock.
