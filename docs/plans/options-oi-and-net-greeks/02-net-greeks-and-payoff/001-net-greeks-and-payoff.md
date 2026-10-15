# Plan 02-001: Strategy Net Greeks Aggregator & Pre-Expiration Black-Scholes Payoff Engine

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "01-001"
  reads:
    - "services/options/greeks_engine.py"
    - "services/options/oi_engine.py"
    - "api/models/options_models.py"
    - "api/routers/options.py"
  produces:
    - "services/options/strategy_greeks_service.py"
    - "services/options/payoff_simulator.py"
    - "tests/unit/test_options_strategy_greeks.py"
    - "tests/integration/test_options_payoff_api.py"
  exposes:
    - "services.options.strategy_greeks_service.StrategyGreeksAggregator"
    - "services.options.payoff_simulator.PreExpiryPayoffSimulator"
    - "POST /api/v1/options/strategy/greeks"
    - "POST /api/v1/options/strategy/payoff"
  must_not_modify:
    - "core/interfaces.py"
    - "db/connection.py"
  test_plan:
    - "pytest tests/unit/test_options_strategy_greeks.py tests/integration/test_options_payoff_api.py -v"
  definition_of_done:
    - "StrategyGreeksAggregator aggregates Net Delta, Gamma, Theta, and Vega across arbitrary multi-leg options combinations"
    - "Aggregator converts unit Greeks to lot-size adjusted INR rupee risks (₹/point, ₹/calendar day, ₹/1% IV shift)"
    - "PreExpiryPayoffSimulator generates both Expiration hockey-stick curve (T=0) and theoretical Black-Scholes curve at Target Date (T+x)"
    - "Simulator models Implied Volatility shock (±20% IV shift) dynamically warping the theoretical curve"
    - "Breakeven strikes, Max Profit (₹), Max Loss (₹), and Risk-to-Reward ratio calculated accurately"
    - "Endpoints POST /api/v1/options/strategy/greeks and POST /api/v1/options/strategy/payoff pass 100% schema validation"
  failure_modes_and_recovery:
    - "Target date exceeds expiry date -> clamp target days between 0.001 and maximum days to expiration"
    - "Zero IV or negative strike -> sanitize inputs with minimum volatility floor (0.05) and positive strike assertion"
  handoff:
    - "Provides the calculation backend for Strategy Net Greeks HUD and Interactive Pre-Expiry Payoff Simulator UI in Plan 03-001"
