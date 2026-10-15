"""
optimization_engine.py
Institutional Strategy Parameter Optimization 2D Grid Search Engine, 
3x3 Plateau Stability Index Analyzer & Walk-Forward Validation Engine.
"""

import time
import os
import math
import pandas as pd
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor

from services.backtest.engine import Engine, Broker, Strategy
from services.backtest.cost_model import IndianEquityCostModel
from services.backtest.metrics import PerformanceCalculator
from services.backtest_service import (
    compute_indicators,
    SMACrossStrategy,
    RSIReversalStrategy,
    BollingerBandsStrategy,
    SupertrendStrategy,
    MACDStrategy
)

MAX_GRID_COMBINATIONS = 400


@dataclass
class ParamSpec:
    name: str
    min_val: float
    max_val: float
    step: float


@dataclass
class OptimizationCell:
    param1_val: float
    param2_val: float
    sharpe_ratio: float
    net_pnl: float
    net_pnl_pct: float
    max_drawdown_pct: float
    win_rate: float
    total_trades: int
    profit_factor: float


@dataclass
class StabilityResult:
    optimal_param1: float
    optimal_param2: float
    optimal_metric_val: float
    stability_score: float  # 0.0 to 1.0
    classification: str     # 'ROBUST_PLATEAU' | 'MODERATE_SENSITIVITY' | 'FRAGILE_CLIFF'
    neighbor_avg_val: float
    cliff_drop_pct: float
    neighbors: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class WalkForwardResult:
    in_sample_net_pnl: float
    in_sample_sharpe: float
    out_of_sample_net_pnl: float
    out_of_sample_sharpe: float
    walk_forward_efficiency: float
    split_date: str
    is_split_pct: float


def generate_param_ticks(min_val: float, max_val: float, step: float) -> List[float]:
    """Generate discrete ticks between min_val and max_val inclusive with step increment."""
    if step <= 0:
        raise ValueError(f"Step must be strictly positive, got {step}")
    if min_val > max_val:
        raise ValueError(f"min_val ({min_val}) cannot be greater than max_val ({max_val})")

    ticks = []
    curr = float(min_val)
    is_int_step = (float(min_val).is_integer() and float(max_val).is_integer() and float(step).is_integer())

    while curr <= float(max_val) + 1e-9:
        if is_int_step:
            ticks.append(int(round(curr)))
        else:
            ticks.append(round(curr, 4))
        curr += float(step)

    if not ticks:
        raise ValueError("Parameter tick generation resulted in 0 ticks.")
    return ticks


def create_strategy_instance(strategy_name: str, pos_type: str = "PERCENT_CAPITAL", pos_val: float = 100.0) -> Strategy:
    """Instantiate concrete strategy class based on strategy name."""
    s_upper = strategy_name.upper()
    if s_upper in ("SMA_CROSS", "SMA CROSSOVER", "SMA"):
        return SMACrossStrategy(position_size_type=pos_type, position_size_val=pos_val)
    elif s_upper in ("RSI_REVERSION", "RSI", "RSI REVERSAL"):
        return RSIReversalStrategy(position_size_type=pos_type, position_size_val=pos_val)
    elif s_upper in ("BOLLINGER_BANDS", "BOLLINGER", "BB"):
        return BollingerBandsStrategy(position_size_type=pos_type, position_size_val=pos_val)
    elif s_upper in ("SUPERTREND", "SUPER_TREND"):
        return SupertrendStrategy(position_size_type=pos_type, position_size_val=pos_val)
    elif s_upper in ("MACD", "MACD_MOMENTUM"):
        return MACDStrategy(position_size_type=pos_type, position_size_val=pos_val)
    else:
        return SMACrossStrategy(position_size_type=pos_type, position_size_val=pos_val)


