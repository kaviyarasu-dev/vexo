# Task Brief: Create 14_BACKTESTING_ENGINE.md

**Target File**: `plan/14_BACKTESTING_ENGINE.md` (ONLY this file may be modified)  
**Allowed Read Set**:
- `plan/00A_CONTRACTS_AND_CONVENTIONS.md`
- `plan/VERIFICATION_REPORT.md`

**Objective**:
Create `14_BACKTESTING_ENGINE.md` specifying the institutional backtesting engine:
1. Begin with mandatory EXECUTION CONTRACT block.
2. Outline User Jobs: "Test algorithmic hypotheses against historical Indian equity data with realistic transaction costs and zero lookahead bias."
3. Dual Strategy Creation:
   - No-code parameter wizard for beginners.
   - Python code-hook sandbox for quant experts with restricted execution environment (`RestrictedPython` / AST parser; no network, no filesystem).
4. Realistic Indian Equity Statutory Cost Model (from VERIFICATION_REPORT.md):
   - Fyers Brokerage (Oct 1, 2024 schedule).
   - STT (Delivery: 0.1% both sides; Intraday: 0.025% sell side).
   - Exchange charges (0.00297%).
   - SEBI fees (₹10/crore).
   - GST (18%).
   - Stamp duty (0.015% delivery buy, 0.003% intraday buy).
   - Configurable slippage model.
5. Anti-Lookahead Enforcement:
   - Signal evaluates on bar $t$ Close; order fills on bar $t+1$ Open.
   - Include a deliberate lookahead test fixture that must trigger a test failure.
6. Quantitative Performance Metrics: CAGR, Sharpe, Sortino, Max Drawdown, Expectancy, Win Rate.
7. Robustness: Walk-Forward Optimization & Monte Carlo simulation.
8. Reproducibility & Governance: Seed + Data-version hash + Mandatory survivorship bias warning.
9. Interface: `IBacktestEngine`.
10. Keep file under 400 lines.
