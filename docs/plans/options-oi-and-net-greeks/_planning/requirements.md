# Requirements Specification: Options Open Interest (ΔOI) Analytics, Strategy Net Greeks & Pre-Expiry Payoff Simulator

- **Feature Slug**: `options-oi-and-net-greeks`
- **Target Workspaces**: Options Lab (`#view-options`), Options Router (`api/routers/options.py`), Greeks Engine (`services/options/`)
- **Status**: APPROVED (/grill-me aligned)
- **Target Users**: Institutional quantitative traders, F&O intraday scalpers, and positional options spread managers.

---

## 1. Executive Summary & Problem Statement

In Indian derivative markets (NSE Nifty 50, Bank Nifty, and 180+ F&O eligible stocks), quantitative participants rely on two primary edges:
1. **Open Interest (OI) & Daily OI Change ($\Delta\text{OI}$):** Institutional market makers and writing desks signal supply/demand concentration through fresh open interest build-up and unwinding. Absolute OI identifies macro structural walls, but **$\Delta\text{OI}$** reveals the active battleground where market participants are writing or covering contracts today.
2. **Strategy-Level Greek Risk & Pre-Expiration Decay ($T+x$):** When trading multi-leg spreads (Credit/Debit Spreads, Straddles, Strangles, Condors), knowing individual leg Greeks is insufficient. Traders must manage **Net Strategy Greeks** ($\Delta_{\text{net}}, \Gamma_{\text{net}}, \Theta_{\text{net}}, \mathcal{V}_{\text{net}}$) converted into actual Indian Rupee (₹) exposure per point and per day. Furthermore, traders exit before expiration; evaluating the theoretical P&L line **today ($T+x$)** under variable Days-to-Expiry and Implied Volatility ($\pm 20\%$) shocks is essential.

---

## 2. Functional Requirements (FR)

### FR-1: Open Interest (ΔOI) Analytics & Market Sentiment Engine
1. **Strike-by-Strike OI & $\Delta\text{OI}$ Tracking:**
   - For every strike in the option chain, track:
     - `call_oi`: Total Call Open Interest
     - `call_oi_change` ($\Delta\text{Call OI}$): Net change in Call OI today
     - `put_oi`: Total Put Open Interest
     - `put_oi_change` ($\Delta\text{Put OI}$): Net change in Put OI today
2. **Put/Call Ratio (PCR) Metrics:**
   - **Total PCR:** $\text{PCR}_{\text{OI}} = \frac{\sum \text{Put OI}}{\sum \text{Call OI}}$
   - **Change PCR:** $\text{PCR}_{\Delta\text{OI}} = \frac{\sum \max(0, \Delta\text{Put OI})}{\sum \max(0, \Delta\text{Call OI})}$
   - **Market Sentiment Tagging:**
     - $\text{PCR} > 1.25$: Strongly Bullish / Overbought support
     - $0.90 \le \text{PCR} \le 1.25$: Neutral / Range-bound
     - $\text{PCR} < 0.90$: Strongly Bearish / Call writing dominance
3. **Key Structural Levels Identification:**
   - **Major Call Resistance Wall:** Strike with $\max(\text{Call OI})$.
   - **Major Put Support Wall:** Strike with $\max(\text{Put OI})$.
   - **Active Battleground Strikes:** Strikes with highest positive Call $\Delta\text{OI}$ and Put $\Delta\text{OI}$.
   - **Max Pain Strike:** Calculated via cumulative intrinsic payout minimization.

### FR-2: Combined Strategy Net Greeks Engine & INR Currency Conversion
1. **Net Greek Aggregation:**
   - For any arbitrary set of option legs $\{(\text{strike}_i, \text{type}_i, \text{pos}_i, \text{qty}_i)\}$:
     $$\Delta_{\text{net}} = \sum_{i} \text{sign}_i \times \text{qty}_i \times \Delta_i$$
     $$\Gamma_{\text{net}} = \sum_{i} \text{sign}_i \times \text{qty}_i \times \Gamma_i$$
     $$\Theta_{\text{net}} = \sum_{i} \text{sign}_i \times \text{qty}_i \times \Theta_i$$
     $$\mathcal{V}_{\text{net}} = \sum_{i} \text{sign}_i \times \text{qty}_i \times \mathcal{V}_i$$
     where $\text{sign}_i = +1$ for LONG and $-1$ for SHORT.
