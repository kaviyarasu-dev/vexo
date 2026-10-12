# Plan 01-001: Paper Trading Database Engine, Order Management & FastAPI Router

```yaml
EXECUTION_CONTRACT:
  depends_on: []
  reads:
    - "services/paper_trading_service.py"
    - "services/backtest/cost_model.py"
    - "db/connection.py"
    - "db/migrations.py"
    - "api/models/"
  produces:
    - "services/paper_trading_service.py"
    - "api/routers/paper_trading.py"
    - "api/models/paper_trading_models.py"
    - "tests/unit/test_paper_trading_engine.py"
    - "tests/integration/test_paper_trading_api.py"
  exposes:
    - "GET /api/v1/paper-trading/account"
    - "POST /api/v1/paper-trading/account/reset"
    - "GET /api/v1/paper-trading/positions"
    - "POST /api/v1/paper-trading/orders"
    - "DELETE /api/v1/paper-trading/positions/{position_id}/close"
    - "PUT /api/v1/paper-trading/positions/{position_id}/risk"
    - "GET /api/v1/paper-trading/orders"
    - "GET /api/v1/paper-trading/history"
    - "POST /api/v1/paper-trading/deploy-strategy"
    - "GET /api/v1/paper-trading/auto-strategies"
  must_not_modify:
    - "core/interfaces.py"
    - "services/downloader_service.py"
    - "services/resampling_service.py"
  test_plan:
    - "pytest tests/unit/test_paper_trading_engine.py -v"
    - "pytest tests/integration/test_paper_trading_api.py -v"
  definition_of_done:
    - "DuckDB migration idempotently initializes paper_account, paper_positions, paper_orders, paper_trades, and paper_auto_strategies tables"
    - "Order placement correctly handles MARKET and LIMIT orders with BUY/SELL side and Intraday vs Delivery margin rules"
    - "Statutory taxes (STT, Stamp Duty, GST, Exchange turnover, SEBI fee, Brokerage) and 5 bps slippage deducted on each fill leg"
    - "Closing a position calculates exact gross/net P&L and updates account cash and realized_pnl"
    - "All 10 REST endpoints respond with standardized envelope within <30ms"
    - "Unit and integration tests pass with 100% coverage"
  failure_modes_and_recovery:
    - "DuckDB write lock conflict -> retry batch write via db.execute_write_batch()"
    - "Insufficient virtual capital -> return HTTP 400 with detail='Insufficient virtual balance for order value and margin requirements'"
  handoff:
    - "Provides backend data feeds and mutation endpoints for Plan 02 (Chart Overlays) and Plan 03 (Positions Terminal Dock)"
```

---

## 1. Goal & Scope / User Jobs Served
Provide a robust, multi-threaded DuckDB virtual execution engine and FastAPI endpoints that allow the frontend and algorithmic trading components to manage virtual cash, place orders, calculate real-time mark-to-market position valuations, and enforce Indian market regulatory constraints without real capital risk.

---

## 2. Architecture & SOLID Principles Application
- **Single Responsibility Principle (SRP):**
  - `PaperTradingService` encapsulates order validation, fill price calculation (with 5 bps slippage), position lot accounting (FIFO), and margin deduction.
  - `IndianEquityCostModel` handles Indian statutory taxes.
  - `api/routers/paper_trading.py` handles HTTP serialization, request validation, and error responses.
- **Dependency Inversion Principle (DIP):**
  - Database access is injected via `DuckDBConnectionManager`.
  - Cost computation is injected via `IndianEquityCostModel`.

---

## 3. Domain, Math & Core Logic Specifications

### 3.1 Financial Formulas & Margin Model
1. **Slippage Adjusted Fill Price:**
   $$\text{Fill Price}_{\text{BUY}} = P_{\text{LTP}} \times (1 + 0.0005)$$
   $$\text{Fill Price}_{\text{SELL}} = P_{\text{LTP}} \times (1 - 0.0005)$$
2. **Margin Requirements:**
   - **DELIVERY (Equity Cash):** $\text{Required Margin} = \text{Fill Price} \times \text{Quantity}$
   - **INTRADAY (MIS):** $\text{Required Margin} = \frac{\text{Fill Price} \times \text{Quantity}}{5.0}$ (5x Leverage)
