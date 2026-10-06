# Phase 16: Options Analytics, Forward Chain Collection & Greeks Engine

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "plan/00_MASTER_ARCHITECTURE.md"
    - "plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md"
    - "plan/04_HISTORICAL_DOWNLOADER_ENGINE.md"
    - "plan/06_DAILY_INCREMENTAL_UPDATE_AND_SCHEDULER.md"
  reads:
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#1-canonical-interface-registry"
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#4-canonical-database-schema-registry"
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#7-global-rategovernor-specification"
    - "plan/VERIFICATION_REPORT.md#27-options-module-history-vs-forward-collection"
  produces:
    - "services/options_service.py"
    - "services/options/greeks_engine.py"
    - "services/options/payoff_calculator.py"
    - "api/v1/options.py"
    - "static/js/options_view.js"
  exposes: []
  must_not_modify:
    - "plan/*"
    - "db/migrations.py"
  test_plan:
    unit_tests: "tests/unit/test_greeks_math.py tests/unit/test_payoff_calculator.py"
    integration_tests: "tests/integration/test_option_chain_collector.py"
    contract_tests: "tests/contract/test_options_api_contract.py"
    fixtures: "tests/fixtures/sample_option_chain.json"
    command: "pytest tests/unit/test_greeks_math.py tests/unit/test_payoff_calculator.py -v"
  definition_of_done:
    - item: 1
      command: "python -c 'from services.options.greeks_engine import BlackScholesGreeks; g = BlackScholesGreeks(); res = g.calculate(spot=2500, strike=2500, t_days=30, iv=0.20, r=0.065, option_type=\"CE\"); assert 0.48 <= res.delta <= 0.55'"
      result: "At-the-money Call option Delta evaluates to ~0.50 with accurate Gamma, Theta, and Vega."
    - item: 2
      command: "python -c 'from services.options.payoff_calculator import PayoffCalculator; p = PayoffCalculator(); res = p.max_pain(strikes=[2400, 2500, 2600], call_oi=[1000, 5000, 2000], put_oi=[3000, 2000, 500]); assert res == 2500'"
      result: "Max Pain algorithm correctly identifies strike price that minimizes aggregate option buyer payout."
    - item: 3
      command: "curl -s http://localhost:8000/api/v1/options/chain?symbol=NSE:NIFTY50-INDEX | jq '.meta.banner'"
      result: "API response includes explicit disclaimer banner: 'No historical options data available prior to local collection start date.'"
  failure_modes_and_recovery:
    - failure: "Fyers Option Chain API returns HTTP 400 when strikecount > 50"
      detection: "Fyers response code -300 or error: strike count exceeds limit"
      recovery: "Clamp requested strike count to 50 strikes centered around current spot price"
    - failure: "Collector misses EOD snapshot due to machine shutdown"
      detection: "Missing snapshot_date record in option_chain_snapshots"
      recovery: "Record gap metadata in audit log; NEVER interpolate fake Greeks or synthetic OI across missing dates"
  handoff:
    - "Options Greeks engine and Max Pain calculator operational."
    - "Daily 15:35 IST option-chain forward snapshot collector wired to scheduler."
    - "Ready for Phase 17 trade journal and paper trading simulator."
