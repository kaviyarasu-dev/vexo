# Task Brief: Create 12_SCREENER_ENGINE.md

**Target File**: `plan/12_SCREENER_ENGINE.md` (ONLY this file may be modified)  
**Allowed Read Set**:
- `plan/00A_CONTRACTS_AND_CONVENTIONS.md`
- `plan/VERIFICATION_REPORT.md`
- `plan/OPEN_QUESTIONS.md`

**Objective**:
Create `12_SCREENER_ENGINE.md` specifying the institutional multi-factor screener engine:
1. Begin with mandatory EXECUTION CONTRACT block.
2. Outline User Jobs: "Find stocks meeting technical and volume setups rapidly across the NSE universe."
3. Filter Builder Specification:
   - Technical filters (Moving Average crosses, RSI thresholds, VWAP distance, 52-week High/Low, Bollinger Band %B).
   - Volume & liquidity filters (Average Daily Turnover > ₹50 Cr, Volume Z-Score > 2.0).
   - Fundamental metrics handling (settling OQ-06): name source (local CSV import `data/fundamentals_latest.csv` or Bhavcopy delivery %); behaviour if absent (filter chips disabled with tooltip; system operates cleanly on technical/volume metrics).
4. Pre-built 1-Click Templates:
   - "Volume Surge Alert" (Volume Z-Score > 2.0).
   - "52-Week High Breakout" (Close within 2% of 52-week high).
   - "RSI Oversold Bounce" (Daily RSI < 30).
5. Workflow Integration:
   - One-click row click jumps directly to interactive chart.
   - One-click export of filtered table to CSV / Parquet.
6. Execution Rules:
   - "As of" date parameter (supports historical scans).
   - Adjusted prices rule: technical calculations execute against adjusted views.
   - Performance budget: Full Nifty 500 scan executes in $< 2.0\text{ seconds}$.
7. Interface: `IScreenerService`.
8. Keep file under 400 lines.