class WalkForwardSplitter:
    """Partitions time series chronologically to prevent lookahead bias."""

    @staticmethod
    def split(df: pd.DataFrame, split_pct: float = 70.0) -> Tuple[pd.DataFrame, pd.DataFrame, str]:
        if df.empty:
            raise ValueError("Cannot split empty DataFrame.")
        if not (10.0 <= split_pct <= 90.0):
            raise ValueError(f"split_pct must be between 10.0 and 90.0, got {split_pct}")

        df_sorted = df.sort_values('timestamp').reset_index(drop=True)
        split_idx = int(len(df_sorted) * (split_pct / 100.0))
        if split_idx <= 0:
            split_idx = 1
        elif split_idx >= len(df_sorted):
            split_idx = len(df_sorted) - 1

        is_df = df_sorted.iloc[:split_idx].copy().reset_index(drop=True)
        oos_df = df_sorted.iloc[split_idx:].copy().reset_index(drop=True)

        split_date_raw = is_df['timestamp'].iloc[-1]
        split_date = split_date_raw.strftime('%Y-%m-%d') if hasattr(split_date_raw, 'strftime') else str(split_date_raw)[:10]

        return is_df, oos_df, split_date

    @staticmethod
    def calculate_wfe(is_return: float, oos_return: float) -> float:
        """Computes Walk-Forward Efficiency (WFE = OOS Return / IS Return)."""
        if is_return <= 0:
            return 0.0
        ratio = oos_return / is_return
        return round(float(np.clip(ratio, -5.0, 5.0)), 4)


class StabilityAnalyzer:
    """Analyzes the 3x3 topological neighborhood around optimal cells to identify overfitting cliffs."""

    @staticmethod
    def evaluate(
        cells: List[OptimizationCell],
        param1_ticks: List[float],
        param2_ticks: List[float],
        target_metric: str = "sharpe_ratio"
    ) -> StabilityResult:
        if not cells:
            raise ValueError("No cells provided to StabilityAnalyzer.")

        metric_attr = target_metric.lower()
        if not hasattr(cells[0], metric_attr):
            metric_attr = "sharpe_ratio"

        # Build coordinate lookup map: (p1, p2) -> cell
        cell_map: Dict[Tuple[float, float], OptimizationCell] = {
            (c.param1_val, c.param2_val): c for c in cells
        }

        # 1. Identify optimal cell
        # For max_drawdown_pct, lower absolute is better, but generally we optimize Sharpe, Net PnL or Win Rate
        if metric_attr == "max_drawdown_pct":
            best_cell = min(cells, key=lambda c: getattr(c, metric_attr, 100.0))
        else:
            best_cell = max(cells, key=lambda c: getattr(c, metric_attr, -999999.0))

        optimal_val = getattr(best_cell, metric_attr, 0.0)

        # 2. Find indices in ticks
        try:
            x_idx = param1_ticks.index(best_cell.param1_val)
        except ValueError:
            x_idx = 0
        try:
            y_idx = param2_ticks.index(best_cell.param2_val)
        except ValueError:
            y_idx = 0

        # 3. Inspect 8 adjacent neighbors in 3x3 matrix
        neighbor_cells: List[OptimizationCell] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx = x_idx + dx
                ny = y_idx + dy
                if 0 <= nx < len(param1_ticks) and 0 <= ny < len(param2_ticks):
                    neighbor_key = (param1_ticks[nx], param2_ticks[ny])
                    if neighbor_key in cell_map:
                        neighbor_cells.append(cell_map[neighbor_key])

        if not neighbor_cells:
            # Grid of 1 cell or edge with no neighbors found
            return StabilityResult(
                optimal_param1=best_cell.param1_val,
                optimal_param2=best_cell.param2_val,
                optimal_metric_val=round(optimal_val, 4),
                stability_score=1.0,
                classification="ROBUST_PLATEAU",
                neighbor_avg_val=round(optimal_val, 4),
                cliff_drop_pct=0.0,
                neighbors=[]
            )

        neighbor_vals = [getattr(nc, metric_attr, 0.0) for nc in neighbor_cells]
        neighbor_avg = float(np.mean(neighbor_vals))

        # Calculate Retention Ratios
        if optimal_val > 0:
            ratios = [max(0.0, v / optimal_val) for v in neighbor_vals]
            stability_score = float(np.mean(ratios))
            min_neighbor = min(neighbor_vals)
            cliff_drop = max(0.0, ((optimal_val - min_neighbor) / optimal_val) * 100.0)
        elif optimal_val < 0:
            # If optimal itself is negative
            stability_score = 0.2
            cliff_drop = 80.0
        else:
            stability_score = 0.5
            cliff_drop = 50.0

        stability_score = round(float(np.clip(stability_score, 0.0, 1.0)), 4)
        cliff_drop = round(float(cliff_drop), 2)

        # Classification
        if stability_score >= 0.75:
            classification = "ROBUST_PLATEAU"
        elif stability_score >= 0.50:
            classification = "MODERATE_SENSITIVITY"
        else:
            classification = "FRAGILE_CLIFF"

        neighbors_summary = [
            {
                "param1": nc.param1_val,
                "param2": nc.param2_val,
                "val": round(getattr(nc, metric_attr, 0.0), 4)
            }
            for nc in neighbor_cells
        ]

        return StabilityResult(
            optimal_param1=best_cell.param1_val,
            optimal_param2=best_cell.param2_val,
            optimal_metric_val=round(optimal_val, 4),
            stability_score=stability_score,
            classification=classification,
            neighbor_avg_val=round(neighbor_avg, 4),
            cliff_drop_pct=cliff_drop,
            neighbors=neighbors_summary
        )