```

---

## 1. Goal & User Jobs Served
Establish an options data and quantitative derivatives analytics module providing daily chain snapshots, analytical Greeks, Max Pain, and multi-leg payoff diagrams adhering to the 00A Canonical Registry.

### Core User Jobs:
1. **Analyze (Both Personas)**: "Show me where institutional players are positioned across the Nifty and Reliance option chains (Open Interest, PCR, and Max Pain)."
2. **Analyze (Quant Expert)**: "Compute fair-value implied volatilities, Delta, Gamma, Theta, and Vega using verified risk-free interest rates."
3. **Test (Both Personas)**: "Let me model the payoff curve of a multi-leg spread (e.g. Bull Call Spread or Iron Condor) before entering a trade."

---

## 2. SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `OptionChainCollector`: Responsible solely for fetching real-time option chain snapshots from Fyers and persisting them to DuckDB.
  - `GreeksEngine`: Responsible solely for computing Black-Scholes/Black-76 pricing and analytical partial derivatives.
  - `PayoffCalculator`: Responsible solely for calculating multi-leg profit and loss profiles across varying underlying spot prices.
- **Open/Closed Principle (OCP)**:
  - Greeks models adhere to an `IOptionsPricingModel` contract. Swapping between Black-Scholes, Black-76, or Bjerksund-Stensland (American options) requires creating a model class without altering API controllers.
- **Dependency Inversion Principle (DIP)**:
  - The collector dispatches requests through the centralized `RateGovernor` abstraction.

---

## 3. Forward Snapshot Collection Architecture

### 3.1. Upstream Limitation: No Expired Options History
- **Verified Fact**: Fyers API v3 provides **NO historical tick or candle data for expired options contracts**. Historical data is only provided for active underlying spot equities.
- **System Architecture**:
  1. The platform executes **forward snapshot collection** starting from the date the user installs the application.
  2. Every evening at **15:35:00 IST** (post-market close, prior to daily sync), the scheduler queries the live chain for `NSE:NIFTY50-INDEX` and liquid counters.
  3. Records are persisted in `option_chain_snapshots` table.
  4. **Prominent UI Disclosure**:
     `"Notice: Historical options data is collected forward starting from [Date]. Fyers API does not provide retrospective expired options contracts."`

### 3.2. Missed-Day Gap Handling
If the host system is powered off during the 15:35 IST snapshot window:
- The system logs a calendar gap in `job_logs`.
- **Integrity Rule**: The engine **NEVER interpolates or forward-fills** fake Open Interest or Greeks across missing days. Gaps are explicitly indicated as missing points on OI historical charts.

---

## 4. Quantitative Options Metrics & Mathematics

### 4.1. Open Interest (OI) & Put-Call Ratio (PCR)
- **PCR by Open Interest**:
  $$\text{PCR}_{\text{OI}} = \frac{\sum \text{Put OI}}{\sum \text{Call OI}}$$
- **PCR by Volume**:
  $$\text{PCR}_{\text{Volume}} = \frac{\sum \text{Put Volume}}{\sum \text{Call Volume}}$$
- Standard interpretation: $\text{PCR} > 1.2$ indicates bullish sentiment (heavy put writing); $\text{PCR} < 0.7$ indicates bearish/overheated call buying.

### 4.2. Max Pain Algorithm
The strike price at which option writers incur the least cumulative financial loss:
$$\text{Total Payout}(S) = \sum_{K \le S} \text{Call OI}_K \times (S - K) + \sum_{K \ge S} \text{Put OI}_K \times (K - S)$$
$$\text{Max Pain Strike} = \arg\min_{S} \text{Total Payout}(S)$$

---

## 5. Analytical Options Greeks Engine

### 5.1. Mathematical Formulation (Black-Scholes & Black-76)
- **Model Inputs**:
  - Underlying Spot Price ($S$).
  - Strike Price ($K$).
  - Annualized Time to Expiry ($T = \text{Trading Days Remaining} / 250$).
  - Risk-Free Rate ($r = 0.065$, based on official RBI 91-day Treasury Bill yield).
  - Implied Volatility ($\sigma$).
- **Formulas**:
  $$d_1 = \frac{\ln(S / K) + (r + \sigma^2 / 2)T}{\sigma \sqrt{T}}, \quad d_2 = d_1 - \sigma \sqrt{T}$$
  $$\text{Delta}_{\text{Call}} = N(d_1), \quad \text{Delta}_{\text{Put}} = N(d_1) - 1$$
  $$\text{Gamma} = \frac{N'(d_1)}{S \sigma \sqrt{T}}$$
  $$\text{Theta}_{\text{Call}} = -\frac{S N'(d_1) \sigma}{2 \sqrt{T}} - r K e^{-rT} N(d_2)$$
  $$\text{Vega} = S \sqrt{T} N'(d_1)$$

---

## 6. Multi-Leg Payoff Builder

Supports interactive visualization of user-constructed option strategies:
- **Preset Strategies**: Long Call/Put, Bull Call Spread, Bear Put Spread, Straddle, Strangle, Iron Condor.
- Computes: Maximum Profit, Maximum Risk, Breakeven Strike Prices, and Risk-to-Reward Ratio.
- Payoff Curve: Plots net P&L across a $\pm 10\%$ spot price envelope at expiry ($T=0$) and current date ($T=t$).

```
      P&L (₹)
        ▲
+₹5,000 │           ┌─────────── Max Profit
        │          /
    ₹0 ─┼─────────/───────────── Breakeven: ₹2,520
        │        /
-₹2,000 │───────┘               Max Risk (Net Premium Paid)
        └──────────────────────► Spot Price (₹)
```

---

## 7. RateGovernor Integration

- Fyers Option Chain endpoint:
  `fyers.optionchain({"symbol": "NSE:NIFTY50-INDEX", "strikecount": 20})`
- **Constraint**: Strike count parameter is capped at **maximum 50 strikes** (25 OTM + 25 ITM).
- **Priority Routing**:
  - EOD scheduled snapshot (15:35 IST): dispatches via **Lane 2 (Medium)**.
  - Interactive UI option-chain viewer: dispatches via **Lane 1 (High)**.
  - Total overhead: $< 5\text{ calls / day}$, negligible impact on rate budget.

---

## 8. Implementation Steps
1. Create `services/options/greeks_engine.py` implementing analytical Black-Scholes equations for Delta, Gamma, Theta, Vega, and numerical Newton-Raphson IV solver.
2. Create `services/options/payoff_calculator.py` computing Max Pain, PCR, and multi-leg P&L matrices.
3. Create `services/options_service.py` managing EOD chain snapshot ingestion into `option_chain_snapshots`.
4. Create `api/v1/options.py` exposing REST endpoints for option chain, Greeks, and payoff curves.
5. Create `static/js/options_view.js` rendering OI bar charts, PCR gauge, and interactive Canvas payoff curves.

---

## 9. Verification & Acceptance Criteria
- Greeks math matches known options benchmark: ATM Call option with $S=2500, K=2500, T=30\text{d}, \sigma=0.20, r=0.065$ produces Delta between $0.48$ and $0.55$.
- Max Pain algorithm correctly identifies the minimum payout strike across sample OI distribution.
- Scheduled snapshot at 15:35 IST inserts active chain strikes into `option_chain_snapshots` in $< 350\text{ ms}$.
- UI displays the mandatory disclaimer banner indicating forward collection policy.
- Interactive payoff curve accurately plots Bull Call Spread with capped upside and defined risk.
