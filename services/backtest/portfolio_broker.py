"""
Portfolio Broker for Multi-Asset Basket Backtesting.
Manages global shared portfolio cash, multi-symbol active positions,
FIFO round-trip trade matching, Indian equity cost model deductions,
and mark-to-market daily portfolio valuation.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import pandas as pd
from core.exceptions import LookaheadBiasError
from services.backtest.cost_model import IndianEquityCostModel


@dataclass
class PortfolioPosition:
    symbol: str
    entry_date: Any
    entry_price: float
    qty: int
    cost_basis: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    entry_bar_idx: int = 0
    buy_fees: float = 0.0


class PortfolioBroker:
    """
    Simulates a broker executing trades across a multi-stock universe
    from a shared pool of capital.
    """

    def __init__(
        self,
        initial_capital: float,
        cost_model: IndianEquityCostModel,
        slippage_bps: float = 5.0,
        trade_type: str = "DELIVERY",
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
    ):
        self.initial_capital = float(initial_capital)
        self.cash = float(initial_capital)
        self.cost_model = cost_model
        self.slippage_bps = float(slippage_bps)
        self.slippage_factor = self.slippage_bps / 10000.0
        self.trade_type = trade_type.upper() if trade_type else "DELIVERY"
        self.stop_loss_pct = float(stop_loss_pct) if stop_loss_pct else None
        self.take_profit_pct = float(take_profit_pct) if take_profit_pct else None

        # Multi-symbol position states
        self.open_positions: Dict[str, PortfolioPosition] = {}
        self._open_lots: Dict[str, List[Dict[str, Any]]] = {}

        # Trade records & curves
        self.pending_orders: List[Dict[str, Any]] = []
        self.trades: List[Dict[str, Any]] = []         # Individual execution legs
        self.closed_trades: List[Dict[str, Any]] = []  # Paired round-trip trades
        self.equity_curve: List[Dict[str, Any]] = []
        self.total_fees = 0.0
        self.gross_pnl = 0.0

    @property
    def open_position_count(self) -> int:
        return len(self.open_positions)

    def can_open_slot(self, max_positions: int) -> bool:
        return len(self.open_positions) < max_positions

    def order(
        self,
        symbol: str,
        side: str,
        qty: int,
        reason: str = "SIGNAL",
        execution_price: Optional[float] = None,
    ):
        """
        Place an order for the next bar's open price.
        Enforces lookahead bias protection.
        """
        if execution_price is not None:
            raise LookaheadBiasError(
                "Strategies cannot specify exact execution prices. Orders must fill at next bar's OPEN."
            )
        if qty <= 0:
            return

        self.pending_orders.append({
            "symbol": symbol,
            "side": side.upper(),
            "qty": int(qty),
            "reason": reason,
        })

    def process_orders(self, current_bars: Dict[str, pd.Series], bar_idx: int = 0):
        """
        Executes pending orders at the OPEN price of current bar for each symbol.
        """
        if not self.pending_orders:
            return

        orders_to_process = self.pending_orders
        self.pending_orders = []

        for order in orders_to_process:
            symbol = order["symbol"]
            if symbol not in current_bars:
                continue

            bar = current_bars[symbol]
            open_price = float(bar["open"])
            side = order["side"]
            qty = order["qty"]
            reason = order.get("reason", "SIGNAL")
            timestamp = bar.get("timestamp")

            if side == "BUY":
                fill_price = open_price * (1.0 + self.slippage_factor)
                trade_val = fill_price * qty
                fees = self.cost_model.compute_fees(
                    buy_val=trade_val, sell_val=0.0, trade_type=self.trade_type
                )
                total_fee = fees.total_taxes_and_fees
                total_cost = trade_val + total_fee

                # If cash is insufficient for the full desired quantity, downsize or drop
                if self.cash < total_cost:
                    if self.cash <= fill_price * 1.001:
                        # Cannot even afford 1 share + statutory charges
                        continue
                    # Approximate affordable shares
                    affordable_qty = int(self.cash // (fill_price * 1.003))
                    if affordable_qty <= 0:
                        continue
                    qty = affordable_qty
                    trade_val = fill_price * qty
                    fees = self.cost_model.compute_fees(
                        buy_val=trade_val, sell_val=0.0, trade_type=self.trade_type
                    )
                    total_fee = fees.total_taxes_and_fees
                    total_cost = trade_val + total_fee

                self.cash -= total_cost
                self.total_fees += total_fee

                # Record execution leg
                ts_str = timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)
                self.trades.append({
                    "timestamp": ts_str,
                    "symbol": symbol,
                    "side": "BUY",
                    "qty": qty,
                    "fill_price": round(fill_price, 2),
                    "fees": round(total_fee, 2),
                    "reason": reason,
                })

                # Maintain lot queue for FIFO matching
                if symbol not in self._open_lots:
                    self._open_lots[symbol] = []
                self._open_lots[symbol].append({
                    "qty": qty,
                    "entry_price": fill_price,
                    "entry_time": ts_str,
                    "bar_idx": bar_idx,
                    "buy_fee": total_fee,
                })

                # Update or create active position
                if symbol in self.open_positions:
                    pos = self.open_positions[symbol]
                    total_qty = pos.qty + qty
                    new_cost_basis = pos.cost_basis + trade_val
                    avg_price = new_cost_basis / total_qty
                    pos.qty = total_qty
                    pos.cost_basis = new_cost_basis
                    pos.entry_price = avg_price
                    pos.buy_fees += total_fee
                else:
                    self.open_positions[symbol] = PortfolioPosition(
                        symbol=symbol,
                        entry_date=ts_str,
                        entry_price=fill_price,
                        qty=qty,
                        cost_basis=trade_val,
                        stop_loss=self.stop_loss_pct,
                        take_profit=self.take_profit_pct,
                        entry_bar_idx=bar_idx,
                        buy_fees=total_fee,
                    )

            elif side == "SELL":
                if symbol not in self.open_positions or self.open_positions[symbol].qty <= 0:
                    continue

                pos = self.open_positions[symbol]
                sell_qty = min(qty, pos.qty)
                fill_price = open_price * (1.0 - self.slippage_factor)
                self._execute_sell(
                    symbol=symbol,
                    fill_price=fill_price,
                    qty=sell_qty,
                    exit_time=timestamp,
                    bar_idx=bar_idx,
                    reason=reason,
                )

    def check_risk_exits(self, current_bars: Dict[str, pd.Series], bar_idx: int = 0):
        """
        Checks intraday high and low on current bars for Stop Loss or Take Profit breaches.
        """
        symbols_to_check = list(self.open_positions.keys())
        for symbol in symbols_to_check:
            if symbol not in current_bars or symbol not in self.open_positions:
                continue

            bar = current_bars[symbol]
            pos = self.open_positions[symbol]
            if pos.qty <= 0:
                continue

            low_price = float(bar["low"])
            high_price = float(bar["high"])
            open_price = float(bar["open"])
            avg_entry = pos.entry_price
            timestamp = bar.get("timestamp")

            # 1. Stop Loss Exit (Capital Preservation Priority)
            if self.stop_loss_pct and self.stop_loss_pct > 0:
                sl_price = avg_entry * (1.0 - (self.stop_loss_pct / 100.0))
                if low_price <= sl_price:
                    fill_price = min(open_price, sl_price) * (1.0 - self.slippage_factor)
                    self._execute_sell(
                        symbol=symbol,
                        fill_price=fill_price,
                        qty=pos.qty,
                        exit_time=timestamp,
                        bar_idx=bar_idx,
                        reason="STOP_LOSS",
                    )
                    continue

            # 2. Take Profit Exit
            if self.take_profit_pct and self.take_profit_pct > 0:
                tp_price = avg_entry * (1.0 + (self.take_profit_pct / 100.0))
                if high_price >= tp_price:
                    fill_price = max(open_price, tp_price) * (1.0 - self.slippage_factor)
                    self._execute_sell(
                        symbol=symbol,
                        fill_price=fill_price,
                        qty=pos.qty,
                        exit_time=timestamp,
                        bar_idx=bar_idx,
                        reason="TAKE_PROFIT",
                    )
                    continue

    def _execute_sell(
        self,
        symbol: str,
        fill_price: float,
        qty: int,
        exit_time: Any,
        bar_idx: int,
        reason: str = "SIGNAL",
    ):
        """
        Internal FIFO matching for a sell order against open lots.
        """
        trade_val = fill_price * qty
        fees = self.cost_model.compute_fees(
            buy_val=0.0, sell_val=trade_val, trade_type=self.trade_type
        )
        sell_fee = fees.total_taxes_and_fees

        self.cash += (trade_val - sell_fee)
        self.total_fees += sell_fee

        ts_str = exit_time.isoformat() if hasattr(exit_time, "isoformat") else str(exit_time)
        self.trades.append({
            "timestamp": ts_str,
            "symbol": symbol,
            "side": "SELL",
            "qty": qty,
            "fill_price": round(fill_price, 2),
            "fees": round(sell_fee, 2),
            "reason": reason,
        })

        # Match lots FIFO
        lots = self._open_lots.get(symbol, [])
        remaining_qty = qty

        while remaining_qty > 0 and lots:
            lot = lots[0]
            matched_qty = min(remaining_qty, lot["qty"])

            entry_cost = lot["entry_price"] * matched_qty
            exit_revenue = fill_price * matched_qty
            gross_pnl = exit_revenue - entry_cost

            # Prorated buy fee + prorated sell fee
            lot_buy_fee = lot["buy_fee"] * (matched_qty / lot["qty"]) if lot["qty"] > 0 else 0.0
            prorated_sell_fee = sell_fee * (matched_qty / qty) if qty > 0 else 0.0
            total_trade_fees = lot_buy_fee + prorated_sell_fee
            net_pnl = gross_pnl - total_trade_fees
            pnl_pct = (net_pnl / entry_cost * 100.0) if entry_cost > 0 else 0.0

            bars_held = max(1, bar_idx - lot["bar_idx"])
            self.gross_pnl += gross_pnl

            self.closed_trades.append({
                "trade_id": len(self.closed_trades) + 1,
                "symbol": symbol,
                "entry_time": lot["entry_time"],
                "exit_time": ts_str,
                "side": "BUY",
                "qty": matched_qty,
                "entry_price": round(lot["entry_price"], 2),
                "exit_price": round(fill_price, 2),
                "gross_pnl": round(gross_pnl, 2),
                "fees": round(total_trade_fees, 2),
                "net_pnl": round(net_pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "exit_reason": reason,
                "holding_period_bars": bars_held,
            })

            if matched_qty == lot["qty"]:
                lots.pop(0)
            else:
                lot["qty"] -= matched_qty
                lot["buy_fee"] -= lot_buy_fee

            remaining_qty -= matched_qty

        # Update position tracker
        if symbol in self.open_positions:
            pos = self.open_positions[symbol]
            pos.qty -= qty
            if pos.qty <= 0:
                del self.open_positions[symbol]
                if symbol in self._open_lots and not self._open_lots[symbol]:
                    del self._open_lots[symbol]

    def update_equity(self, timestamp: Any, current_bars: Dict[str, pd.Series]) -> float:
        """
        Updates the mark-to-market portfolio equity snapshot.
        """
        mtm = 0.0
        for symbol, pos in self.open_positions.items():
            if symbol in current_bars:
                close_price = float(current_bars[symbol]["close"])
                mtm += pos.qty * close_price
            else:
                mtm += pos.qty * pos.entry_price

        total_equity = self.cash + mtm
        exposure_ratio = (mtm / total_equity) if total_equity > 0 else 0.0

        ts_str = timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)
        self.equity_curve.append({
            "timestamp": ts_str,
            "equity": round(total_equity, 2),
            "cash": round(self.cash, 2),
            "invested": round(mtm, 2),
            "open_positions": len(self.open_positions),
            "exposure_ratio": round(exposure_ratio, 4),
        })
        return total_equity

    def close_all_positions(
        self,
        timestamp: Any,
        current_bars: Dict[str, pd.Series],
        bar_idx: int,
        reason: str = "END_OF_DATA",
    ):
        """
        Force liquidates all open positions at the close price of the final bar.
        """
        symbols_to_close = list(self.open_positions.keys())
        for symbol in symbols_to_close:
            pos = self.open_positions.get(symbol)
            if not pos or pos.qty <= 0:
                continue

            if symbol in current_bars:
                close_price = float(current_bars[symbol]["close"])
            else:
                close_price = pos.entry_price

            self._execute_sell(
                symbol=symbol,
                fill_price=close_price,
                qty=pos.qty,
                exit_time=timestamp,
                bar_idx=bar_idx,
                reason=reason,
            )
