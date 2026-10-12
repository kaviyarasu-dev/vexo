import uuid
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from db.connection import DuckDBConnectionManager
from services.backtest.cost_model import IndianEquityCostModel
from core.interfaces import PaperFill
from api.models.paper_trading_models import (
    OrderResponse,
    PositionResponse,
    AccountResponse,
    TradeHistoryItem,
    AutoStrategyResponse,
)

logger = logging.getLogger(__name__)


class PaperTradingService:
    """Institutional-grade Paper Trading Engine with Indian statutory tax accounting and MTM position management."""

    def __init__(self, db: DuckDBConnectionManager, cost_model: Optional[IndianEquityCostModel] = None):
        self.db = db
        self.cost_model = cost_model or IndianEquityCostModel(slippage_bps=5.0)
        self._ensure_tables()

    def _ensure_tables(self):
        def _create(conn):
            # 1. paper_account
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_account (
                    account_id VARCHAR PRIMARY KEY,
                    balance DOUBLE NOT NULL DEFAULT 1000000.0,
                    initial_balance DOUBLE DEFAULT 1000000.0,
                    realized_pnl DOUBLE DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Safe column additions if table already existed in earlier migration
            for col, col_type in [
                ("initial_balance", "DOUBLE DEFAULT 1000000.0"),
                ("realized_pnl", "DOUBLE DEFAULT 0.0"),
                ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            ]:
                try:
                    conn.execute(f"ALTER TABLE paper_account ADD COLUMN {col} {col_type}")
                except Exception:
                    pass

            # 2. paper_positions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_positions (
                    symbol VARCHAR PRIMARY KEY,
                    quantity INTEGER NOT NULL,
                    average_price DOUBLE NOT NULL,
                    side VARCHAR DEFAULT 'LONG',
                    trade_type VARCHAR DEFAULT 'DELIVERY',
                    stop_loss DOUBLE,
                    take_profit DOUBLE,
                    trailing_sl_pct DOUBLE,
                    highest_price DOUBLE,
                    lowest_price DOUBLE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            for col, col_type in [
                ("side", "VARCHAR DEFAULT 'LONG'"),
                ("trade_type", "VARCHAR DEFAULT 'DELIVERY'"),
                ("stop_loss", "DOUBLE"),
                ("take_profit", "DOUBLE"),
                ("trailing_sl_pct", "DOUBLE"),
                ("highest_price", "DOUBLE"),
                ("lowest_price", "DOUBLE"),
                ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            ]:
                try:
                    conn.execute(f"ALTER TABLE paper_positions ADD COLUMN {col} {col_type}")
                except Exception:
                    pass

            # 3. paper_orders
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_orders (
                    order_id VARCHAR PRIMARY KEY,
                    symbol VARCHAR NOT NULL,
                    side VARCHAR NOT NULL,
                    order_type VARCHAR NOT NULL DEFAULT 'MARKET',
                    trade_type VARCHAR NOT NULL DEFAULT 'DELIVERY',
                    quantity INTEGER NOT NULL,
                    price DOUBLE,
                    trigger_price DOUBLE,
                    status VARCHAR NOT NULL DEFAULT 'FILLED',
                    stop_loss DOUBLE,
                    take_profit DOUBLE,
                    trailing_sl_pct DOUBLE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    filled_at TIMESTAMP
                )
            """)

            # 4. paper_trades
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_trades (
                    trade_id VARCHAR PRIMARY KEY,
                    order_id VARCHAR NOT NULL,
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
                )
            """)

            # 5. paper_auto_strategies
            conn.execute("""
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
                )
            """)

            # Ensure default account exists
            row = conn.execute("SELECT balance FROM paper_account WHERE account_id = 'DEFAULT'").fetchone()
            if not row:
                conn.execute("""
                    INSERT INTO paper_account (account_id, balance, initial_balance, realized_pnl)
                    VALUES ('DEFAULT', 1000000.0, 1000000.0, 0.0)
                """)

        self.db.execute_write_batch(_create)

    def _get_latest_price(self, symbol: str) -> float:
        """Retrieves latest close price from DuckDB or fallback spot."""
        cursor = self.db.get_read_cursor()
        try:
            row = cursor.execute(
                "SELECT close FROM candles_1d_adjusted WHERE symbol = ? ORDER BY date DESC LIMIT 1",
                [symbol.strip()]
            ).fetchone()
            if row and row[0] is not None and float(row[0]) > 0:
                return round(float(row[0]), 2)
        except Exception:
            pass
        finally:
            cursor.close()

        # Sensible defaults for testing/indices
        defaults = {
            "RELIANCE": 2865.0,
            "TCS": 4120.0,
            "INFY": 1915.0,
            "HDFCBANK": 1660.0,
            "NIFTY50": 25050.0,
            "NIFTYBANK": 51200.0
        }
        for k, v in defaults.items():
            if k in symbol:
                return v
        return 2500.0

    def execute_order(self, symbol: str, quantity: int, side: str, order_type: str, current_price: float) -> PaperFill:
        """Legacy interface maintained for backwards compatibility with test_paper_trading_execution."""
        res = self.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            trade_type="DELIVERY",
            current_price=current_price
        )
        slippage_factor = self.cost_model.slippage_bps / 10000.0
        legacy_fill = current_price * (1 + slippage_factor) if side.upper() == "BUY" else current_price * (1 - slippage_factor)
        return PaperFill(
            symbol=symbol,
            quantity=quantity,
            side=side,
            fill_price=legacy_fill,
            total_charges=res.total_charges
        )

    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "MARKET",
        trade_type: str = "DELIVERY",
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        trailing_sl_pct: Optional[float] = None,
        current_price: Optional[float] = None
    ) -> OrderResponse:
        """Places a simulated virtual order with realistic slippage and statutory costs."""
        clean_symbol = symbol.strip().upper()
        clean_side = side.strip().upper()
        clean_order_type = order_type.strip().upper()
        clean_trade_type = trade_type.strip().upper()

        if clean_side not in ("BUY", "SELL"):
            raise ValueError("Side must be BUY or SELL")
        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0")

        base_price = current_price or price or self._get_latest_price(clean_symbol)
        slippage_factor = self.cost_model.slippage_bps / 10000.0

        if clean_side == "BUY":
            fill_price = round(base_price * (1.0 + slippage_factor), 2)
            buy_val = fill_price * quantity
            sell_val = 0.0
        else:
            fill_price = round(base_price * (1.0 - slippage_factor), 2)
            buy_val = 0.0
            sell_val = fill_price * quantity

        # Statutory fees
        cost_res = self.cost_model.compute_fees(buy_val, sell_val, clean_trade_type)
        total_charges = round(cost_res.total_taxes_and_fees - cost_res.slippage, 2)
        trade_val = fill_price * quantity

        # Margin requirement: 5x for INTRADAY, 1x for DELIVERY
        margin_required = (trade_val / 5.0) if clean_trade_type == "INTRADAY" else trade_val

        order_id = str(uuid.uuid4())
        trade_id = str(uuid.uuid4())
        now = datetime.now()

        def _execute_tx(conn):
            # Check balance
            acc_row = conn.execute("SELECT balance FROM paper_account WHERE account_id = 'DEFAULT'").fetchone()
            current_bal = float(acc_row[0]) if acc_row else 1000000.0

            pos = conn.execute(
                "SELECT quantity, average_price, side, stop_loss, take_profit, trailing_sl_pct, trade_type FROM paper_positions WHERE symbol = ?",
                [clean_symbol]
            ).fetchone()

            is_closing = False
            gross_pnl = 0.0
            net_pnl = 0.0

            if clean_side == "BUY":
                if pos and pos[2] == "SHORT":
                    # Closing a short position
                    is_closing = True
                    existing_qty = pos[0]
                    avg_entry = pos[1]
                    existing_trade_type = pos[6] or "DELIVERY"
                    closed_qty = min(quantity, existing_qty)
                    gross_pnl = (avg_entry - fill_price) * closed_qty
                    net_pnl = gross_pnl - total_charges
                    margin_released = (avg_entry * closed_qty / 5.0) if existing_trade_type == "INTRADAY" else (avg_entry * closed_qty)
                    cash_returned = margin_released + net_pnl

                    # Update cash & realized P&L
                    conn.execute("""
                        UPDATE paper_account
                        SET balance = balance + ?,
                            realized_pnl = realized_pnl + ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE account_id = 'DEFAULT'
                    """, [cash_returned, net_pnl])

                    rem_qty = existing_qty - closed_qty
                    if rem_qty > 0:
                        conn.execute("UPDATE paper_positions SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE symbol = ?", [rem_qty, clean_symbol])
                    else:
                        conn.execute("DELETE FROM paper_positions WHERE symbol = ?", [clean_symbol])
                else:
                    # New or adding to LONG position
                    required_cash = margin_required + total_charges
                    if current_bal < required_cash:
                        raise ValueError(f"Insufficient virtual balance. Required: ₹{required_cash:,.2f}, Available: ₹{current_bal:,.2f}")

                    conn.execute("""
                        UPDATE paper_account
                        SET balance = balance - ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE account_id = 'DEFAULT'
                    """, [required_cash])

                    if not pos:
                        conn.execute("""
                            INSERT INTO paper_positions 
                            (symbol, quantity, average_price, side, trade_type, stop_loss, take_profit, trailing_sl_pct, highest_price, lowest_price, created_at, updated_at)
                            VALUES (?, ?, ?, 'LONG', ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """, [clean_symbol, quantity, fill_price, clean_trade_type, stop_loss, take_profit, trailing_sl_pct, fill_price, fill_price])
                    else:
                        new_qty = pos[0] + quantity
                        new_avg = round(((pos[0] * pos[1]) + (quantity * fill_price)) / new_qty, 2)
                        conn.execute("""
                            UPDATE paper_positions 
                            SET quantity = ?, average_price = ?, stop_loss = ?, take_profit = ?, trailing_sl_pct = ?, updated_at = CURRENT_TIMESTAMP 
                            WHERE symbol = ?
                        """, [new_qty, new_avg, stop_loss or pos[3], take_profit or pos[4], trailing_sl_pct or pos[5], clean_symbol])

            else:  # SELL
                if pos and pos[2] == "LONG":
                    # Closing or reducing LONG position
                    is_closing = True
                    existing_qty = pos[0]
                    avg_entry = pos[1]
                    existing_trade_type = pos[6] or "DELIVERY"
                    closed_qty = min(quantity, existing_qty)
                    gross_pnl = (fill_price - avg_entry) * closed_qty
                    net_pnl = gross_pnl - total_charges
                    margin_released = (avg_entry * closed_qty / 5.0) if existing_trade_type == "INTRADAY" else (avg_entry * closed_qty)
                    cash_returned = margin_released + net_pnl

                    # Add back margin released + net P&L
                    conn.execute("""
                        UPDATE paper_account 
                        SET balance = balance + ?,
                            realized_pnl = realized_pnl + ?,
                            updated_at = CURRENT_TIMESTAMP 
                        WHERE account_id = 'DEFAULT'
                    """, [cash_returned, net_pnl])

                    rem_qty = existing_qty - closed_qty
                    if rem_qty > 0:
                        conn.execute("UPDATE paper_positions SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE symbol = ?", [rem_qty, clean_symbol])
                    else:
                        conn.execute("DELETE FROM paper_positions WHERE symbol = ?", [clean_symbol])
                else:
                    # New SHORT position
                    required_cash = margin_required + total_charges
                    if current_bal < required_cash:
                        raise ValueError(f"Insufficient virtual balance for short position. Required: ₹{required_cash:,.2f}, Available: ₹{current_bal:,.2f}")

                    conn.execute("""
                        UPDATE paper_account 
                        SET balance = balance - ?,
                            updated_at = CURRENT_TIMESTAMP 
                        WHERE account_id = 'DEFAULT'
                    """, [required_cash])

                    if not pos:
                        conn.execute("""
                            INSERT INTO paper_positions 
                            (symbol, quantity, average_price, side, trade_type, stop_loss, take_profit, trailing_sl_pct, highest_price, lowest_price, created_at, updated_at)
                            VALUES (?, ?, ?, 'SHORT', ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """, [clean_symbol, quantity, fill_price, clean_trade_type, stop_loss, take_profit, trailing_sl_pct, fill_price, fill_price])
                    else:
                        new_qty = pos[0] + quantity
                        new_avg = round(((pos[0] * pos[1]) + (quantity * fill_price)) / new_qty, 2)
                        conn.execute("""
                            UPDATE paper_positions 
                            SET quantity = ?, average_price = ?, stop_loss = ?, take_profit = ?, trailing_sl_pct = ?, updated_at = CURRENT_TIMESTAMP 
                            WHERE symbol = ?
                        """, [new_qty, new_avg, stop_loss or pos[3], take_profit or pos[4], trailing_sl_pct or pos[5], clean_symbol])

            # Record in orders
            conn.execute("""
                INSERT INTO paper_orders 
                (order_id, symbol, side, order_type, trade_type, quantity, price, status, stop_loss, take_profit, trailing_sl_pct, created_at, filled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'FILLED', ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, [order_id, clean_symbol, clean_side, clean_order_type, clean_trade_type, quantity, fill_price, stop_loss, take_profit, trailing_sl_pct])

            # Record in trades
            conn.execute("""
                INSERT INTO paper_trades 
                (trade_id, order_id, symbol, side, quantity, fill_price, brokerage, stt, total_charges, gross_pnl, net_pnl, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, [trade_id, order_id, clean_symbol, clean_side, quantity, fill_price, cost_res.brokerage, cost_res.stt, total_charges, gross_pnl, net_pnl])

        self.db.execute_write_batch(_execute_tx)

        return OrderResponse(
            order_id=order_id,
            symbol=clean_symbol,
            side=clean_side,
            order_type=clean_order_type,
            trade_type=clean_trade_type,
            quantity=quantity,
            fill_price=fill_price,
            total_charges=total_charges,
            status="FILLED",
            executed_at=now.isoformat()
        )

    def close_position(self, symbol: str, exit_price: Optional[float] = None) -> OrderResponse:
        """Closes an open position completely at current market price."""
        clean_symbol = symbol.strip().upper()
        cursor = self.db.get_read_cursor()
        try:
            pos = cursor.execute("SELECT quantity, side, trade_type FROM paper_positions WHERE symbol = ?", [clean_symbol]).fetchone()
        finally:
            cursor.close()

        if not pos:
            raise ValueError(f"No active position found for {clean_symbol}")

        qty, side, trade_type = pos[0], pos[1], pos[2]
        opposite_side = "SELL" if side == "LONG" else "BUY"

        return self.place_order(
            symbol=clean_symbol,
            side=opposite_side,
            quantity=qty,
            order_type="MARKET",
            trade_type=trade_type or "DELIVERY",
            current_price=exit_price
        )

    def update_position_risk(
        self,
        symbol: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        trailing_sl_pct: Optional[float] = None
    ) -> bool:
        """Updates stop loss, take profit, or trailing SL % for an active position."""
        clean_symbol = symbol.strip().upper()

        def _update(conn):
            conn.execute("""
                UPDATE paper_positions
                SET stop_loss = COALESCE(?, stop_loss),
                    take_profit = COALESCE(?, take_profit),
                    trailing_sl_pct = COALESCE(?, trailing_sl_pct),
                    updated_at = CURRENT_TIMESTAMP
                WHERE symbol = ?
            """, [stop_loss, take_profit, trailing_sl_pct, clean_symbol])

        self.db.execute_write_batch(_update)
        return True

    def get_positions_with_mtm(self, quotes_map: Optional[Dict[str, float]] = None) -> List[PositionResponse]:
        """Returns all open positions with real-time mark-to-market valuations."""
        quotes = quotes_map or {}
        cursor = self.db.get_read_cursor()
        try:
            rows = cursor.execute("""
                SELECT symbol, quantity, average_price, side, trade_type, stop_loss, take_profit, trailing_sl_pct, updated_at
                FROM paper_positions
                ORDER BY updated_at DESC
            """).fetchall()
        finally:
            cursor.close()

        positions = []
        for r in rows:
            sym = r[0]
            qty = int(r[1])
            avg_p = float(r[2])
            side = str(r[3] or "LONG")
            t_type = str(r[4] or "DELIVERY")
            sl = float(r[5]) if r[5] is not None else None
            tp = float(r[6]) if r[6] is not None else None
            trail = float(r[7]) if r[7] is not None else None
            updated = str(r[8])

            ltp = quotes.get(sym) or self._get_latest_price(sym)
            if side == "LONG":
                unrealized = round((ltp - avg_p) * qty, 2)
            else:
                unrealized = round((avg_p - ltp) * qty, 2)

            cost_basis = avg_p * qty
            pct = round((unrealized / cost_basis) * 100.0, 2) if cost_basis > 0 else 0.0

            positions.append(PositionResponse(
                symbol=sym,
                side=side,
                trade_type=t_type,
                quantity=qty,
                average_price=avg_p,
                current_price=ltp,
                unrealized_pnl=unrealized,
                unrealized_pnl_pct=pct,
                stop_loss=sl,
                take_profit=tp,
                trailing_sl_pct=trail,
                updated_at=updated
            ))
        return positions

    def get_account_summary(self, quotes_map: Optional[Dict[str, float]] = None) -> AccountResponse:
        """Computes virtual balance, utilized margin, and total portfolio valuation."""
        cursor = self.db.get_read_cursor()
        try:
            acc = cursor.execute("SELECT balance, initial_balance, realized_pnl FROM paper_account WHERE account_id = 'DEFAULT'").fetchone()
        finally:
            cursor.close()

        bal = float(acc[0]) if acc else 1000000.0
        init_bal = float(acc[1]) if acc else 1000000.0
        realized = float(acc[2]) if acc else 0.0

        positions = self.get_positions_with_mtm(quotes_map)
        total_unrealized = sum(p.unrealized_pnl for p in positions)
        margin_used = sum((p.average_price * p.quantity / 5.0) if p.trade_type == "INTRADAY" else (p.average_price * p.quantity) for p in positions)
        available = round(bal, 2)
        net_worth = round(bal + margin_used + total_unrealized, 2)

        return AccountResponse(
            account_id="DEFAULT",
            balance=round(bal, 2),
            initial_balance=round(init_bal, 2),
            margin_utilized=round(margin_used, 2),
            available_balance=round(available, 2),
            realized_pnl=round(realized, 2),
            total_unrealized_pnl=round(total_unrealized, 2),
            net_portfolio_value=net_worth
        )

    def reset_account(self, initial_capital: float = 1000000.0) -> AccountResponse:
        """Resets virtual account balance and clears all active positions, orders, and trade history."""
        def _reset(conn):
            conn.execute("DELETE FROM paper_positions")
            conn.execute("DELETE FROM paper_orders")
            conn.execute("DELETE FROM paper_trades")
            conn.execute("DELETE FROM paper_auto_strategies")
            conn.execute("""
                UPDATE paper_account 
                SET balance = ?, initial_balance = ?, realized_pnl = 0.0, updated_at = CURRENT_TIMESTAMP 
                WHERE account_id = 'DEFAULT'
            """, [initial_capital, initial_capital])

        self.db.execute_write_batch(_reset)
        return self.get_account_summary()

    def get_orders(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent order records."""
        cursor = self.db.get_read_cursor()
        try:
            rows = cursor.execute("""
                SELECT order_id, symbol, side, order_type, trade_type, quantity, price, status, stop_loss, take_profit, created_at, filled_at
                FROM paper_orders
                ORDER BY created_at DESC
                LIMIT ?
            """, [limit]).fetchall()
        finally:
            cursor.close()

        orders = []
        for r in rows:
            orders.append({
                "order_id": r[0],
                "symbol": r[1],
                "side": r[2],
                "order_type": r[3],
                "trade_type": r[4],
                "quantity": int(r[5]),
                "price": float(r[6]) if r[6] is not None else None,
                "status": r[7],
                "stop_loss": float(r[8]) if r[8] is not None else None,
                "take_profit": float(r[9]) if r[9] is not None else None,
                "created_at": str(r[10]),
                "filled_at": str(r[11]) if r[11] is not None else None
            })
        return orders

    def get_history(self, limit: int = 50) -> List[TradeHistoryItem]:
        """Returns closed trades ledger with tax breakdown."""
        cursor = self.db.get_read_cursor()
        try:
            rows = cursor.execute("""
                SELECT trade_id, order_id, symbol, side, quantity, fill_price, brokerage, stt, total_charges, gross_pnl, net_pnl, executed_at
                FROM paper_trades
                ORDER BY executed_at DESC
                LIMIT ?
            """, [limit]).fetchall()
        finally:
            cursor.close()

        history = []
        for r in rows:
            history.append(TradeHistoryItem(
                trade_id=r[0],
                order_id=r[1],
                symbol=r[2],
                side=r[3],
                quantity=int(r[4]),
                fill_price=round(float(r[5]), 2),
                brokerage=round(float(r[6]), 2),
                stt=round(float(r[7]), 2),
                total_charges=round(float(r[8]), 2),
                gross_pnl=round(float(r[9] or 0.0), 2),
                net_pnl=round(float(r[10] or 0.0), 2),
                executed_at=str(r[11])
            ))
        return history

    def register_auto_strategy(
        self,
        strategy_name: str,
        symbol: str,
        timeframe: str = "1D",
        parameters: Optional[Dict[str, Any]] = None,
        trade_type: str = "DELIVERY",
        allocated_capital: float = 100000.0
    ) -> AutoStrategyResponse:
        """Registers a backtested quantitative strategy for forward-testing execution."""
        strategy_id = str(uuid.uuid4())
        params = parameters or {}
        now = datetime.now()

        def _insert(conn):
            conn.execute("""
                INSERT INTO paper_auto_strategies 
                (strategy_id, strategy_name, symbol, timeframe, parameters, trade_type, allocated_capital, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', CURRENT_TIMESTAMP)
            """, [strategy_id, strategy_name, symbol.strip().upper(), timeframe, json.dumps(params), trade_type, allocated_capital])

        self.db.execute_write_batch(_insert)

        return AutoStrategyResponse(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            symbol=symbol.strip().upper(),
            timeframe=timeframe,
            parameters=params,
            trade_type=trade_type,
            allocated_capital=allocated_capital,
            status="ACTIVE",
            created_at=now.isoformat()
        )

    def list_auto_strategies(self) -> List[AutoStrategyResponse]:
        """Lists active deployed strategies."""
        cursor = self.db.get_read_cursor()
        try:
            rows = cursor.execute("""
                SELECT strategy_id, strategy_name, symbol, timeframe, parameters, trade_type, allocated_capital, status, created_at
                FROM paper_auto_strategies
                ORDER BY created_at DESC
            """).fetchall()
        finally:
            cursor.close()

        strategies = []
        for r in rows:
            try:
                params = json.loads(r[4]) if isinstance(r[4], str) else (r[4] or {})
            except Exception:
                params = {}

            strategies.append(AutoStrategyResponse(
                strategy_id=r[0],
                strategy_name=r[1],
                symbol=r[2],
                timeframe=r[3],
                parameters=params,
                trade_type=r[5],
                allocated_capital=float(r[6]),
                status=r[7],
                created_at=str(r[8])
            ))
        return strategies

    def delete_auto_strategy(self, strategy_id: str) -> bool:
        """Stops and removes an automated strategy from forward testing."""
        def _del(conn):
            conn.execute("DELETE FROM paper_auto_strategies WHERE strategy_id = ?", [strategy_id])
        self.db.execute_write_batch(_del)
        return True
