# Report: Create 15_CORPORATE_ACTIONS_AND_EXTERNAL_DATA.md

**Status**: Done  
**File Written**: `plan/15_CORPORATE_ACTIONS_AND_EXTERNAL_DATA.md`  
**Open Questions Count**: 0  

### Summary of Changes
- Created `15_CORPORATE_ACTIONS_AND_EXTERNAL_DATA.md` with complete EXECUTION CONTRACT block.
- Detailed corporate-action adjustment engine: cumulative price and volume multipliers stored in `adjustment_factors` and applied dynamically via SQL views (`candles_1d_adjusted`, `candles_1m_adjusted`).
- Solved the recomputation problem: new corporate actions recompute factors in $< 15$ ms without re-downloading raw candles.
- Formulated external NSE data ingestion: UDiFF Common Bhavcopy, delivery quantity and percentage, FII/DII net flows, bulk/block deals.
- Detailed scraping governance, cookie bootstrap, politeness rate limit ($\le 1$ req / 3s), and local fallback imports.
- Aligned interface with `ICorporateActionRepository`.
