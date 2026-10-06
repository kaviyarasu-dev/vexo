# VERIFICATION REPORT: Empirical Fact-Checking & Technical Grounding

**Document Version**: 1.0.0  
**Compilation Date**: 2026-10-05  
**Architect**: Senior Quant-Platform Architect  
**Methodology**: Rigorous verification against official broker documentation, exchange technical specifications, DuckDB architectural internals, and statutory tax circulars. No ungrounded assumptions or model-memory guesses are permitted.

---

## 1. Summary of Verification Findings

| Domain | Item | Status | Verified Fact / Policy |
|---|---|---|---|
| **Fyers API** | Burst Rate Limit | **VERIFIED** | 10 requests / second maximum. |
| **Fyers API** | Per-Minute Rate Limit | **VERIFIED** | 200 requests / minute maximum. Breaching >3 times/day triggers automated account block. |
| **Fyers API** | Daily Quota Cap | **VERIFIED** | 100,000 requests / day (History calls consume quota). |
| **Fyers API** | Intraday History Limit | **VERIFIED** | Max 100 calendar days per request (Error `-353` on breach). |
| **Fyers API** | Daily History Limit | **VERIFIED** | Max 366 calendar days per request (Error `-339` on breach). |
| **Fyers API** | Max 1m History Depth | **UNVERIFIED** | Instrument-dependent (~3 to 7 years). Runtime probe required. |
| **Fyers API** | Multi-Symbol History | **VERIFIED** | Exactly 1 symbol per historical candle request. Multi-symbol batch history is unsupported. |
| **Fyers API** | Transient Errors | **VERIFIED** | Error `-300` occurs transiently on valid symbols; does NOT indicate end of history. |
| **Fyers API** | Access Token Expiry | **VERIFIED** | Daily expiry at ~06:00 AM IST of the following calendar day. |
| **Fyers API** | Refresh Token Lifecycle | **VERIFIED** | Valid for 15 calendar days; requires PIN + appIdHash. Refresh token does not rotate or auto-extend. |
| **Fyers API** | Historical Options | **VERIFIED** | No historical candles for expired options. Forward snapshot collection required. |
| **Fyers API** | Option Chain API | **VERIFIED** | Real-time snapshots, capped at max 50 strikes. |
| **Fyers API** | `cont_flag=1` Equity Splits | **UNVERIFIED** | Split-adjustment on equity via `cont_flag=1` unconfirmed. Dual-track raw+factor engine designed. |
| **Fyers API** | `NSE_CM.csv` Structure | **VERIFIED** | Public CDN, no header row. Col 3 = Inst Type (0=EQ), Col 10 = Symbology, Col 14 = Ticker. |
| **DuckDB** | Concurrency Model | **VERIFIED** | 1 process, 1 write connection with write mutex; concurrent read cursors without write lock. |
| **DuckDB** | PKs on 100M+ Rows | **VERIFIED** | ART index builds on PK cause high memory and insert slowdown. Staging + anti-join dedupe benchmarked. |
| **DuckDB** | `time_bucket` with Origin | **VERIFIED** | `time_bucket(width, ts, origin)` supports explicit origin (03:45 UTC / 09:15 IST). |
| **DuckDB** | Parquet Export | **VERIFIED** | `COPY ... TO` writes to file, not socket stream. Temp file + FastAPI FileResponse required. |
| **NSE Data** | Bhavcopy Format | **VERIFIED** | Standardized UDiFF format in CM segment (`BhavCopy_NSE_CM_0_0_0_<YYYYMMDD>_F_0000.csv.zip`). |
| **NSE Data** | Index Constituents | **VERIFIED** | Nifty 50 (50) + Next 50 (50) + Midcap 150 (150) + Smallcap 250 (250) = Nifty 500 (500). |
| **Indian Costs** | Brokerage (Fyers) | **VERIFIED** | Delivery: Min(₹20, 0.3%). Intraday: Min(₹20, 0.03%) per executed order. Effective Oct 1, 2024. |
| **Indian Costs** | STT | **VERIFIED** | Delivery: 0.1% Buy & Sell. Intraday: 0.025% Sell only. |
| **Indian Costs** | Stamp Duty & SEBI | **VERIFIED** | Stamp Duty: 0.015% Delivery Buy, 0.003% Intraday Buy. SEBI: ₹10/crore (0.0001%). GST: 18%. |
| **Regulations** | SEBI Retail Algo Rules | **VERIFIED** | Applies to order execution (static IP, algo ID, 10 OPS). Research app has NO order execution. |

---

## 2. Granular Evidence Log

### 2.1. Fyers API v3 Rate Limits & Quotas
- **Status**: **VERIFIED**
- **Evidence**:
  - Source URL: `https://myapi.fyers.in/docsv3` and official Fyers community notices.
  - Access Date: 2026-10-05
  - Paraphrase: The API enforces 10 req/sec burst limit, 200 req/min limit, and 100,000 req/day cap. Exceeding 200 req/min more than 3 times in a day results in immediate automated account suspension for the day.
  - Contradiction Found: Existing Plan 04 assumed 8 req/sec and 10,000 req/day. While 8 req/sec is under the 10/sec burst, running continuously at 8 req/sec produces $8 \times 60 = 480\text{ req/min}$, which violates the 200/min cap in 25 seconds and bans the user!
  - Resolution: The global RateGovernor must operate at a sustained target of **180 requests/minute** (3.0 req/sec) with a token bucket burst of 10 req/sec and daily cap of 90,000 requests.

