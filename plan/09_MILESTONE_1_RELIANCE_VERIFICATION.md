# Phase 09: Milestone 1 Verification & Scaling Readiness Benchmark

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "plan/00_MASTER_ARCHITECTURE.md"
    - "plan/01_ENVIRONMENT_CONFIG_AND_AUTH.md"
    - "plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md"
    - "plan/03_SYMBOL_MASTER_AND_UNIVERSE_MANAGER.md"
    - "plan/04_HISTORICAL_DOWNLOADER_ENGINE.md"
    - "plan/05_RESAMPLING_AND_QUANT_METRICS_ENGINE.md"
    - "plan/06_DAILY_INCREMENTAL_UPDATE_AND_SCHEDULER.md"
    - "plan/07_FASTAPI_BACKEND_AND_QUANT_APIS.md"
    - "plan/08_FRONTEND_CHARTING_AND_DASHBOARD.md"
  reads:
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md"
    - "plan/VERIFICATION_REPORT.md"
    - "plan/OPEN_QUESTIONS.md"
  produces:
    - "scripts/run_m1_benchmark.py"
    - "tests/probes/test_probe_split_adjustment.py"
    - "tests/probes/test_probe_timestamp_conventions.py"
    - "tests/probes/test_probe_duckdb_scaling.py"
    - "artifacts/m1_benchmark_report.md"
    - "artifacts/probe_results.json"
  exposes: []
  must_not_modify:
    - "plan/*"
    - "db/migrations.py"
  test_plan:
    unit_tests: "tests/unit/test_benchmark_metrics.py"
    integration_tests: "tests/integration/test_m1_pipeline.py"
    contract_tests: "tests/contract/test_m1_gates.py"
    fixtures: "tests/fixtures/reliance_m1_golden_dataset.json"
    command: "python scripts/run_m1_benchmark.py"
  definition_of_done:
    - item: 1
      command: "python scripts/run_m1_benchmark.py --soak-minutes 30"
      result: "Completes 30-minute rate soak test with zero HTTP 429 errors and sustained rate <= 180 req/min."
    - item: 2
      command: "pytest tests/probes/test_probe_split_adjustment.py"
      result: "Verifies historical split adjustment ratio within 0.1% of nominal split factor across ex-date."
    - item: 3
      command: "python scripts/run_m1_benchmark.py --check-gates"
      result: "All 5 empirical scaling gates pass with measured metrics written to artifacts/m1_benchmark_report.md."
  failure_modes_and_recovery:
    - failure: "DuckDB ART index insertion degrades on 100M row synthetic test"
      detection: "Insertion speed drops below 10,000 rows/sec or RAM exceeds 4 GB during test_probe_duckdb_scaling.py"
      recovery: "Formally adopt staging table + anti-join deduplication architecture as the production standard"
    - failure: "Measured disk footprint per candle exceeds 20 bytes"
      detection: "Measured bytes/candle > 20 in artifacts/probe_results.json"
      recovery: "Enforce sorting by (symbol, timestamp) prior to batch commits to maximize ALP and dictionary compression"
  handoff:
    - "Milestone 1 benchmark passed on RELIANCE."
    - "Open questions OQ-01, OQ-02, OQ-03, OQ-04 empirically settled."
    - "Scaling Readiness Gate UNLOCKED for full-universe ingestion and Phase 11+."
