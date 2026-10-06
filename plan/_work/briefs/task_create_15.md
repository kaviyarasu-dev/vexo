# Task Brief: Create 15_CORPORATE_ACTIONS_AND_EXTERNAL_DATA.md

**Target File**: `plan/15_CORPORATE_ACTIONS_AND_EXTERNAL_DATA.md` (ONLY this file may be modified)  
**Allowed Read Set**:
- `plan/00A_CONTRACTS_AND_CONVENTIONS.md`
- `plan/VERIFICATION_REPORT.md`
- `plan/OPEN_QUESTIONS.md`

**Objective**:
Create `15_CORPORATE_ACTIONS_AND_EXTERNAL_DATA.md` specifying the corporate actions engine and external NSE data ingestion:
1. Begin with mandatory EXECUTION CONTRACT block.
2. Formulate Corporate-Action Ingestion & Adjustment Factor Engine:
   - Ingests splits, bonuses, dividends, and rights into `corporate_actions`.
   - Computes cumulative price and volume adjustment factors into `adjustment_factors`.
   - Maintains raw vs adjusted separation via views (`candles_1d_adjusted`, `candles_1m_adjusted`).
   - Idempotent recomputation: recalculating factors when new events occur without re-downloading raw candles.
3. Incorporate the empirical `cont_flag=0` vs `1` verification probe (settling OQ-01).
4. External NSE Data Ingestion:
   - UDiFF Common Bhavcopy (`BhavCopy_NSE_CM_0_0_0_<YYYYMMDD>_F_0000.csv.zip`).
   - Delivery quantity & delivery % feed.
   - FII/DII daily net activity feed.
   - Bulk and Block deals feed.
   - Index constituents CSV feeds.
5. Governance, Politeness & Scraping Risk:
   - Realistic User-Agent, cookie session initialization, throttling ($\le 1$ req / 3 sec).
   - Local manual override fallbacks for every external source.
   - Source freshness indicators in UI.
6. Align interface: `ICorporateActionRepository`.
7. Keep file under 400 lines.
