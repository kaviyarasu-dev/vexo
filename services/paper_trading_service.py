from typing import Optional
from db.connection import DuckDBConnectionManager
from services.backtest.cost_model import IndianEquityCostModel
from core.interfaces import PaperFill

class PaperTradingService:
    def __init__(self, db: DuckDBConnectionManager, cost_model: Optional[IndianEquityCostModel] = None):
        self.db = db
        self.cost_model = cost_model or IndianEquityCostModel(slippage_bps=5.0)
        self._ensure_account()

    def _ensure_account(self):
        def _create(conn):
            # check if exists
            row = conn.execute("SELECT balance FROM paper_account WHERE account_id = 'DEFAULT'").fetchone()
            if not row:
                conn.execute("INSERT INTO paper_account (account_id, balance) VALUES ('DEFAULT', 1000000.0)")
        self.db.execute_write_batch(_create)

    def execute_order(self, symbol: str, quantity: int, side: str, order_type: str, current_price: float) -> PaperFill:
        # Calculate slippage adjusted price
        # 5 bps slippage
        # Buy: price moves up, Sell: price moves down
        slippage_factor = self.cost_model.slippage_bps / 10000.0
        if side.upper() == "BUY":
            fill_price = current_price * (1 + slippage_factor)
        else:
            fill_price = current_price * (1 - slippage_factor)
            
        buy_val = (fill_price * quantity) if side.upper() == "BUY" else 0.0
        sell_val = (fill_price * quantity) if side.upper() == "SELL" else 0.0
        
        # We pass 0 for slippage to compute_fees since we already adjusted price, 
        # or we let compute_fees handle slippage as a charge. 
        # Plan 14: CostModel adds slippage to total_taxes_and_fees.
        # Wait, if we adjusted price, we don't want to double count slippage.
        # But `IndianEquityCostModel` internally uses its own slippage_bps.
        # If we just use cost_model for fees, we should pass original price and let it compute slippage,
        # OR we just use the fill_price but set cost_model.slippage_bps = 0 temporarily.
        # Wait, plan says: "Fill Price = 2500 * 1.0005 = 2501.25. Update Cash: Deduct 250,125 + 320 (from cost model)"
        # But the IndianEquityCostModel from Phase 14 INCLUDES slippage in `total_taxes_and_fees`.
        # Actually, let's just let IndianEquityCostModel do it but we need to report fill_price properly.
        # Let's adjust fill_price and temporarily override cost_model slippage, 
        # OR we just subtract slippage from the cost result.
        
        cost_res = self.cost_model.compute_fees(buy_val, sell_val, "DELIVERY")
        total_charges = cost_res.total_taxes_and_fees - cost_res.slippage # subtract slippage since it's baked into fill_price now
        
        net_cash_impact = (buy_val + total_charges) if side.upper() == "BUY" else (-sell_val + total_charges)
        
        def _update(conn):
            # Update balance
            conn.execute("UPDATE paper_account SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP WHERE account_id = 'DEFAULT'", [net_cash_impact])
            
            # Update positions
            pos = conn.execute("SELECT quantity, average_price FROM paper_positions WHERE symbol = ?", [symbol]).fetchone()
            if side.upper() == "BUY":
                if not pos:
                    conn.execute("INSERT INTO paper_positions (symbol, quantity, average_price) VALUES (?, ?, ?)", [symbol, quantity, fill_price])
                else:
                    new_qty = pos[0] + quantity
                    new_avg = ((pos[0] * pos[1]) + (quantity * fill_price)) / new_qty
                    conn.execute("UPDATE paper_positions SET quantity = ?, average_price = ?, updated_at = CURRENT_TIMESTAMP WHERE symbol = ?", [new_qty, new_avg, symbol])
            else: # SELL
                if pos:
                    new_qty = pos[0] - quantity
                    if new_qty > 0:
                        conn.execute("UPDATE paper_positions SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE symbol = ?", [new_qty, symbol])
                    else:
                        conn.execute("DELETE FROM paper_positions WHERE symbol = ?", [symbol])

        self.db.execute_write_batch(_update)
        
        return PaperFill(
            symbol=symbol,
            quantity=quantity,
            side=side,
            fill_price=fill_price,
            total_charges=total_charges
        )