```

---

## 1. Goal & Scope
Execute an end-to-end, empirical verification benchmark on `NSE:RELIANCE-EQ` across all system components before scaling to the full universe adhering to the 00A Canonical Registry.

This phase delivers:
- Complete historical download of `NSE:RELIANCE-EQ` (maximum available 1m intraday and 15+ years of 1D EOD).
- **The Five Mandatory Scaling Readiness Gates**:
  1. **Rate-Limit Soak Gate**: 30-minute continuous download soak achieving zero 429 errors and $\le 180\text{ req/min}$.
  2. **Timestamp Convention Gate**: Recorded-fixture test verifying intraday epoch aligns to 09:15:00 IST (`03:45:00 UTC`) and daily bars align to pure dates.
  3. **Adjustment Correctness Gate**: Probe comparing `cont_flag=0` vs `1` vs corporate actions ledger across a known split ex-date.
  4. **DuckDB PK vs Staging Scaling Gate**: Synthetic scaling benchmark at 1M, 10M, and 100M rows comparing `PRIMARY KEY` vs Staging anti-join deduplication.
  5. **Empirical Disk Size Gate**: Extrapolating database size from measured bytes/candle rather than guesses.
- Generation of the official Markdown benchmark report (`artifacts/m1_benchmark_report.md`).

---

## 2. SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `MilestoneBenchmarkSuite`: Responsible solely for executing latency, storage, and correctness measurements and reporting metrics.
  - Test probes are decoupled into discrete standalone modules under `tests/probes/`.
- **Dependency Inversion Principle (DIP)**:
  - Verification scripts execute exclusively against production interfaces (`ICandleReader`, `IResamplingService`, `IDataExporter`).

---

## 3. The Five Quantitative Scaling Readiness Gates

### 3.1. Gate 1: Rate-Governor 30-Minute Soak Gate
- **Protocol**: Dispatches continuous requests for 30 minutes under RateGovernor Lane 3.
- **Pass Criteria**:
  - Total HTTP 429 ("Too Many Requests") errors: **STRICTLY ZERO**.
  - Peak 1-minute request throughput: $\le \mathbf{180\text{ requests / minute}}$.
  - Account suspension warnings: **ZERO**.

### 3.2. Gate 2: Timestamp Convention & Session Alignment Gate
- **Protocol**: Inspects raw timestamps returned by Fyers and stored in `candles_1m_raw` for RELIANCE.
- **Pass Criteria**:
  - Intraday Market Open: First bar of every standard trading session starts at `03:45:00 UTC` (`09:15:00 IST`).
  - Intraday Market Close: Final bar starts at `09:59:00 UTC` (`15:29:00 IST`) with duration 1 minute.
  - Zero timestamps exist outside trading session hours (`03:45:00 to 10:00:00 UTC`).
  - Daily timestamps are stored as discrete `DATE` (`YYYY-MM-DD`).

### 3.3. Gate 3: Corporate Action Adjustment Correctness Gate
- **Protocol** (Settles **OQ-01** from `OPEN_QUESTIONS.md`):
  - Fetches candles across a known split event (e.g., Tata Steel 10:1 split on 2022-07-28 or IRCTC 5:1 split on 2021-10-28).
  - Evaluates:
    $$\text{Ratio} = \frac{\text{Close}_{\text{pre-split}}}{\text{Close}_{\text{post-split}}}$$
  - **Pass Criteria**:
    - If `cont_flag="1"` returns prices pre-adjusted by the exact split ratio ($10.0 \pm 0.1\%$), `cont_flag=1` is validated.
    - If not, verify that `candles_1m_adjusted` view correctly applies `adjustment_factors` to raw data with $< 0.1\%$ variance from official exchange adjusted prices.

### 3.4. Gate 4: DuckDB PK vs Staging Scaling Gate (100M Rows)
- **Protocol** (Settles **OQ-03** from `OPEN_QUESTIONS.md`):
  - Generates synthetic candle batches at 1M, 10M, and 100M rows.
  - Benchmarks:
    1. Table A: `PRIMARY KEY (symbol, timestamp)`
    2. Table B: Unindexed table with sorted inserts + temporary staging anti-join deduplication.
- **Measurements Recorded**:
  - Batch insertion speed (rows / second).
  - Peak memory usage during bulk load (MB).
  - Query latency for a 1-month 5m resample slice (ms).
- **Pass Criteria**:
  - Winning strategy must sustain $\ge \mathbf{25,000\text{ rows / second}}$ at 100M rows with peak RAM $< \mathbf{2.5\text{ GB}}$.

### 3.5. Gate 5: Empirical Disk Size & Query Latency Gate
- **Protocol**:
  - Measure empty database size ($S_0$).
  - Ingest full history for `NSE:RELIANCE-EQ` (15 years 1D, maximum available 1m).
  - Measure final database size ($S_{\text{final}}$) and total row count ($N_{1m}$).
  - Calculate real measured bytes per candle:
    $$B_{\text{candle}} = \frac{S_{\text{final}} - S_0}{N_{1m}}$$
  - Extrapolate full Nifty 500 footprint:
    $$S_{\text{Nifty500}} = 500 \times 468,750 \times B_{\text{candle}}$$
- **Pass Criteria**:
  - Measured $B_{\text{candle}} \le \mathbf{15\text{ bytes / candle}}$.
  - Projected Nifty 500 storage $\le \mathbf{5.0\text{ GB}}$.
  - Server-side 5m resampling query latency $\le \mathbf{25\text{ ms}}$.
  - Full quant indicator pipeline (VWAP + RSI + MACD + BB) latency $\le \mathbf{120\text{ ms}}$.
  - Parquet export of 1 year 1m data streams in $\le \mathbf{1.5\text{ seconds}}$.

---

## 4. Implementation Steps
1. Create `tests/probes/test_probe_split_adjustment.py` implementing Gate 3.
2. Create `tests/probes/test_probe_timestamp_conventions.py` implementing Gate 2.
3. Create `tests/probes/test_probe_duckdb_scaling.py` implementing Gate 4.
4. Create `scripts/run_m1_benchmark.py`:
   - Runs soak test, executes probes, ingests full RELIANCE history.
   - Measures query latencies across 50 consecutive runs.
   - Emits structured report to `artifacts/m1_benchmark_report.md` and metrics JSON to `artifacts/probe_results.json`.

---

## 5. Verification & Acceptance Criteria
- Running `python scripts/run_m1_benchmark.py` completes with exit code 0.
- All 5 scaling gates pass without exceptions.
- `artifacts/m1_benchmark_report.md` contains verified empirical measurements.
- Milestone 1 checklist in `HANDOFF.md` marked PASSED, unlocking multi-symbol full-universe scaling.
