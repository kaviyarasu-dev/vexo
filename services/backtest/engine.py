import pandas as pd
from typing import Dict, Any, List, Optional
from core.exceptions import LookaheadBiasError
from services.backtest.cost_model import IndianEquityCostModel

class Strategy:
    def on_bar(self, bar: pd.Series, broker: 'Broker'):
        pass

class Broker:
    def __init__(
        self,
        initial_capital: float,
        cost_model: IndianEquityCostModel,
        slippage_bps: float = 0.0,
        trade_type: str = "DELIVERY",
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None
    ):
        self.capital = initial_capital
        self.cash = initial_capital
        self.positions = 0
        self.cost_model = cost_model
        self.slippage_bps = slippage_bps
        self.trade_type = trade_type.upper() if trade_type else "DELIVERY"
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
        self.pending_orders = []
        self.trades = []            # Fill legs (raw)
        self.closed_trades = []     # Paired round-trip trade records
        self.equity_curve = []
        self.total_fees = 0.0
        self.gross_pnl = 0.0
        
        # Open lots queue for FIFO matching
        self._open_lots: List[Dict[str, Any]] = []

    def order(self, side: str, qty: int, execution_price: float = None, reason: str = "SIGNAL"):
        if execution_price is not None:
            raise LookaheadBiasError("Strategies cannot specify exact execution prices. Orders must fill at next bar's OPEN.")
        if qty <= 0:
            return
        self.pending_orders.append({'side': side.upper(), 'qty': int(qty), 'reason': reason})

    def process_orders(self, current_bar: pd.Series, bar_idx: int = 0):
        if not self.pending_orders:
            return

        open_price = float(current_bar['open'])
        slippage_factor = self.slippage_bps / 10000.0
        
        for order in self.pending_orders:
            side = order['side']
            qty = order['qty']
            reason = order.get('reason', 'SIGNAL')
            
            if side == 'BUY':
                fill_price = open_price * (1 + slippage_factor)
                trade_val = fill_price * qty
                fees = self.cost_model.compute_fees(buy_val=trade_val, sell_val=0, trade_type=self.trade_type)
                total_fee = fees.total_taxes_and_fees
                
                self.cash -= (trade_val + total_fee)
                self.positions += qty
                self.total_fees += total_fee
                
                self.trades.append({
                    'timestamp': current_bar['timestamp'],
                    'side': 'BUY',
                    'qty': qty,
                    'fill_price': fill_price,
                    'fees': total_fee,
                    'reason': reason
                })
                
                self._open_lots.append({
                    'qty': qty,
                    'entry_price': fill_price,
                    'entry_time': current_bar['timestamp'],
                    'bar_idx': bar_idx,
                    'buy_fee': total_fee
                })
                
            elif side == 'SELL' and self.positions >= qty:
                fill_price = open_price * (1 - slippage_factor)
                self._execute_sell(fill_price, qty, current_bar['timestamp'], bar_idx, reason=reason)
                
        self.pending_orders = []

    def check_risk_exits(self, current_bar: pd.Series, bar_idx: int = 0):
        """Check intraday bar extremes for Stop Loss or Take Profit breaches."""
        if self.positions <= 0 or not self._open_lots:
            return
        
        avg_entry = sum(lot['entry_price'] * lot['qty'] for lot in self._open_lots) / self.positions
        low_price = float(current_bar['low'])
        high_price = float(current_bar['high'])
        open_price = float(current_bar['open'])
        slippage_factor = self.slippage_bps / 10000.0

        # Check Stop Loss first (capital protection priority)
        if self.stop_loss_pct and self.stop_loss_pct > 0:
            sl_price = avg_entry * (1.0 - (self.stop_loss_pct / 100.0))
            if low_price <= sl_price:
                # Triggered SL
                fill_price = min(open_price, sl_price) * (1 - slippage_factor)
                self._execute_sell(fill_price, self.positions, current_bar['timestamp'], bar_idx, reason="STOP_LOSS")
                self.pending_orders = []
                return

        # Check Take Profit
        if self.take_profit_pct and self.take_profit_pct > 0:
            tp_price = avg_entry * (1.0 + (self.take_profit_pct / 100.0))
            if high_price >= tp_price:
                # Triggered TP
                fill_price = max(open_price, tp_price) * (1 - slippage_factor)
                self._execute_sell(fill_price, self.positions, current_bar['timestamp'], bar_idx, reason="TAKE_PROFIT")
                self.pending_orders = []
                return

    def _execute_sell(self, fill_price: float, qty: int, exit_time: Any, bar_idx: int, reason: str = "SIGNAL"):
        """Internal helper to close open lots with FIFO matching."""
        trade_val = fill_price * qty
        fees = self.cost_model.compute_fees(buy_val=0, sell_val=trade_val, trade_type=self.trade_type)
        sell_fee = fees.total_taxes_and_fees
        
        self.cash += (trade_val - sell_fee)
        self.positions -= qty
        self.total_fees += sell_fee
        
        self.trades.append({
            'timestamp': exit_time,
            'side': 'SELL',
            'qty': qty,
            'fill_price': fill_price,
            'fees': sell_fee,
            'reason': reason
        })
        
        # Match FIFO with open lots
        remaining_qty = qty
        while remaining_qty > 0 and self._open_lots:
            lot = self._open_lots[0]
            matched_qty = min(remaining_qty, lot['qty'])
            
            entry_cost = lot['entry_price'] * matched_qty
            exit_revenue = fill_price * matched_qty
            gross_pnl = exit_revenue - entry_cost
            
            # Prorated buy fee + prorated sell fee
            lot_buy_fee = lot['buy_fee'] * (matched_qty / lot['qty']) if lot['qty'] > 0 else 0.0
            prorated_sell_fee = sell_fee * (matched_qty / qty) if qty > 0 else 0.0
            total_trade_fees = lot_buy_fee + prorated_sell_fee
            net_pnl = gross_pnl - total_trade_fees
            pnl_pct = (net_pnl / entry_cost * 100.0) if entry_cost > 0 else 0.0
            
            bars_held = max(1, bar_idx - lot['bar_idx'])
            
            self.closed_trades.append({
                'trade_id': len(self.closed_trades) + 1,
                'entry_time': lot['entry_time'].isoformat() if hasattr(lot['entry_time'], 'isoformat') else str(lot['entry_time']),
                'exit_time': exit_time.isoformat() if hasattr(exit_time, 'isoformat') else str(exit_time),
                'side': 'BUY',
                'qty': matched_qty,
                'entry_price': round(lot['entry_price'], 2),
                'exit_price': round(fill_price, 2),
                'gross_pnl': round(gross_pnl, 2),
                'fees': round(total_trade_fees, 2),
                'net_pnl': round(net_pnl, 2),
                'pnl_pct': round(pnl_pct, 2),
                'exit_reason': reason,
                'holding_period_bars': bars_held
            })
            
            if matched_qty == lot['qty']:
                self._open_lots.pop(0)
            else:
                lot['qty'] -= matched_qty
                lot['buy_fee'] -= lot_buy_fee
                
            remaining_qty -= matched_qty

    def update_equity(self, current_bar: pd.Series):
        close_price = float(current_bar['close'])
        mtm = self.positions * close_price
        total_equity = self.cash + mtm
        ts_str = current_bar['timestamp'].isoformat() if hasattr(current_bar['timestamp'], 'isoformat') else str(current_bar['timestamp'])
        self.equity_curve.append({
            'timestamp': ts_str,
            'equity': round(total_equity, 2)
        })


