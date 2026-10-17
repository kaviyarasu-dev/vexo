# Plan 005: Dynamic Bayesian Pattern Edge & Deflated Sharpe Ratio (DSR)

## Goal
Eliminate deceptive metrics and protect traders against data mining overfitting:
1. Replace static hardcoded candlestick pattern accuracy numbers in `services/pattern_recognition_service.py` with dynamic Bayesian empirical win rates queried from DuckDB.
2. Implement Marcos López de Prado's Deflated Sharpe Ratio (DSR) in `services/backtest/robustness.py`, adjusting for non-normality (skewness, kurtosis) and multiple-testing selection bias.
3. Integrate an Amber Overfitting Alert banner in Backtest Lab when a strategy fails the DSR significance test ($p > 0.05$).

## Read first
- `trading-app/services/pattern_recognition_service.py`
- `trading-app/services/backtest/engine.py`
- `trading-app/static/js/backtest_ui.js`
- `trading-app/static/js/chart_patterns.js`

## Steps

### Step 1: Refactor pattern recognition engine with dynamic Bayesian win rates
- In `services/pattern_recognition_service.py`, remove the static dictionary accuracy percentages across all 12 candlestick patterns.
- Implement `compute_empirical_win_rate(db_cursor, pattern_id, symbol, timeframe, regime)`:
  - Queries historical occurrences of the pattern in DuckDB.
  - Applies Bayesian Beta prior: $P(\text{Win}) = \frac{\alpha_0 + \text{Wins}}{\alpha_0 + \beta_0 + N}$, where $\alpha_0=1, \beta_0=1$.
  - Returns empirical win rate, sample size $N$, and expected value in ₹.
- Update marker payload so tooltips render dynamic empirical statistics.

### Step 2: Implement Deflated Sharpe Ratio in backtest robustness module
- Create `services/backtest/robustness.py`.
- Implement `calculate_deflated_sharpe_ratio(returns_series, num_trials, benchmark_sharpe=0.0)`:
  - Computes sample Sharpe ratio $\widehat{\text{SR}}$, annualized return, variance, skewness $\hat{\gamma}_3$, and kurtosis $\hat{\gamma}_4$.
  - Computes the expected maximum Sharpe ratio under null hypothesis of zero alpha:
    $$\mathbb{E}[\max_{N} \text{SR}] \approx (1 - \gamma)\Phi^{-1}\left(1 - \frac{1}{N}\right) + \gamma \Phi^{-1}\left(1 - \frac{1}{Ne}\right)$$
  - Computes DSR statistic and asymptotic $p$-value:
    $$\text{DSR} = \Phi\left( \frac{(\widehat{\text{SR}} - \text{SR}^*) \sqrt{T-1}}{\sqrt{1 - \hat{\gamma}_3 \widehat{\text{SR}} + \frac{\hat{\gamma}_4 - 1}{4}\widehat{\text{SR}}^2}} \right)$$
  - Returns `{raw_sharpe, deflated_sharpe, p_value, is_overfitted}`.

### Step 3: Integrate DSR reporting and Amber Overfitting Alert in UI
- In `api/routers/backtest.py`, include `dsr` object in backtest execution results payload.
- In `static/js/backtest_ui.js`, add DSR KPI card beside standard Sharpe/Sortino ratios.
- If `p_value > 0.05`, display prominent Amber Alert badge: `⚠️ High Risk of Overfitting: DSR p-value = 0.24 (Strategy fails multiple testing significance test)`.

### Step 4: Write and verify unit test suites
- Create `tests/unit/test_pattern_edge.py`: verifies that empirical pattern queries run without error in $< 20\text{ms}$ and return calibrated probabilities.
- Create `tests/unit/test_dsr.py`: verifies DSR calculation against synthetic Gaussian returns and asserts that overfitted strategies (high $N$, zero true alpha) produce $p > 0.05$.

## Do not touch
- `trading-app/core/security.py`
- `trading-app/services/options/greeks_engine.py`

## Acceptance
Run:
```bash
.\.venv\Scripts\pytest.exe tests/unit/test_pattern_edge.py tests/unit/test_dsr.py
```
Pattern edge and DSR tests must pass with exit code 0.

## If blocked
Write exact error trace, failing assertions, and attempted fixes to `docs/plans/ai-candle-prediction/BLOCKED.md` and stop.

## Report back
Provide test execution output confirming dynamic Bayesian pattern accuracy queries and DSR statistical calculations.
