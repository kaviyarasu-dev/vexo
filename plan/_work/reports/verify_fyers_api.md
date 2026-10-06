# Verification Report: Fyers API v3 Specifications

**Research Topic**: Fyers API v3 (Limits, History, Errors, Auth, Options, Symbology)  
**Date of Research**: 2026-10-05  
**Reviewer/Researcher**: Stage A Quant Architect Researcher  

---

## 1. Rate Limits & Quotas
- **Status**: VERIFIED
- **Source**: Fyers API v3 Official Documentation & Community Developer Guidelines (`https://myapi.fyers.in/docsv3`)
- **Paraphrase**: Fyers enforces a strict multi-tier rate limit: 10 requests/second burst, 200 requests/minute, and 100,000 requests/day. History API calls count directly against these limits.
- **Critical Caveat**: Exceeding the per-minute limit (200 req/min) more than 3 times in a single calendar day results in automated account-level API suspension for the remainder of the day.
- **Architectural Requirement**:
  - The Global RateGovernor must enforce a conservative target of **180 requests/minute** (3.0 req/sec sustained) with a burst ceiling of 10 req/sec and a daily soft cap of 90,000 requests (leaving 10,000 buffer under the 100,000 hard cap).
  - The old assumption in plan 04 (8 req/sec = 480 req/min) would violate the 200/min cap within 25 seconds and trigger an immediate day-long ban!

---

## 2. History Range & Chunking Constraints
- **Status**: VERIFIED
- **Source**: Fyers V3 Data API Specification (`https://myapi.fyers.in/docsv3/data/historical-data`)
- **Paraphrase**:
  - Intraday resolutions (`1`, `2`, `3`, `5`, `10`, `15`, `20`, `30`, `45`, `60`, `120`, `180`, `240` minutes): Maximum **100 calendar days** per request. Exceeding 100 calendar days triggers error response (`-353`).
  - Daily resolution (`1D`): Maximum **366 calendar days** (or 1 full year) per request. Exceeding triggers error response (`-339`).
  - Max history depth: Varies per instrument based on listing date and exchange retention (~5 to 7 years for 1m, 15+ years for 1D).
- **Status**: UNVERIFIED (Max history depth for specific symbols)
  - A runtime probe must be run during Milestone 1 (Phase 09) on `NSE:RELIANCE-EQ` to discover exact earliest 1m timestamp available.

---

## 3. Error Handling & Stop Conditions
- **Status**: VERIFIED
- **Source**: Fyers Community & Developer Logs (`https://community.fyers.in`)
- **Paraphrase**:
  - Error `-300` is a generic/transient server-side or connection error that can occur even on valid liquid equity symbols.
  - Therefore, treating a single empty response or error `-300` as "end of history reached" (as done in old plan 04) causes premature truncation of historical data.
- **Architectural Rule**:
  - Stop condition requires: `consecutive_empty_chunks >= 3` AND `chunk_start_date < listing_date` (or < 2017-01-01 for legacy stocks).
  - Error `-300` / `500` / `502` / `504`: Exponential backoff and retry up to 5 times.
  - Error `429`: Backoff starting at 2.0s with jitter, reducing token refill rate.
  - Error `-353` / `-339`: Bug in chunker (window exceeded); must log fatal bug and adjust date range.
  - Error `-16` / `401`: Token expired; trigger `AuthenticationExpiredError`.

---

## 4. Multi-Symbol Query Capability
- **Status**: VERIFIED
- **Source**: Fyers API v3 History Endpoint Spec
- **Paraphrase**: The history endpoint accepts exactly ONE symbol string per request (`{"symbol": "NSE:SBIN-EQ", ...}`). Multi-symbol batch queries are not supported on the historical candle endpoint.
- **Design Rule**: Ingestion must iterate symbol by symbol.

---

## 5. Corporate Actions & `cont_flag`
- **Status**: UNVERIFIED (Empirical Behaviour for Equity Splits/Bonuses)
- **Source**: Fyers API Docs mention `cont_flag="1"` returns continuous/adjusted data primarily for derivatives contracts.
- **Hypothesis**: Whether `cont_flag="1"` cleanly adjusts equity splits/bonuses across historical ex-dates is unconfirmed in official equity documentation.
- **Architectural Decision**:
  - Phase 15 specifies a dual-track architecture:
    1. Download raw prices (`cont_flag="0"` or default) and store them in `candles_1m_raw` / `candles_1d_raw`.
    2. Maintain an explicit `corporate_actions` and `adjustment_factors` table sourced from official NSE corporate action feeds.
    3. Expose views `candles_1m_adjusted` and `candles_1d_adjusted` computed via vectorized adjustment factors.
    4. Provide a runtime probe in Phase 09 testing a known split stock (e.g., Tata Steel 10:1 split on 2022-07-28 or IRCTC 5:1 split on 2021-10-28) with `cont_flag=0` vs `cont_flag=1` to compare ratios.

---

## 6. Authentication, Refresh Tokens & PIN
- **Status**: VERIFIED
- **Source**: Fyers Developer OAuth v3 Documentation & API Community
- **Paraphrase**:
  - Access Token: Valid daily until approximately 06:00 AM IST of the next calendar day.
  - Refresh Token: Valid for **15 calendar days**. Generated alongside the access token.
  - Renewal Endpoint: `POST https://api-t1.fyers.in/api/v3/validate-refresh-token`
  - Required Payload: `{"grant_type": "refresh_token", "appIdHash": "<SHA256(app_id + ':' + secret_key)>", "refresh_token": "<token>", "pin": "<user_4digit_pin>"}`.
  - **Critical Rule**: The refresh token itself is static and is NOT extended by calling validate-refresh-token. After 15 days, it expires, requiring a full interactive OAuth browser login.
  - User PIN and tokens must NEVER be stored in plain text `.env`. Use OS keyring (`keyring` Python package) or an AES-256 encrypted local credential vault (`data/.auth_vault.enc`).

---

## 7. Options Module: History vs Forward Collection
- **Status**: VERIFIED
- **Source**: Fyers API v3 Documentation & Community
- **Paraphrase**: Fyers provides NO historical data endpoint for expired options contracts. The Option Chain endpoint (`fyers.optionchain()`) returns real-time snapshot data up to 50 strikes for active expiries.
- **Design Rule**: Phase 16 must implement forward snapshot collection (capturing EOD chain snapshots into DuckDB daily at 15:35 IST) and display a prominent UI banner: "No historical options data available prior to local collection start date".

---

## 8. Symbol Master (`NSE_CM.csv`) Symbology
- **Status**: VERIFIED
- **Source**: Public CDN `https://public.fyers.in/sym_details/NSE_CM.csv` and community specifications
- **Paraphrase**: The CSV contains no header row. Column 3 (0-indexed 2) is instrument type (`0` for Equity). Column 10 (0-indexed 9) contains the canonical Fyers symbology (e.g. `NSE:RELIANCE-EQ`). Column 14 (0-indexed 13) contains the exchange ticker.
