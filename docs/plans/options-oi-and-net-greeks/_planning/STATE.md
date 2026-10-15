# Feature Plan State: Options Open Interest (ΔOI) Analytics, Strategy Net Greeks & Pre-Expiry Payoff Simulator

- **Slug**: `options-oi-and-net-greeks`
- **Feature Name**: Options Open Interest (ΔOI) Analytics, Strategy Net Greeks & Pre-Expiry Payoff Simulator
- **Status**: REQUIREMENTS DEFINED & PLANS CREATED
- **Parent Initiative**: Institutional Quantitative Trader Roadmap (Priority Tier P1)
- **Manifest**: `docs/plans/options-oi-and-net-greeks/manifest.json`

## Milestones & Plans
1. [DONE] Requirements Definition & User Alignment (/grill-me)
2. [DONE] Architecture & Mathematical Design Specification
3. [DONE] Plan Files & Manifest Creation (`docs/plans/options-oi-and-net-greeks/manifest.json`)
4. [DONE] Plan 01-001: Options Open Interest (ΔOI) Calculation Engine, Support/Resistance & REST Router
   - Task File: `01-oi-engine-and-api/001-oi-engine-and-api.md`
   - Gate: true
   - Verify: `pytest tests/unit/test_options_oi_engine.py tests/integration/test_options_oi_api.py -v` (PASSED: 9/9 tests)
5. [DONE] Plan 02-001: Strategy Net Greeks Aggregator & Pre-Expiration Black-Scholes Payoff Engine
   - Task File: `02-net-greeks-and-payoff/001-net-greeks-and-payoff.md`
   - Gate: true
   - Verify: `pytest tests/unit/test_options_strategy_greeks.py tests/integration/test_options_payoff_api.py -v` (PASSED: 9/9 tests)
6. [DONE] Plan 03-001: Options Lab UI: ΔOI Bar Chart, Net Greeks Dashboard & Interactive Pre-Expiry Payoff Simulator
   - Task File: `03-options-lab-ui/001-options-lab-ui.md`
   - Gate: true
   - Verify: `pytest tests/integration/test_options_lab_ui_integration.py -v` (PASSED: 8/8 tests)

## Execution Gate Order
- `01-001` (Core ΔOI calculation, PCR computation, Max Call/Put resistance/support detection & FastAPI endpoints)
- `02-001` (Combined Strategy Net Greeks engine with lot-size INR conversions, Black-Scholes pre-expiry T+x simulation & IV shocks)
- `03-001` (Options Lab UI: Dedicated Open Interest dual-bar chart, persistent Strategy Net Greeks HUD, pre-expiry payoff curve with sliders, and hybrid 180+ F&O symbol search)
