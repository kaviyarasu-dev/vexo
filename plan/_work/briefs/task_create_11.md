# Task Brief: Create 11_PERSONAS_AND_SIMPLE_PRO_UX.md

**Target File**: `plan/11_PERSONAS_AND_SIMPLE_PRO_UX.md` (ONLY this file may be modified)  
**Allowed Read Set**:
- `plan/00A_CONTRACTS_AND_CONVENTIONS.md`
- `plan/VERIFICATION_REPORT.md`

**Objective**:
Create `11_PERSONAS_AND_SIMPLE_PRO_UX.md` defining user personas, UX modes, and user journeys:
1. Begin with mandatory EXECUTION CONTRACT block.
2. Define the two primary personas and user jobs:
   - **Persona A (Retail Beginner)**: Needs plain-language guidance, curated templates, zero jargon, risk-first alerts, and one-click workflows. Job: "Help me find and understand good Indian stocks without confusing me."
   - **Persona B (Quant / Systematic Trader)**: Needs raw time-series data, high-performance screener, Python/Parquet exports, realistic Indian-cost backtests, and multi-factor parameters. Job: "Give me fast, uncorrupted data and rigorous backtesting on my local machine."
3. Simple Mode vs Pro Mode UI specification:
   - Mode switching mechanism (persistent client preference).
   - Component visibility matrix (what is shown / hidden in each mode).
   - Plain-language translation dictionary (e.g. VWAP $\rightarrow$ "Intraday Average Price").
4. Measurable UX performance targets:
   - Time-to-first-chart for a beginner: $< 5\text{ seconds}$ from app launch.
   - Clicks-to-first-scan: $\le 2\text{ clicks}$ from home screen.
5. Onboarding flow: interactive walkthrough and sample guided scan.
6. Keep file under 400 lines.