class Engine:
    def __init__(
        self,
        data: pd.DataFrame,
        initial_capital: float = 1000000.0,
        slippage_bps: float = 0.0,
        trade_type: str = "DELIVERY",
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None
    ):
        self.data = data.sort_values('timestamp').reset_index(drop=True)
        self.cost_model = IndianEquityCostModel(slippage_bps=slippage_bps)
        self.broker = Broker(
            initial_capital=initial_capital,
            cost_model=self.cost_model,
            slippage_bps=slippage_bps,
            trade_type=trade_type,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )

    def run(self, strategy: Strategy):
        # Prevent data leakage by iterating row by row. 
        # Strategy only receives current bar.
        for i, row in self.data.iterrows():
            # 1. Process pending orders at OPEN of current bar (signals generated on previous bar)
            self.broker.process_orders(row, bar_idx=i)
            
            # 2. Check intraday SL/TP risk exits on current bar extremes
            self.broker.check_risk_exits(row, bar_idx=i)
            
            # 3. Evaluate strategy at the CLOSE of the current bar
            strategy.on_bar(row, self.broker)
            
            # 4. Update MTM equity curve at bar CLOSE
            self.broker.update_equity(row)
        
        # Liquidate at end if open positions exist at final close
        if self.broker.positions > 0:
            last_idx = len(self.data) - 1
            last_row = self.data.iloc[last_idx]
            last_price = float(last_row['close'])
            self.broker._execute_sell(
                fill_price=last_price,
                qty=self.broker.positions,
                exit_time=last_row['timestamp'],
                bar_idx=last_idx,
                reason="END_OF_DATA"
            )
            self.broker.positions = 0
            self.broker.update_equity(last_row)