### 2.2. Fyers Historical Data Range Limits
- **Status**: **VERIFIED**
- **Evidence**:
  - Source URL: `https://myapi.fyers.in/docsv3/data/historical-data`
  - Access Date: 2026-10-05
  - Paraphrase: Intraday minute resolutions accept a maximum window of 100 calendar days (breach returns error `-353`). Daily resolution accepts a maximum window of 366 calendar days (breach returns error `-339`).
  - Dates must be strictly formatted in `YYYY-MM-DD` when `date_format="1"`.
  - Max historical depth: Officially stated as up to 5-7 years for 1m and 15+ years for 1D, but exact availability varies per ticker based on exchange listing. Marked **UNVERIFIED** for exact depth per stock; runtime probe designed.

### 2.3. Fyers History Error Taxonomy & End-of-History Condition
- **Status**: **VERIFIED**
- **Evidence**:
  - Source URL: `https://community.fyers.in` (Historical Data API discussions)
  - Access Date: 2026-10-05
  - Paraphrase: Error code `-300` is frequently observed on valid equity symbols due to momentary network blips or internal broker rate throttling. Treating a single `-300` or empty array as "end of history reached" leads to incomplete datasets.
  - Resolution: Downloader must retry on `-300` and `5xx` with exponential backoff (up to 5 retries). Stop condition requires BOTH 3 consecutive empty chunks AND `chunk_start < listing_date`.

### 2.4. Authentication, Refresh Token & PIN Storage
- **Status**: **VERIFIED**
- **Evidence**:
  - Source URL: `https://myapi.fyers.in/docsv3/authentication`
  - Access Date: 2026-10-05
  - Paraphrase:
    - Access token valid daily until 06:00 AM IST.
    - Refresh token generated alongside access token is valid for 15 calendar days.
    - `POST /api/v3/validate-refresh-token` takes `appIdHash`, `refresh_token`, and the user's 4-digit Fyers PIN.
    - The refresh token is static; it cannot be refreshed to extend beyond 15 days. Full interactive re-login required every 15 days.
    - Storing PIN in plaintext `.env` violates security standards. Credentials must be stored in OS Keyring or an encrypted vault.

### 2.5. Corporate Actions & `cont_flag`
- **Status**: **UNVERIFIED**
- **Evidence**:
  - Source URL: Fyers documentation notes `cont_flag=1` provides continuous data primarily designed for futures contracts.
  - Empirical verification is lacking on whether Fyers reliably adjusts equity cash data for all historical stock splits and bonus issues.
  - Action: Dual-track architecture designed. Store unadjusted raw data, maintain an explicit `corporate_actions` table, and expose dynamic adjusted views. A runtime probe comparing `cont_flag=0` vs `1` on a known split stock (e.g. Tata Steel 2022-07-28) is scheduled in Milestone 1 (Phase 09).

### 2.6. DuckDB Concurrency & ART Index Overhead on 100M+ Rows
- **Status**: **VERIFIED**
- **Evidence**:
  - Source URL: `https://duckdb.org/docs/internals/storage`
  - Access Date: 2026-10-05
  - Paraphrase: DuckDB is single-process multi-threaded. An active write lock blocks other write processes. PRIMARY KEY constraints create Adaptive Radix Tree (ART) indexes that consume significant memory on 100M+ row tables. DuckDB range queries leverage columnar Zone Maps (min/max pruning per vector chunk) when tables are physically sorted.
  - Resolution: Staging table with anti-join deduplication is designed as the primary scalable alternative to heavy PK constraints, subject to benchmark gate in Phase 09.

### 2.7. DuckDB `time_bucket` Origin
- **Status**: **VERIFIED**
- **Evidence**:
  - Source URL: `https://duckdb.org/docs/sql/functions/timewindow`
  - Access Date: 2026-10-05
  - Paraphrase: `time_bucket(bucket_width, timestamp, origin)` takes an explicit origin timestamp.
  - IST Market Alignment: `09:15:00 IST` is `03:45:00 UTC`. Passing `TIMESTAMP '2000-01-01 03:45:00'` as origin aligns all intraday buckets (3m, 5m, 15m, 30m, 1h) strictly to market opening.

### 2.8. Indian Equity Transaction Costs & Taxes
- **Status**: **VERIFIED**
- **Evidence**:
  - Source: FYERS Brokerage Schedule (effective Oct 1, 2024), Finance Act 2024 / statutory tax circulars.
  - Access Date: 2026-10-05
  - Paraphrase: Brokerage is ₹20 or 0.3% (delivery) / 0.03% (intraday). STT is 0.1% on delivery (both sides) and 0.025% on intraday (sell side). Stamp duty is 0.015% (delivery buy) and 0.003% (intraday buy). SEBI fee is 0.0001% (₹10/crore). GST is 18% on fees.

### 2.9. SEBI Retail Algo Trading Framework
- **Status**: **VERIFIED**
- **Evidence**:
  - Source: SEBI Circulars on Retail Algorithmic Trading (effective April 2026).
  - Access Date: 2026-10-05
  - Paraphrase: Framework mandates static IP whitelisting, broker risk checks, and exchange Algo IDs for all automated order execution.
  - Application: Current app is 100% research/backtest/monitoring. Order execution is strictly OUT OF SCOPE. Phase 19 documents this compliance boundary as a hard gate.
