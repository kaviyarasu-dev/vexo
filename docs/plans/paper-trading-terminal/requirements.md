# Requirements Document: Interactive Paper Trading Terminal & Chart Order Execution Engine

## 1. Executive Summary & Objective
Transform the existing backend `PaperTradingService` and DuckDB virtual account tables into a comprehensive, professional **Paper Trading Terminal & Chart Order Execution Suite** directly accessible from the Web User Interface.

### Finalized Design & Architectural Decisions:
1. **Chart Quick Execution Floating Bar**: Positioned directly on the top-right of the active Chart canvas (TradingView-style `[ 🟢 BUY ₹LTP ] [ Qty ] [ 🔴 SELL ₹LTP ]`), with an expandable drawer for bracket orders (Target & Stop-Loss in ₹ or %).
2. **Collapsible Bottom Positions Dock**: A multi-tab terminal docked below the chart workspace displaying `Positions (N)`, `Orders (N)`, `Fills History (N)`, and `Auto Strategies (N)` with real-time P&L ticker and 1-click square-off.
3. **Capital & Margin Model**: Default virtual starting capital of **₹10,00,000 (10 Lakhs)**. Supports **Delivery (1x cash)** and **Intraday MIS (5x leverage with 15:15 IST compulsory square-off)**. Full Indian statutory taxes and 5 bps slippage deducted per fill.
4. **Chart Visual Overlays**: Render interactive horizontal price lines on the candlestick chart for Entry Price (Blue line), Target/Take-Profit (Green dashed line), and Stop-Loss (Red dashed line) with floating P&L badges and execution arrows.
5. **Backtest Studio Forward Testing**: A prominent **"⚡ Deploy Strategy to Paper Trading"** button in Quant Backtest Studio that forward-tests strategies by registering them in `paper_auto_strategies` and auto-placing simulated orders on candle signal triggers.


---

## 2. User Stories & Core Workflows

### User Story 1: Fast Chart Order Execution
- *As a discretionary or price-action trader*, I want to click a quick `BUY` or `SELL` button floating over the active stock chart, specify quantity (or lot size) and optional Stop-Loss/Target, and have the order immediately fill with realistic slippage and statutory costs.
- *Acceptance Criteria*:
  - Floating widget on top-right of chart: `[ 🟢 BUY ₹LTP ]` | `[ 🔴 SELL ₹LTP ]`.
  - Clicking opens a non-blocking Order Ticket pre-filled with active symbol and current price.
  - Submitting sends `POST /api/v1/paper-trading/orders` and updates the chart within 50ms with an entry line.

### User Story 2: Real-Time Position Management & Square-Off
- *As an active trader*, I want to see all open positions in a bottom dock, watch my live unrealized P&L tick up/down as the price moves, and click "Square Off" to close any position instantly.
- *Acceptance Criteria*:
  - Collapsible terminal at screen bottom with `Positions (N)` and `Orders (N)` tabs.
  - Position row displays: Symbol, Side, Qty, Avg Price, LTP, P&L (₹), P&L (%), Trailing SL, and Action buttons (Square Off, Edit SL/TP).
  - Clicking "Square Off" generates an offsetting SELL (for LONG) or BUY (for SHORT) fill, calculates net P&L after all Indian costs, and removes the position.

### User Story 3: Trailing Stop Loss & Risk Management
- *As a risk-conscious quant*, I want to configure a Trailing Stop-Loss (e.g. 1.5% or 2 * ATR) so that as the price moves in my favor, the stop-loss level trails upward automatically to protect profits.
- *Acceptance Criteria*:
  - Position can have an active `trailing_sl_pct` or fixed `stop_loss_price`.
  - Background tick evaluator or on-candle update recalculates stop-loss and auto-triggers exit if price breaches SL.

### User Story 4: Forward Testing from Backtest Studio
- *As an algorithmic trader*, after backtesting a strategy (e.g. RSI Reversal or Supertrend) and seeing profitable historical metrics, I want to click "Deploy to Paper Trading" to forward-test the strategy in simulated real-time market conditions.
- *Acceptance Criteria*:
  - "⚡ Deploy to Paper Trading" button in Backtest Studio Configurator.
  - Active automated strategies monitor incoming candle closes and execute simulated orders automatically into the Paper Trading account.

