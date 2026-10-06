# Task Brief: Create 17_JOURNAL_AND_PAPER_TRADING.md

**Target File**: `plan/17_JOURNAL_AND_PAPER_TRADING.md` (ONLY this file may be modified)  
**Allowed Read Set**:
- `plan/00A_CONTRACTS_AND_CONVENTIONS.md`
- `plan/14_BACKTESTING_ENGINE.md`
- `plan/VERIFICATION_REPORT.md`

**Objective**:
Create `17_JOURNAL_AND_PAPER_TRADING.md` specifying the quantitative trade journal and paper-trading execution simulator:
1. Begin with mandatory EXECUTION CONTRACT block.
2. Outline User Jobs: "Log, analyze, and review my historical trades; tag psychological mistakes; simulate live trading without risking real capital."
3. Trade Journal Architecture:
   - Manual trade logging and CSV tradebook import.
   - Exact mathematical derivation of R-multiple:
     $$R = \frac{\text{Exit} - \text{Entry}}{\text{Entry} - \text{Stop Loss}}$$
   - Net P&L factoring in statutory Indian costs (reusing Phase 14 `IndianEquityCostModel`).
   - Psychological and rule-execution mistake tagging (FOMO, Revenge Trading, Chased Breakout, Sized Too Big).
   - Equity curve and trade distribution analytics.
4. Paper Trading Execution Simulator:
   - Event-driven paper fills executing over real-time market data or latest candle prints.
   - Enforces realistic limit and market order rules with 5 bps slippage and full statutory Indian taxes.
5. Align interface: `IJournalService`.
6. Keep file under 400 lines.
