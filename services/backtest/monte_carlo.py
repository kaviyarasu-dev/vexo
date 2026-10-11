import random
import hashlib
from typing import List, Dict, Any
from services.backtest.metrics import PerformanceCalculator

class MonteCarloSimulator:
    def __init__(self, trades: List[Dict[str, Any]], initial_capital: float = 1000000.0, num_simulations: int = 1000, seed: int = 42):
        self.trades = trades
        self.initial_capital = initial_capital
        self.num_simulations = num_simulations
        self.seed = seed

    def run(self) -> Dict[str, Any]:
        if not self.trades:
            return {}

        random.seed(self.seed)
        
        # Calculate individual trade PnL (net)
        # Pair trades up to get trade PnL. For simplicity in MC, we just simulate the daily returns 
        # or the sequence of trade PnL.
        # Since the engine generates raw executions (BUY/SELL), let's pair them up.
        
        trade_pnls = []
        open_trades = []
        for trade in self.trades:
            if trade['side'] == 'BUY':
                open_trades.append(trade)
            elif trade['side'] == 'SELL' and open_trades:
                buy_trade = open_trades.pop(0)
                # Net PnL = Sell Value - Buy Value - Total Fees for both
                buy_val = buy_trade['fill_price'] * buy_trade['qty']
                sell_val = trade['fill_price'] * trade['qty']
                net_pnl = sell_val - buy_val - trade['fees'] - buy_trade['fees']
                trade_pnls.append(net_pnl)

        if not trade_pnls:
            return {}

        max_drawdowns = []
        final_equities = []
        
        for _ in range(self.num_simulations):
            # Resample with replacement
            simulated_pnls = random.choices(trade_pnls, k=len(trade_pnls))
            
            equity = self.initial_capital
            peak = equity
            mdd = 0.0
            
            for pnl in simulated_pnls:
                equity += pnl
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak if peak > 0 else 0
                if dd > mdd:
                    mdd = dd
            
            max_drawdowns.append(mdd)
            final_equities.append(equity)

        # 95% Confidence Interval for Max Drawdown
        max_drawdowns.sort()
        idx_95 = int(self.num_simulations * 0.95)
        mdd_95 = max_drawdowns[idx_95]

        # Probability of Ruin (say, equity drops below 50% of initial)
        ruin_count = sum(1 for e in final_equities if e < self.initial_capital * 0.5)
        prob_ruin = ruin_count / self.num_simulations

        return {
            "mdd_95_ci": mdd_95,
            "prob_ruin": prob_ruin,
            "seed": self.seed
        }

def generate_data_hash(data) -> str:
    # Hash the data version using some deterministic attributes
    # For a DataFrame, we can hash the bytes of the shape and first/last dates
    if data is None or data.empty:
        return ""
    
    first_dt = str(data.iloc[0]['timestamp'])
    last_dt = str(data.iloc[-1]['timestamp'])
    shape_str = str(data.shape)
    
    raw_str = f"{first_dt}_{last_dt}_{shape_str}"
    return hashlib.sha256(raw_str.encode('utf-8')).hexdigest()
