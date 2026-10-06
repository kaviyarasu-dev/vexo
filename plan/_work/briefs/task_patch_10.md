# Task Brief: Patch 10_EDGE_CASES_RISKS_AND_MAINTENANCE.md

**Target File**: `plan/10_EDGE_CASES_RISKS_AND_MAINTENANCE.md` (ONLY this file may be modified)  
**Allowed Read Set**:
- `plan/00A_CONTRACTS_AND_CONVENTIONS.md`
- `plan/10_EDGE_CASES_RISKS_AND_MAINTENANCE.md`
- `plan/VERIFICATION_REPORT.md`

**Objective**:
Upgrade `10_EDGE_CASES_RISKS_AND_MAINTENANCE.md` to enterprise quant architecture standards:
1. Add mandatory EXECUTION CONTRACT block at top.
2. Formulate Corporate-Action Integrity Audit:
   - Scans for single-bar price shifts $> 25\%$; cross-references detected anomalies against the official `corporate_actions` table. Emits audit alerts for unadjusted splits or bad ticks.
3. Automated Backup & Disaster Recovery Drill:
   - Weekly Parquet snapshot export (`EXPORT DATABASE ... (FORMAT PARQUET)`).
   - Automated restoration drill: loads snapshot into an isolated scratch database (`data/scratch/restore_test.duckdb`) and verifies table row counts match production before declaring backup valid.
4. Schema Migration Rollback:
   - Formalize rollback protocol for `schema_version` (down-migrations, transaction wrapping).
5. Routine Maintenance:
   - Automated post-sync `CHECKPOINT;` to truncate WAL.
   - Weekly Saturday 02:00 AM `VACUUM;` to reclaim freed space and refresh zone-map statistics.
6. Keep file under 400 lines.

**Acceptance Self-Test**:
- Begins with EXECUTION CONTRACT.
- Corporate action audit rules specified with $> 25\%$ threshold.
- Backup restore drill script and schema rollback protocol documented.