2. **Lot-Size Adjusted Rupee (₹) Exposures:**
   - Indian options trade in standardized lot sizes (e.g. NIFTY = 25, BANKNIFTY = 15, RELIANCE = 250).
   - **Delta Cash Exposure (₹/point):** $\Delta_{\text{net}} \times \text{Lot Size}$
   - **Gamma Acceleration (₹/point²):** $\Gamma_{\text{net}} \times \text{Lot Size}$
   - **Daily Theta Decay (₹/calendar day):** $\Theta_{\text{net}} \times \text{Lot Size}$
   - **Vega Sensitivity (₹ per 1% IV shift):** $\mathcal{V}_{\text{net}} \times \text{Lot Size} \times 100$

### FR-3: Pre-Expiration Black-Scholes Payoff Simulator & Dynamic Sliders
1. **Dual Payoff Curves:**
   - **Curve 1 (Expiration P&L):** Discrete hockey-stick payoff at expiration $T=0$.
   - **Curve 2 (Target Date $T+x$ Theoretical P&L):** Smooth curve evaluated using Black-Scholes pricing at target days to expiry $t_{\text{target}}$ and shifted IV $\sigma_{\text{shock}}$.
     $$\text{Theoretical Value}_i(S) = \text{BSM}(S, K_i, t_{\text{target}}, \sigma_i \times (1 + \text{IV}_{\text{shock}}), r, \text{type}_i)$$
     $$\text{P\&L}_{\text{theoretical}}(S) = \sum_{i} \text{sign}_i \times \text{qty}_i \times (\text{Theoretical Value}_i(S) - \text{Entry Premium}_i) \times \text{Lot Size}$$
2. **Interactive Simulation Controls:**
   - **Target Date / Days to Expiry Slider:** Range $[0, T_{\text{max}}]$ days.
   - **IV Shock Slider:** Range $[-20\%, +20\%]$ in steps of $1\%$.
3. **Key Spread Metrics:**
   - Max Profit (₹ or Unlimited), Max Loss (₹ or Unlimited), Risk-to-Reward Ratio (e.g. 1:2.4), Lower Breakeven, Upper Breakeven, Net Entry Cost (Debit/Credit).
4. **Expanded Strategy Presets (1-Click Application):**
   - Bull Call Spread, Bull Put Spread, Bear Call Spread, Bear Put Spread, Long Straddle, Short Straddle, Long Strangle, Short Strangle, Iron Condor, Iron Butterfly.

### FR-4: Hybrid Underlying Selector & Discovery
1. **Quick Index Chips:** 1-click pills for `NIFTY`, `BANKNIFTY`, `FINNIFTY`, `MIDCPNIFTY`.
2. **Searchable F&O Autocomplete:** Dynamic search across all 180+ NSE F&O equities loaded from DuckDB symbol master, including lot size badge (e.g. `NSE:RELIANCE-EQ (Lot: 250)`).

---

## 3. Non-Functional Requirements (NFR)

1. **Sub-50ms API Latency:** All mathematical computations (Greeks, Payoff curves, $\Delta\text{OI}$ aggregations) must complete in $< 50$ms.
2. **Zero Lookahead & Strict IST Alignment:** All timestamping, daily snapshot dates, and expirations strictly align with Indian Standard Time (IST).
3. **DuckDB Concurrency Standard:** All database operations strictly use `db.get_read_cursor()` to prevent write lock acquisition.
4. **Resilient Offline Fallback:** If live broker Fyers option chain token is unauthenticated or market is closed, gracefully calculate synthetic realistic $\Delta\text{OI}$ and Black-Scholes Greeks without throwing 500 errors.
5. **60 FPS Client-Side Rendering:** SVG Payoff curves and bar charts must recalculate and re-render within 16ms during slider drags without UI stutter.

---

## 4. Verification & Acceptance Criteria
- Unit tests cover Black-Scholes Net Greeks, Lot size multipliers, pre-expiry payoff formula, and $\Delta\text{OI}$ calculation.
- Integration tests cover `GET /api/v1/options/open-interest`, `POST /api/v1/options/strategy/greeks`, and `POST /api/v1/options/strategy/payoff`.
- Frontend integration test verifies DOM elements for OI charts, Net Greeks HUD, pre-expiry sliders, and hybrid underlying search.
- 100% assertions pass across all newly created test suites with zero regressions.
