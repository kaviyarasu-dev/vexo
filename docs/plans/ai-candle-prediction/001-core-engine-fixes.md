# Plan 001: Core Calculation & Mathematical Bug Remediation

## Goal
Resolve critical calculation flaws in the active codebase:
1. Eliminate double-slippage deduction in backtest trade execution.
2. Fix Cartesian join duplication in DuckDB dynamic corporate actions split-adjusted views.
3. Standardize Black-Scholes Greeks time-scale annualization ($T = t / 250.0$) and add dividend yield ($q$).

## Read first
- `trading-app/services/backtest/cost_model.py`
- `trading-app/services/backtest/engine.py`
- `trading-app/db/migrations.py`
- `trading-app/services/options/greeks_engine.py`

## Steps

### Step 1: Create verification test suite for core calculations
Create `tests/unit/test_core_engine_fixes.py` with test fixtures covering:
- Single slippage deduction verification (verifying that `cost_model.compute_fees()` does NOT include slippage in `total_taxes_and_fees`).
- Multi-split candle row integrity verification on split stocks (verifying that `candles_1d_adjusted` returns strictly $1:1$ rows matching `candles_1d_raw`).
- BSM Greeks time-scale verification (verifying that daily Theta matches $250$ trading days convention and incorporates dividend yield $q$).

### Step 2: Fix double-slippage in cost model and backtest engine
- In `services/backtest/cost_model.py`, remove `slippage` from `CostResult.total_taxes_and_fees`.
- Ensure `self.slippage_bps` remains recorded in `CostResult.slippage` for reporting, but is not added to the cash statutory fee sum.
- In `services/backtest/engine.py`, verify that `fill_price = open_price * (1 \pm \text{slippage_factor})` is the sole mechanism through which slippage impacts portfolio cash balance.

### Step 3: Redesign corporate actions adjusted views to eliminate Cartesian product
- In `db/migrations.py`, redesign the view definitions `candles_1d_adjusted` and `candles_1m_adjusted`.
- Implement non-overlapping interval joins on `adjustment_factors` so that each candle matches at most one cumulative factor row.
- Ensure that for equities with multiple corporate actions (e.g. INFY, RELIANCE), queries on adjusted views return strictly the same row count as raw candle tables.

### Step 4: Standardize options Greeks engine time scale and dividend yield
- In `services/options/greeks_engine.py`, update `T = t_days / 250.0` (trading days convention) consistent with `theta = theta / 250.0`.
- Add optional `dividend_yield: float = 0.0` to `calculate()` method signature.
- Update $d_1$ calculation: $d_1 = \frac{\ln(S/K) + (r - q + \sigma^2/2)T}{\sigma\sqrt{T}}$.
- Update Call/Put Delta and Theta formulas to discount spot price by $e^{-qT}$.

## Do not touch
- `trading-app/core/security.py`
- `trading-app/api/routers/auth.py`
- `trading-app/data/db/nse_quant.duckdb`

## Acceptance
Run:
```bash
.\.venv\Scripts\pytest.exe tests/unit/test_core_engine_fixes.py
```
All tests must pass with exit code 0.

## If blocked
Write exact error trace, failing assertions, and attempted fixes to `docs/plans/ai-candle-prediction/BLOCKED.md` and stop.

## Report back
Provide test execution output confirming zero double-slippage, strictly unique $1:1$ adjusted candle rows, and calibrated Black-Scholes Greeks.