3. **P&L Valuation:**
   - Long Position: $\text{Unrealized P&L} = (\text{LTP} - \text{Average Price}) \times \text{Quantity}$
   - Short Position: $\text{Unrealized P&L} = (\text{Average Price} - \text{LTP}) \times \text{Quantity}$
   - Net Realized P&L = $\text{Gross P&L} - \text{Total Taxes and Charges (Entry + Exit)}$

### 3.2 Database Schema DDL
```sql
CREATE TABLE IF NOT EXISTS paper_account (
    account_id VARCHAR PRIMARY KEY,
    balance DOUBLE NOT NULL DEFAULT 1000000.0,
    initial_balance DOUBLE NOT NULL DEFAULT 1000000.0,
    realized_pnl DOUBLE NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS paper_positions (
    position_id VARCHAR PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    side VARCHAR NOT NULL, -- LONG or SHORT
    trade_type VARCHAR NOT NULL DEFAULT 'DELIVERY', -- DELIVERY or INTRADAY
    quantity INTEGER NOT NULL,
    average_price DOUBLE NOT NULL,
    stop_loss DOUBLE,
    take_profit DOUBLE,
    trailing_sl_pct DOUBLE,
    highest_price DOUBLE,
    lowest_price DOUBLE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS paper_orders (
    order_id VARCHAR PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    side VARCHAR NOT NULL, -- BUY or SELL
    order_type VARCHAR NOT NULL, -- MARKET or LIMIT
    trade_type VARCHAR NOT NULL DEFAULT 'DELIVERY',
    quantity INTEGER NOT NULL,
    price DOUBLE,
    trigger_price DOUBLE,
    status VARCHAR NOT NULL DEFAULT 'FILLED', -- PENDING, FILLED, CANCELLED
    stop_loss DOUBLE,
    take_profit DOUBLE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    filled_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS paper_trades (
    trade_id VARCHAR PRIMARY KEY,
    order_id VARCHAR NOT NULL,
    position_id VARCHAR,
    symbol VARCHAR NOT NULL,
    side VARCHAR NOT NULL,
    quantity INTEGER NOT NULL,
    fill_price DOUBLE NOT NULL,
    brokerage DOUBLE NOT NULL DEFAULT 0.0,
    stt DOUBLE NOT NULL DEFAULT 0.0,
    total_charges DOUBLE NOT NULL DEFAULT 0.0,
    gross_pnl DOUBLE DEFAULT 0.0,
    net_pnl DOUBLE DEFAULT 0.0,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS paper_auto_strategies (
    strategy_id VARCHAR PRIMARY KEY,
    strategy_name VARCHAR NOT NULL,
    symbol VARCHAR NOT NULL,
    timeframe VARCHAR NOT NULL DEFAULT '1D',
    parameters JSON NOT NULL,
    trade_type VARCHAR NOT NULL DEFAULT 'DELIVERY',
    allocated_capital DOUBLE NOT NULL DEFAULT 100000.0,
    status VARCHAR NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. Implementation Steps
1. Create `api/models/paper_trading_models.py` with Pydantic schemas (`OrderRequest`, `PositionResponse`, `AccountResponse`, `ClosePositionRequest`, `UpdateRiskRequest`, `DeployStrategyRequest`).
2. Add table initialization in `services/paper_trading_service.py` to ensure all 5 tables exist on boot.
3. Enhance `PaperTradingService` with:
   - `place_order(symbol, side, order_type, quantity, price, stop_loss, take_profit, trade_type)`
   - `close_position(position_id, exit_price)`
   - `update_position_risk(position_id, stop_loss, take_profit, trailing_sl_pct)`
   - `get_positions_with_mtm(current_quotes_map)`
   - `get_account_summary()`
   - `reset_account(initial_capital=1000000.0)`
   - `deploy_strategy(strategy_name, symbol, timeframe, parameters, capital)`
4. Create `api/routers/paper_trading.py` and mount router onto `main.py`.
5. Implement unit and integration test suite: `tests/unit/test_paper_trading_engine.py` and `tests/integration/test_paper_trading_api.py`.

---

## 5. Verification & Acceptance Criteria
- Run `pytest tests/unit/test_paper_trading_engine.py tests/integration/test_paper_trading_api.py -v`.
- Verify order placement deducts cash and records fill in `paper_trades` with STT > 0.
- Verify closing position removes row from `paper_positions` and increments `paper_account.realized_pnl`.
- Verify `POST /api/v1/paper-trading/account/reset` restores balance to ₹10,00,000 cleanly.
