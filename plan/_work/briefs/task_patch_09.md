# Task Brief: Patch 09_MILESTONE_1_RELIANCE_VERIFICATION.md

**Target File**: `plan/09_MILESTONE_1_RELIANCE_VERIFICATION.md` (ONLY this file may be modified)  
**Allowed Read Set**:
- `plan/00A_CONTRACTS_AND_CONVENTIONS.md`
- `plan/09_MILESTONE_1_RELIANCE_VERIFICATION.md`
- `plan/VERIFICATION_REPORT.md`
- `plan/OPEN_QUESTIONS.md`

**Objective**:
Upgrade `09_MILESTONE_1_RELIANCE_VERIFICATION.md` to enterprise quant architecture standards:
1. Add mandatory EXECUTION CONTRACT block at top.
2. Add explicit quantitative gates:
   - **Adjustment Correctness Gate**: Automated test on historical split/bonus counter (comparing raw vs adjusted ratios).
   - **Rate-Limit Soak Gate**: 30-minute continuous download soak achieving zero 429 errors and strictly $\le 180\text{ req/min}$.
   - **Timestamp Convention Gate**: Recorded-fixture test verifying intraday epoch starts at 09:15:00 IST (`03:45:00 UTC`) and daily bars align to session dates.
   - **DuckDB PK vs Staging Benchmark Gate**: Synthetic benchmark at 1M, 10M, and 100M rows measuring insertion speed, peak RAM, and query latency for PK vs Staging anti-join deduplication.
   - **Empirical Disk Size Gate**: File size extrapolation derived from real measured bytes per candle ($S_{\text{measured}}$), not hypothetical guesses.
3. Keep file under 400 lines.

**Acceptance Self-Test**:
- Begins with EXECUTION CONTRACT.
- All 5 empirical gates explicitly detailed with measurable pass/fail criteria.
- Benchmark command line and artifact output paths specified.