class OptimizationEngine:
    """In-memory concurrent grid search runner."""

    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or min(8, max(2, os.cpu_count() or 4))

    def evaluate_cell(
        self,
        df: pd.DataFrame,
        strategy_name: str,
        param1_name: str,
        param1_val: float,
        param2_name: str,
        param2_val: float,
        base_params: Dict[str, Any],
        base_config: Dict[str, Any]
    ) -> OptimizationCell:
        """Evaluates a single parameter combination over provided candle DataFrame."""
        params = dict(base_params)
        params[param1_name] = param1_val
        params[param2_name] = param2_val

        initial_capital = float(base_config.get("initial_capital", 1000000.0))
        slippage_bps = float(base_config.get("slippage_bps", 5.0))
        trade_type = str(base_config.get("trade_type", "DELIVERY"))
        stop_loss_pct = float(base_config.get("stop_loss_pct")) if base_config.get("stop_loss_pct") is not None else None
        take_profit_pct = float(base_config.get("take_profit_pct")) if base_config.get("take_profit_pct") is not None else None
        pos_type = str(base_config.get("position_size_type", "PERCENT_CAPITAL"))
        pos_val = float(base_config.get("position_size_val", 100.0))

        # 1. Indicator computation
        df_signals = compute_indicators(df, strategy_name, params)

        # 2. Engine and Strategy execution
        engine = Engine(
            data=df_signals,
            initial_capital=initial_capital,
            slippage_bps=slippage_bps,
            trade_type=trade_type,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )
        strategy = create_strategy_instance(strategy_name, pos_type=pos_type, pos_val=pos_val)
        engine.run(strategy)

        # 3. Extract metrics
        broker = engine.broker
        closed_trades = broker.closed_trades
        total_trades = len(closed_trades)
        net_pnl = sum(t['net_pnl'] for t in closed_trades) if closed_trades else 0.0
        net_pnl_pct = (net_pnl / initial_capital) * 100.0 if initial_capital > 0 else 0.0

        wins = [t for t in closed_trades if t['net_pnl'] > 0]
        losses = [t for t in closed_trades if t['net_pnl'] < 0]
        win_rate = (len(wins) / total_trades) if total_trades > 0 else 0.0

        gross_wins = sum(t['gross_pnl'] for t in wins)
        gross_losses = abs(sum(t['gross_pnl'] for t in losses))
        profit_factor = round(gross_wins / gross_losses, 2) if gross_losses > 0 else (99.99 if gross_wins > 0 else 0.0)

        equity_vals = [e['equity'] for e in broker.equity_curve]
        max_dd = PerformanceCalculator.calculate_max_drawdown(equity_vals)
        daily_returns = pd.Series(equity_vals).pct_change().dropna().tolist()
        sharpe = PerformanceCalculator.calculate_sharpe(daily_returns)

        return OptimizationCell(
            param1_val=param1_val,
            param2_val=param2_val,
            sharpe_ratio=round(float(sharpe), 4),
            net_pnl=round(float(net_pnl), 2),
            net_pnl_pct=round(float(net_pnl_pct), 2),
            max_drawdown_pct=round(float(max_dd), 2),
            win_rate=round(float(win_rate), 4),
            total_trades=total_trades,
            profit_factor=round(float(profit_factor), 2)
        )

    def run_grid(
        self,
        df: pd.DataFrame,
        strategy_name: str,
        param1: ParamSpec,
        param2: ParamSpec,
        base_params: Optional[Dict[str, Any]] = None,
        base_config: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[OptimizationCell], List[float], List[float]]:
        """Runs the Cartesian grid evaluation in parallel across thread pool."""
        base_params = base_params or {}
        base_config = base_config or {}

        p1_ticks = generate_param_ticks(param1.min_val, param1.max_val, param1.step)
        p2_ticks = generate_param_ticks(param2.min_val, param2.max_val, param2.step)

        total_combinations = len(p1_ticks) * len(p2_ticks)
        if total_combinations > MAX_GRID_COMBINATIONS:
            raise ValueError(
                f"Optimization grid has {total_combinations} combinations, which exceeds the "
                f"institutional cap of {MAX_GRID_COMBINATIONS}. Please increase the parameter step size."
            )

        tasks = []
        for p2 in p2_ticks:
            for p1 in p1_ticks:
                tasks.append((p1, p2))

        def _worker(pair: Tuple[float, float]) -> OptimizationCell:
            p1, p2 = pair
            return self.evaluate_cell(
                df=df,
                strategy_name=strategy_name,
                param1_name=param1.name,
                param1_val=p1,
                param2_name=param2.name,
                param2_val=p2,
                base_params=base_params,
                base_config=base_config
            )

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(_worker, tasks))

        return results, p1_ticks, p2_ticks

    def optimize_with_walk_forward(
        self,
        df: pd.DataFrame,
        strategy_name: str,
        param1: ParamSpec,
        param2: ParamSpec,
        walk_forward_split_pct: float = 70.0,
        target_metric: str = "sharpe_ratio",
        base_params: Optional[Dict[str, Any]] = None,
        base_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Complete workflow: Split IS/OOS, run grid on IS, analyze stability, validate on OOS."""
        start_time = time.time()
        base_params = base_params or {}
        base_config = base_config or {}

        # 1. Chronological Walk-Forward Split
        is_df, oos_df, split_date = WalkForwardSplitter.split(df, walk_forward_split_pct)

        # 2. In-Sample Grid Search
        is_cells, p1_ticks, p2_ticks = self.run_grid(
            df=is_df,
            strategy_name=strategy_name,
            param1=param1,
            param2=param2,
            base_params=base_params,
            base_config=base_config
        )

        # 3. 3x3 Plateau Stability Analysis on IS Matrix
        stability = StabilityAnalyzer.evaluate(
            cells=is_cells,
            param1_ticks=p1_ticks,
            param2_ticks=p2_ticks,
            target_metric=target_metric
        )

        # 4. Out-of-Sample Validation using Best Discovered Parameters
        best_p1 = stability.optimal_param1
        best_p2 = stability.optimal_param2

        # Find IS best cell
        is_best_cell = next(c for c in is_cells if c.param1_val == best_p1 and c.param2_val == best_p2)

        # Run OOS evaluation
        oos_cell = self.evaluate_cell(
            df=oos_df,
            strategy_name=strategy_name,
            param1_name=param1.name,
            param1_val=best_p1,
            param2_name=param2.name,
            param2_val=best_p2,
            base_params=base_params,
            base_config=base_config
        )

        # 5. Compute Walk-Forward Efficiency (WFE)
        wfe = WalkForwardSplitter.calculate_wfe(
            is_return=is_best_cell.net_pnl,
            oos_return=oos_cell.net_pnl
        )

        walk_forward = WalkForwardResult(
            in_sample_net_pnl=is_best_cell.net_pnl,
            in_sample_sharpe=is_best_cell.sharpe_ratio,
            out_of_sample_net_pnl=oos_cell.net_pnl,
            out_of_sample_sharpe=oos_cell.sharpe_ratio,
            walk_forward_efficiency=wfe,
            split_date=split_date,
            is_split_pct=walk_forward_split_pct
        )

        execution_ms = round((time.time() - start_time) * 1000.0, 2)

        best_params_dict = dict(base_params)
        best_params_dict[param1.name] = best_p1
        best_params_dict[param2.name] = best_p2

        return {
            "strategy": strategy_name,
            "param1_name": param1.name,
            "param2_name": param2.name,
            "param1_ticks": p1_ticks,
            "param2_ticks": p2_ticks,
            "total_combinations": len(is_cells),
            "execution_time_ms": execution_ms,
            "best_params": best_params_dict,
            "stability": stability,
            "walk_forward": walk_forward,
            "matrix": is_cells
        }