---

## 3. UI/UX Component Specifications

1. **Top Navigation / Toolbar Integration:**
   - Add Paper Account balance pill to header or Pro toolbar: `💼 Virtual: ₹10,00,000 | P&L: +₹0.00`.
   - Clicking opens the Paper Account modal with deposit/reset options.
2. **Chart Quick Execution Floating Bar (`.chart-quick-trade-bar`):**
   - Floating at top-right or top-center of the chart canvas:
     - `BUY` button (Green `#089981`)
     - Quantity stepper `[ - ] 50 [ + ]`
     - `SELL` button (Red `#F23645`)
     - Expand button `⚙️` for advanced bracket order ticket (SL/TP in ₹ or %).
3. **Bottom Paper Trading Terminal Dock (`#paper-trading-dock`):**
   - Collapsible dock docked below the chart / subpanes with tabs:
     - `Positions (N)`
     - `Orders (N)`
     - `Trade History (N)`
     - `Account Summary`
   - Controls: Minimize `▼`, Maximize `▲`, Reset Account `🔄`.
4. **Chart Visual Markers:**
   - Green arrow marker on the execution candle for BUY fill.
   - Red arrow marker on the execution candle for SELL fill.
   - Horizontal ray for Entry Price, TP Price (Green dashed), and SL Price (Red dashed).

---

## 4. Technical & Database Architecture

1. **DuckDB Tables (Expanding existing schema):**
   - `paper_account`: `account_id`, `balance`, `initial_balance`, `realized_pnl`, `updated_at`.
   - `paper_positions`: `position_id`, `symbol`, `side`, `quantity`, `average_price`, `stop_loss`, `take_profit`, `trailing_sl_pct`, `highest_price`, `lowest_price`, `created_at`, `updated_at`.
   - `paper_orders`: `order_id`, `symbol`, `side`, `order_type`, `quantity`, `price`, `trigger_price`, `status`, `stop_loss`, `take_profit`, `created_at`, `filled_at`.
   - `paper_trades`: `trade_id`, `order_id`, `symbol`, `side`, `quantity`, `fill_price`, `brokerage`, `stt`, `taxes_and_charges`, `net_pnl`, `executed_at`.
   - `paper_auto_strategies`: `strategy_id`, `strategy_name`, `symbol`, `timeframe`, `parameters`, `status`, `created_at`.
2. **FastAPI Endpoints (`api/routers/paper_trading.py`):**
   - `GET /api/v1/paper-trading/account` -> Account balance, margin, realized P&L.
   - `POST /api/v1/paper-trading/account/reset` -> Reset balance to ₹10,00,000.
   - `GET /api/v1/paper-trading/positions` -> List active open positions with live LTP and unrealized P&L.
   - `POST /api/v1/paper-trading/orders` -> Place virtual market, limit, or bracket order.
   - `DELETE /api/v1/paper-trading/positions/{position_id}/close` -> 1-click square-off position at current market price.
   - `PUT /api/v1/paper-trading/positions/{position_id}/risk` -> Update SL, TP, or Trailing SL.
   - `GET /api/v1/paper-trading/orders` -> List active and past orders.
   - `GET /api/v1/paper-trading/history` -> List closed trade fills ledger with tax breakdown.
   - `POST /api/v1/paper-trading/deploy-strategy` -> Deploy backtested strategy for automated forward testing.
3. **Execution Engine & Pricing:**
   - Consume latest candle close/LTP from `candles_1d_adjusted` or `candles_1m_adjusted`.
   - Apply Phase 14 `IndianEquityCostModel` (STT, Stamp Duty, GST, Exchange turnover, SEBI fee, Brokerage).
   - Apply 5 bps realistic slippage (Buy fills at `LTP * 1.0005`, Sell fills at `LTP * 0.9995`).
