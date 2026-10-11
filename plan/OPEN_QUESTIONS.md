# OPEN QUESTIONS & RUNTIME PROBES REGISTRY

**Document Version**: 1.0.0  
**Status**: Active  
**Rule**: Every item tagged `UNVERIFIED` in `VERIFICATION_REPORT.md` must appear here with an empirical probe, execution phase, and safe production default. No unverified assumptions are permitted in implementation code.

---

## 1. Open Questions Matrix

| ID | Topic / Item | Description of Uncertainty | Settling Probe / Test Design | Executing Phase | Safe Production Default |
|---|---|---|---|---|---|
| **OQ-01** (VERIFIED) | `cont_flag=1` Equity Adjustment | Does Fyers `cont_flag="1"` accurately adjust historical cash equity candles for splits and bonuses? | **Split Ratio Verification Probe**: Select a stock with a known historical split (e.g., Tata Steel `NSE:TATASTEEL-EQ`, 10:1 split on 2022-07-28). Fetch `range_from="2022-07-20"` to `range_to="2022-08-05"` with `cont_flag="0"` and `cont_flag="1"`. Check if pre-split close prices in `cont_flag=1` equal $1/10$th of `cont_flag=0`. Pass if ratio matches split factor within 0.1%; fail if unchanged. | Phase 09 (Milestone 1 Benchmark) | Download and store RAW candles (`cont_flag="0"`). Compute adjusted series dynamically using official NSE corporate actions table and adjustment factor engine (Phase 15). |
| **OQ-02** (VERIFIED) | Maximum 1m History Depth | What is the exact earliest available date for 1-minute historical candles from Fyers for liquid stocks? | **Earliest Date Discovery Probe**: Disptach backward-walking 100-day 1m requests for `NSE:RELIANCE-EQ` starting from 2020 backward to 2015. Record earliest candle timestamp returned before 3 consecutive empty chunks occur. | Phase 09 (Milestone 1 Benchmark) | Default historical backfill target configured to 5 years (1,825 calendar days) from current date, capped dynamically at earliest returned timestamp. |
| **OQ-03** (VERIFIED) | DuckDB PK Overhead on 100M+ Rows | Does a `PRIMARY KEY (symbol, timestamp)` constraint in DuckDB cause memory exhaustion or severe ingestion slowdown at 100M+ rows? | **Synthetic Scaling Benchmark Probe**: Generate synthetic candle batches (1M, 10M, and 100M rows). Benchmark insertion throughput (rows/sec), peak memory consumption (MB), and range query latency (ms) for: (A) Table with `PRIMARY KEY`, vs (B) Unindexed table with sorted inserts and staging anti-join deduplication. | Phase 09 (Gate Benchmark) | Staging table with anti-join deduplication (`INSERT INTO master SELECT * FROM staging WHERE NOT EXISTS ...`). |
| **OQ-04** (VERIFIED) | Intraday Candle Epoch Convention | Does Fyers intraday timestamp represent the bar START time (e.g. 09:15) or bar CLOSE time (e.g. 09:16)? | **Market Open Timestamp Probe**: Inspect the first intraday candle of any standard trading session. Verify whether the epoch translates to `09:15:00 IST` or `09:16:00 IST`. | Phase 01 / Phase 09 Test Suite | Treat timestamp as bar start time (`09:15:00 IST`); if probe reveals close-time convention, apply a standardized `- INTERVAL '1 MINUTE'` normalizer at ingestion. |
| **OQ-05** (VERIFIED) | Daily Candle Epoch Timestamp | Does Fyers Daily (`1D`) candle epoch timestamp represent IST midnight or UTC midnight? | **Daily Epoch Alignment Probe**: Parse the raw epoch integer for `1D` candles. Verify if `epoch % 86400 == 0` (UTC midnight) or `epoch % 86400 == 66600` (IST midnight / 18:30 UTC previous day). | Phase 01 / Phase 09 Test Suite | Store daily candles with `DATE` column type (`YYYY-MM-DD`), parsed from Fyers date string or normalized session date, ignoring time-of-day offsets. |
| **OQ-06** | Fundamental Data Availability | Does Fyers API provide fundamental financial metrics (P/E, Market Cap, Debt/Equity) for equity stocks? | **Fundamental API Probe**: Query Fyers quotes and market depth endpoints for presence of fundamental ratios. | Phase 12 (Screener Engine) | If fundamental metrics are unavailable from broker API, screener defaults to pure technical and volume/turnover filters, with optional CSV import for fundamentals. |

---

## 2. Probe Execution Protocol

1. **Isolation**: Probes must execute within dedicated test scripts (`tests/probes/test_probe_*.py`) without modifying production database files.
2. **Recording**: When a probe executes during Phase 09, its results must be recorded in `artifacts/probe_results.json` and merged into `VERIFICATION_REPORT.md`.
3. **Transition**: Once verified, the status in `VERIFICATION_REPORT.md` transitions from `UNVERIFIED` to `VERIFIED`, and the corresponding open question is marked resolved.
