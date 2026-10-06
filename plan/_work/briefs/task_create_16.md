# Task Brief: Create 16_OPTIONS_MODULE.md

**Target File**: `plan/16_OPTIONS_MODULE.md` (ONLY this file may be modified)  
**Allowed Read Set**:
- `plan/00A_CONTRACTS_AND_CONVENTIONS.md`
- `plan/VERIFICATION_REPORT.md`

**Objective**:
Create `16_OPTIONS_MODULE.md` specifying the options analytics, forward chain collector, and Greeks engine:
1. Begin with mandatory EXECUTION CONTRACT block.
2. Outline User Jobs: "Analyze options open interest, implied volatility, Greeks, and construct multi-leg payoff diagrams."
3. Forward Snapshot Collection Architecture:
   - Verified constraint: Fyers provides no historical data for expired options contracts.
   - Daily collector runs at 15:35 IST capturing EOD chain snapshots into `option_chain_snapshots`.
   - Mandatory UI banner: "No historical options data available prior to local collection start date."
   - Missed-day gap handling: records calendar gap, never forward-fills fake Greeks or open interest.
4. Quantitative Options Metrics:
   - Open Interest (OI) & $\Delta \text{OI}$ analysis.
   - Put-Call Ratio (PCR) by Volume and OI.
   - Max Pain algorithm with mathematical formulation.
5. Options Greeks Engine:
   - Black-76 / Black-Scholes pricing model.
   - Verified inputs: Spot, Strike, Fractional year time to expiry, Implied Volatility, Risk-free rate (RBI T-Bill / Repo rate, configurable default 6.5%).
   - Analytical Greeks: Delta, Gamma, Theta, Vega.
6. Interactive Multi-Leg Payoff Builder.
7. RateGovernor Integration:
   - Uses `fyers.optionchain()` capped at 50 strikes.
   - EOD snapshot runs in Lane 2; interactive UI queries run in Lane 1.
8. Keep file under 400 lines.