```

---

## 1. Goal & Scope / User Jobs Served
Options spread trading requires multi-dimensional risk monitoring. When executing a multi-leg trade (such as a 4-leg Iron Condor or Calendar Spread), a trader needs to know:
1. What is my net directional risk in rupees per point? ($\Delta_{\text{net}} \times \text{Lot Size}$)
2. How much time decay will this position earn or bleed every single night? ($\Theta_{\text{net}} \times \text{Lot Size}$)
3. What happens to my P&L if volatility drops by 3% tomorrow after earnings? (Vega & pre-expiration modeling)
4. Where is my theoretical P&L line today ($T+x$) versus expiration?

This plan builds the mathematical calculation engine and REST endpoints to deliver these quantitative insights.

---

## 2. Architecture & SOLID Principles

- **StrategyGreeksAggregator (`services/options/strategy_greeks_service.py`):**
  - Consumes list of `OptionLeg` models.
  - Queries `FOUniverseRegistry` for standardized underlying lot sizes.
  - Computes net Greek coefficients and INR-denominated sensitivities.
- **PreExpiryPayoffSimulator (`services/options/payoff_simulator.py`):**
  - Evaluates both Expiration P&L (intrinsic value) and pre-expiration theoretical P&L using Black-Scholes formula.
  - Supports dynamic IV shock adjustment ($\sigma_{\text{adjusted}} = \sigma \times (1 + \Delta\text{IV})$) and target days $t_{\text{target}}$.
  - Detects zero-crossings for breakeven points.

---

## 3. Mathematical Specifications

### 3.1 Net Greek Aggregations
For a strategy with $M$ legs:
$$\Delta_{\text{net}} = \sum_{i=1}^{M} w_i \Delta_i, \quad \Gamma_{\text{net}} = \sum_{i=1}^{M} w_i \Gamma_i, \quad \Theta_{\text{net}} = \sum_{i=1}^{M} w_i \Theta_i, \quad \mathcal{V}_{\text{net}} = \sum_{i=1}^{M} w_i \mathcal{V}_i$$
where $w_i = +\text{qty}_i$ for `LONG` and $-\text{qty}_i$ for `SHORT`.

### 3.2 Indian Rupee (₹) Conversions
$$\Delta_{\text{INR}} = \Delta_{\text{net}} \times L \quad (\text{₹ per 1 point spot move})$$
$$\Theta_{\text{INR}} = \Theta_{\text{net}} \times L \quad (\text{₹ decay per calendar day})$$
$$\mathcal{V}_{\text{INR}} = \mathcal{V}_{\text{net}} \times L \times 100 \quad (\text{₹ per 1.0\% absolute IV shift})$$
where $L$ is the underlying lot size (e.g. 25 for NIFTY, 15 for BANKNIFTY).

### 3.3 Pre-Expiration Theoretical Pricing ($T+x$)
For spot price candidate $S \in [S_{\min}, S_{\max}]$:
$$\text{Theoretical Premium}_i(S) = \text{BSM}(S, K_i, t_{\text{target}}, \sigma_i \times (1 + \text{IV}_{\text{shock}}), r, \text{type}_i)$$
$$\text{Theoretical P\&L}(S) = \sum_{i=1}^{M} w_i \times (\text{Theoretical Premium}_i(S) - P_i) \times L$$
where $P_i$ is the entry premium paid/received.

$$\text{Expiration P\&L}(S) = \sum_{i=1}^{M} w_i \times (\text{Intrinsic}_i(S) - P_i) \times L$$
where $\text{Intrinsic}_i(S) = \max(0, S - K_i)$ for CE and $\max(0, K_i - S)$ for PE.

---

## 4. API Endpoints & Request/Response Models

### 4.1 `POST /api/v1/options/strategy/greeks`
```json
// Request
{
  "symbol": "NSE:NIFTY50-INDEX",
  "spot": 25050.0,
  "t_days": 4.0,
  "r": 0.065,
  "legs": [
    {"strike": 25000, "option_type": "CE", "position": "LONG", "premium": 140.0, "quantity": 1, "iv": 0.14},
    {"strike": 25200, "option_type": "CE", "position": "SHORT", "premium": 55.0, "quantity": 1, "iv": 0.135}
  ]
}
```
```json
// Response
{
  "symbol": "NSE:NIFTY50-INDEX",
  "lot_size": 25,
  "net_delta": 0.28,
  "net_gamma": 0.00045,
  "net_theta": -4.20,
  "net_vega": 6.80,
  "delta_inr": 7.00,
  "theta_inr": -105.00,
  "vega_inr": 170.00,
  "net_premium": -85.00,
  "total_cost_inr": -2125.00
}
```

### 4.2 `POST /api/v1/options/strategy/payoff`
```json
// Request
{
  "symbol": "NSE:NIFTY50-INDEX",
  "spot": 25050.0,
  "t_days_remaining": 4.0,
  "target_days": 2.0,
  "iv_shock_pct": 0.0,
  "r": 0.065,
  "legs": [
    {"strike": 25000, "option_type": "CE", "position": "LONG", "premium": 140.0, "quantity": 1, "iv": 0.14},
    {"strike": 25200, "option_type": "CE", "position": "SHORT", "premium": 55.0, "quantity": 1, "iv": 0.135}
  ]
}
```
```json
// Response
{
  "symbol": "NSE:NIFTY50-INDEX",
  "lot_size": 25,
  "spot": 25050.0,
  "max_profit": 2875.0,
  "max_loss": -2125.0,
  "risk_reward_ratio": 1.35,
  "breakevens": [25085.0],
  "net_debit_credit_inr": -2125.0,
  "expiration_curve": [{"spot": 24800, "pnl": -2125.0}, ...],
  "target_date_curve": [{"spot": 24800, "pnl": -1650.0}, ...]
}
```

---

## 5. Implementation Steps
1. Create `services/options/strategy_greeks_service.py` implementing `StrategyGreeksAggregator`.
2. Create `services/options/payoff_simulator.py` implementing `PreExpiryPayoffSimulator`.
3. Add Pydantic schemas in `api/models/options_models.py` (`StrategyGreeksRequest`, `StrategyGreeksResponse`, `PayoffSimulationRequest`, `PayoffSimulationResponse`).
4. Mount `POST /api/v1/options/strategy/greeks` and `POST /api/v1/options/strategy/payoff` in `api/routers/options.py`.
5. Author unit tests `tests/unit/test_options_strategy_greeks.py`.
6. Author integration tests `tests/integration/test_options_payoff_api.py`.

---

## 6. Verification & Acceptance Criteria
- `pytest tests/unit/test_options_strategy_greeks.py tests/integration/test_options_payoff_api.py -v` passes 100%.
- Bull Call Spread, Iron Condor, and Straddle test cases verify exact Greek aggregations and Breakeven calculations.
- Execution completes in $< 20$ms per payoff evaluation.
