import math
from typing import List, Dict, Any

class PerformanceCalculator:
    @staticmethod
    def calculate_cagr(start_val: float, end_val: float, years: float) -> float:
        if years <= 0 or start_val <= 0:
            return 0.0
        return ((end_val / start_val) ** (1 / years)) - 1

    @staticmethod
    def calculate_max_drawdown(equity_curve: List[float]) -> float:
        max_dd = 0.0
        peak = 0.0
        for val in equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        return max_dd

    @staticmethod
    def calculate_sharpe(returns: List[float], risk_free_rate: float = 0.065, periods_per_year: int = 250) -> float:
        if not returns or len(returns) < 2:
            return 0.0
        avg_return = sum(returns) / len(returns)
        # Annualized average return approx:
        ann_return = avg_return * periods_per_year
        
        # Variance of returns
        variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return 0.0
        return (ann_return - risk_free_rate) / (std_dev * math.sqrt(periods_per_year))

    @staticmethod
    def calculate_sortino(returns: List[float], risk_free_rate: float = 0.065, periods_per_year: int = 250) -> float:
        if not returns or len(returns) < 2:
            return 0.0
        avg_return = sum(returns) / len(returns)
        ann_return = avg_return * periods_per_year

        downside_returns = [r for r in returns if r < 0]
        if not downside_returns:
            return 0.0
        
        downside_variance = sum(r ** 2 for r in downside_returns) / (len(returns) - 1)
        downside_std_dev = math.sqrt(downside_variance)
        
        if downside_std_dev == 0:
            return 0.0
        return (ann_return - risk_free_rate) / (downside_std_dev * math.sqrt(periods_per_year))
