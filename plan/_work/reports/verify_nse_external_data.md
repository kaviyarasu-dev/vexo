# Verification Report: NSE & External Data Feeds

**Research Topic**: NSE Data (UDiFF Bhavcopy, Delivery %, Corporate Actions, Index CSVs, Holidays, Terms of Use)  
**Date of Research**: 2026-10-05  
**Reviewer/Researcher**: Stage A Quant Architect Researcher  

---

## 1. UDiFF Common Bhavcopy Pattern
- **Status**: VERIFIED
- **Source**: NSE Official Notice on Unified Distilled File Formats (UDiFF) & Archives (`https://www.nseindia.com/all-reports`)
- **Paraphrase**:
  - In mid-2024, NSE deprecated legacy bhavcopy filenames (`cmDDMMMYYYYbhav.csv.zip`) and standardized on UDiFF.
  - Active URL Pattern for Capital Market (Cash Equity):
    `https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_<YYYYMMDD>_F_0000.csv.zip`
  - Archive contains standardized columns: `TckrSymb`, `SctySrs`, `OpnPric`, `HghPric`, `LwPric`, `ClsPric`, `TtlTradgVol`, `TtlTrfVal`, `ISIN`, etc.

---

## 2. Delivery Data & Security-wise Trade Volumes
- **Status**: VERIFIED
- **Source**: NSE Archives (`https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_<DDMMYYYY>.csv`)
- **Paraphrase**: Security-wise delivery quantity and delivery percentage are published daily post-market (~18:00 IST).

---

## 3. Index Constituents CSVs
- **Status**: VERIFIED
- **Source**: NSE Indices Official Downloads (`https://www.niftyindices.com/` & `https://nsearchives.nseindia.com/content/indices/`)
- **Paraphrase**:
  - Official index constituent CSV URLs:
    - Nifty 50: `https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv`
    - Nifty Next 50: `https://nsearchives.nseindia.com/content/indices/ind_niftynext50list.csv`
    - Nifty Midcap 150: `https://nsearchives.nseindia.com/content/indices/ind_niftymidcap150list.csv`
    - Nifty Smallcap 250: `https://nsearchives.nseindia.com/content/indices/ind_niftysmallcap250list.csv`
    - Nifty 500: `https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv`
- **Arithmetic Verification**:
  - Nifty 100 = Nifty 50 (50) + Nifty Next 50 (50) = 100 stocks.
  - Nifty Midcap 150 = 150 stocks.
  - Nifty Smallcap 250 = 250 stocks.
  - Nifty 500 = $100 + 150 + 250 = 500\text{ stocks}$.
  - Therefore, the tier hierarchy in Phase 03 is:
    - Tier 1: Nifty 50 + Nifty Next 50 (100 stocks).
    - Tier 2: Nifty Midcap 150 (150 stocks).
    - Tier 3: Nifty Smallcap 250 (250 stocks).
    - Total Tiers 1-3 = Exactly Nifty 500 (500 stocks).
    - Tier 4: Remaining non-Nifty-500 NSE equities (~1,500+ stocks).
  - This eliminates the contradictory "remaining Nifty 500 constituents" error in the old plan 03.

---

## 4. Market Holidays Feed
- **Status**: VERIFIED
- **Source**: NSE API & Official Circulars (`https://www.nseindia.com/api/holiday-master?type=trading`)
- **Paraphrase**: Holiday list is fetched via an automated script (`scripts/fetch_nse_holidays.py`) with a local fallback JSON file (`config/holidays/manual_override_holidays.json`). Never hardcode model-memory holiday dates in code or plan documents.

---

## 5. Licensing, Scraping Risks & Politeness
- **Status**: VERIFIED
- **Source**: NSE India Website Terms & Conditions
- **Paraphrase**: Direct automated scraping of `nseindia.com` can lead to IP blocking (Akamai / Cloudflare bot protection).
- **Design Rule**:
  - Any external scraper must use proper HTTP headers (realistic User-Agent, referer session initialization, rate throttling at $\le 1$ req / 3 sec).
  - Provide local manual override/import CSV fallbacks for all external data.
  - Data is strictly for single-user local personal research; commercial redistribution is prohibited.
