# Plan 005: Phase 09 Hard Gate Benchmark Tuning & Final Report

## Goal
Tune Gate 4 query latency in `scripts/run_m1_benchmark.py` to $\le 200$ms, verify all 5 gates pass against `NSE:RELIANCE-EQ`, and generate the final benchmark report:
1. Inspect Gate 4 query execution profile in `scripts/run_m1_benchmark.py`.
2. Optimize index lookups or query projections in `scripts/run_m1_benchmark.py` to achieve latency $\le 200$ms.
3. Execute `python scripts/run_m1_benchmark.py` and verify Gate 1 through Gate 5 pass.
4. Write benchmark report artifact to `artifacts/m1_benchmark_results.json`.

## Read first
- `trading-app/scripts/run_m1_benchmark.py`
- `trading-app/db/migrations.py`
- `trading-app/db/connection.py`

## Steps

### Step 1: Profile Gate 4 query latency bottleneck
- Inspect `run_gate_4_duckdb_scaling()` in `scripts/run_m1_benchmark.py`.
- Identify the timing overhead during `time_bucket('5 MINUTE', timestamp)` aggregation across 10,000,000 in-memory rows.
- Note that without a clustered sort or primary key ordering on `timestamp`, full-table scans can slightly exceed 200ms.

### Step 2: Implement index and query optimization
- In `scripts/run_m1_benchmark.py`, ensure `candles_1m_raw` table definition or insertion includes `ORDER BY timestamp` or an index on `timestamp`.
- Verify query execution latency drops well below the 200ms ceiling (typically achieving 5ms to 50ms).

### Step 3: Execute complete 5-gate benchmark suite
- Run `scripts/run_m1_benchmark.py`:
  - Gate 1: Rate Soak (100,000 requests without 429 throttling).
  - Gate 2: Timestamp Alignment (IST boundary conformance).
  - Gate 3: Split Probe (Zero duplicate rows across corporate actions).
  - Gate 4: DuckDB PK vs Staging Scaling (Insert $> 25,000$ rows/sec, query latency $\le 200$ms).
  - Gate 5: Empirical Disk Size (Measured bytes per candle $\le 15$ bytes, projected Nifty 500 database $\le 5$ GB).

### Step 4: Validate and record benchmark artifact
- Confirm `artifacts/m1_benchmark_results.json` contains `"ALL_PASSED": true`.
- Update `plan/HANDOFF.md` or platform status ledger with Gate 1 to Gate 5 completion metrics.

## Do not touch
- `trading-app/services/backtest/engine.py`
- `trading-app/api/routers/auth.py`

## Acceptance
Run:
```bash
.\.venv\Scripts\python.exe scripts/run_m1_benchmark.py
```
All 5 gates must pass and the script must exit with status code 0.

## If blocked
Write exact error trace and attempted fixes to `docs/plans/platform-automation-and-backlog/BLOCKED.md` and stop.

## Report back
Provide benchmark JSON output confirming all 5 hard gates passed.
