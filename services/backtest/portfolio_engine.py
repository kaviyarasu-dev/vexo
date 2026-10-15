"""
Portfolio / Multi-Stock Basket Backtesting Engine.
Executes multi-asset quantitative strategies across synchronized chronological bars,
managing shared capital allocation, signal contention ranking, and cross-asset analytics.
"""

from typing import Dict, List, Optional, Any, Callable
import math
import pandas as pd
from services.backtest.cost_model import IndianEquityCostModel
from services.backtest.allocation import AllocationModel, EqualWeightAllocator, create_allocator
from services.backtest.portfolio_broker import PortfolioBroker
from services.backtest.metrics import PerformanceCalculator


class SignalContentionResolver:
    """
    Ranks competing BUY signals when candidate opportunities exceed available portfolio slots.
    """

    @staticmethod
    def rank_candidates(
        candidates: List[Dict[str, Any]],
        metric: str = "AUTO",
    ) -> List[Dict[str, Any]]:
        """
        Sort candidate symbols according to the selected ranking policy.

        Args:
            candidates: List of dicts with keys {'symbol', 'bar', 'rank_value'}.
            metric: 'AUTO', 'RSI_OVERSOLD', 'ROC_MOMENTUM', 'VOLUME_SURGE'.

        Returns:
            Sorted list of candidates in priority order.
        """
        if not candidates or len(candidates) <= 1:
            return candidates

        mode = (metric or "AUTO").upper()

        if mode == "RSI_OVERSOLD":
            # Lowest RSI first (deepest oversold)
            return sorted(candidates, key=lambda c: float(c.get("rank_value", c["bar"].get("rsi", 50.0))))

        elif mode in ("ROC_MOMENTUM", "MOMENTUM"):
            # Highest Rate of Change / momentum first
            return sorted(candidates, key=lambda c: float(c.get("rank_value", c["bar"].get("roc", 0.0))), reverse=True)

        elif mode == "VOLUME_SURGE":
            # Highest volume ratio first
            return sorted(candidates, key=lambda c: float(c.get("rank_value", c["bar"].get("volume_ratio", 1.0))), reverse=True)

        else:
            # AUTO: inspect available indicator columns
            first_bar = candidates[0]["bar"]
            if "rsi" in first_bar:
                return sorted(candidates, key=lambda c: float(c["bar"].get("rsi", 50.0)))
            elif "roc" in first_bar:
                return sorted(candidates, key=lambda c: float(c["bar"].get("roc", 0.0)), reverse=True)
            elif "volume_ratio" in first_bar:
                return sorted(candidates, key=lambda c: float(c["bar"].get("volume_ratio", 1.0)), reverse=True)
            else:
                # Deterministic fallback by symbol ticker
                return sorted(candidates, key=lambda c: c["symbol"])


class PortfolioEngine:
    """
    High-performance chronological simulation engine for multi-asset stock baskets.
    """

    def __init__(
        self,
        universe_data: Dict[str, pd.DataFrame],
        initial_capital: float = 1000000.0,
        max_open_positions: int = 10,
        allocator: Optional[AllocationModel] = None,
        ranking_metric: str = "AUTO",
        slippage_bps: float = 5.0,
        trade_type: str = "DELIVERY",
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
        benchmark_data: Optional[pd.DataFrame] = None,
    ):
        self.universe_data = universe_data
        self.initial_capital = float(initial_capital)
        self.max_open_positions = max(1, int(max_open_positions))
        self.allocator = allocator or EqualWeightAllocator()
        self.ranking_metric = ranking_metric
        self.slippage_bps = float(slippage_bps)
        self.benchmark_data = benchmark_data

        self.cost_model = IndianEquityCostModel(slippage_bps=self.slippage_bps)
        self.broker = PortfolioBroker(
            initial_capital=self.initial_capital,
            cost_model=self.cost_model,
            slippage_bps=self.slippage_bps,
            trade_type=trade_type,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
        )

    def run(
        self,
        strategy_evaluator: Optional[Callable[[str, pd.Series, Dict[str, Any]], Optional[int]]] = None,
    ) -> Dict[str, Any]:
        """
        Executes chronological multi-asset simulation.

        Args:
            strategy_evaluator: Optional custom callable(symbol, current_bar, context) -> signal (1=BUY, -1=SELL, 0=HOLD).
                                If None, expects a 'signal' column in each symbol's DataFrame.

        Returns:
            Consolidated backtest results dictionary.
        """
        if not self.universe_data:
            return self._empty_result()

        # 1. Normalize timestamps and build global timeline
        indexed_data = {}
        all_timestamps_set = set()

        for symbol, df in self.universe_data.items():
            if df.empty or "timestamp" not in df.columns:
                continue
            clean_df = df.copy()
            clean_df["timestamp_str"] = clean_df["timestamp"].apply(
                lambda ts: ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
            )
            # Ensure essential columns
            for col in ["open", "high", "low", "close"]:
                if col in clean_df.columns:
                    clean_df[col] = pd.to_numeric(clean_df[col], errors="coerce").fillna(0.0)

            clean_df = clean_df.sort_values("timestamp_str").drop_duplicates(subset=["timestamp_str"])
            indexed_data[symbol] = clean_df.set_index("timestamp_str")
            all_timestamps_set.update(clean_df["timestamp_str"].tolist())

        timeline = sorted(list(all_timestamps_set))
        if not timeline:
            return self._empty_result()

        # 2. Chronological bar iteration (Zero Lookahead Bias)
        current_equity = self.initial_capital

        for bar_idx, ts in enumerate(timeline):
            # Extract current bar for each active stock in the universe
            current_bars = {}
            for symbol, df in indexed_data.items():
                if ts in df.index:
                    row = df.loc[ts]
                    if isinstance(row, pd.DataFrame):
                        row = row.iloc[-1]
                    bar_dict = row.to_dict()
                    bar_dict["timestamp"] = ts
                    bar_dict["symbol"] = symbol
                    current_bars[symbol] = pd.Series(bar_dict)

            if not current_bars:
                continue

            # Step 2a: Fill pending orders at current bar's OPEN
            self.broker.process_orders(current_bars, bar_idx=bar_idx)

            # Step 2b: Check intraday Stop Loss / Take Profit triggers
            self.broker.check_risk_exits(current_bars, bar_idx=bar_idx)

            # Step 2c: Evaluate Strategy Signals at current bar's CLOSE
            candidate_buys: List[Dict[str, Any]] = []

            for symbol, bar in current_bars.items():
                if strategy_evaluator is not None:
                    signal = strategy_evaluator(symbol, bar, {"broker": self.broker})
                else:
                    signal = bar.get("signal", 0)

                # Convert numeric or string signals
                is_buy = signal in (1, "1", "BUY", "buy")
                is_sell = signal in (-1, "-1", "SELL", "sell")

                # Handle SELL: If currently holding the position, schedule exit for next open
                if is_sell and symbol in self.broker.open_positions:
                    pos = self.broker.open_positions[symbol]
                    if pos.qty > 0:
                        self.broker.order(symbol, "SELL", qty=pos.qty, reason="SIGNAL")

                # Handle BUY: Candidate if not already holding and not already pending order
                elif is_buy:
                    already_held = symbol in self.broker.open_positions
                    already_ordered = any(
                        o["symbol"] == symbol and o["side"] == "BUY" for o in self.broker.pending_orders
                    )
                    if not already_held and not already_ordered:
                        candidate_buys.append({
                            "symbol": symbol,
                            "bar": bar,
                            "rank_value": bar.get("rsi") or bar.get("roc") or bar.get("volume_ratio"),
                        })

            # Step 2d: Resolve Contention & Allocate Slots
            remaining_slots = self.max_open_positions - self.broker.open_position_count
            # Subtract pending BUY orders already placed this bar
            pending_buys_count = sum(1 for o in self.broker.pending_orders if o["side"] == "BUY")
            available_slots = max(0, remaining_slots - pending_buys_count)

            if candidate_buys and available_slots > 0:
                ranked_candidates = SignalContentionResolver.rank_candidates(
                    candidate_buys, metric=self.ranking_metric
                )
                selected_buys = ranked_candidates[:available_slots]

                # Allocate capital and place orders for next bar's OPEN
                for cand in selected_buys:
                    sym = cand["symbol"]
                    b = cand["bar"]
                    close_price = float(b["close"])
                    atr_val = b.get("atr")
                    if atr_val is not None:
                        try:
                            atr_val = float(atr_val)
                        except (ValueError, TypeError):
                            atr_val = None

                    qty = self.allocator.calculate_quantity(
                        symbol=sym,
                        price=close_price,
                        atr=atr_val,
                        available_cash=self.broker.cash,
                        remaining_slots=available_slots,
                        portfolio_value=current_equity,
                        slippage_rate=self.broker.slippage_factor,
                    )

                    if qty > 0:
                        self.broker.order(sym, "BUY", qty=qty, reason="SIGNAL")
                        available_slots = max(0, available_slots - 1)

            # Step 2e: Mark-to-Market Equity Snapshot at CLOSE
            current_equity = self.broker.update_equity(ts, current_bars)

        # 3. Post-timeline liquidation of remaining open positions at final bar
        if self.broker.open_positions and timeline:
            final_ts = timeline[-1]
            final_bars = {}
            for sym, df in indexed_data.items():
                if final_ts in df.index:
                    row = df.loc[final_ts]
                    if isinstance(row, pd.DataFrame):
                        row = row.iloc[-1]
                    final_bars[sym] = row

            self.broker.close_all_positions(
                timestamp=final_ts,
                current_bars=final_bars,
                bar_idx=len(timeline) - 1,
                reason="END_OF_DATA",
            )
            self.broker.update_equity(final_ts, final_bars)

        # 4. Generate consolidated metrics & analytics
        return self._generate_report(timeline)

    def _generate_report(self, timeline: List[str]) -> Dict[str, Any]:
        """Calculates institutional portfolio-level KPIs, asset contributions, and monthly matrix."""
        curve = self.broker.equity_curve
        final_equity = curve[-1]["equity"] if curve else self.initial_capital
        net_profit = round(final_equity - self.initial_capital, 2)
        return_pct = round((net_profit / self.initial_capital) * 100.0, 2)

        # CAGR Calculation
        days = max(1, len(timeline))
        years = days / 252.0
        cagr = PerformanceCalculator.calculate_cagr(self.initial_capital, final_equity, years)

        # Drawdown Series
        equity_values = [p["equity"] for p in curve] if curve else [self.initial_capital]
        max_dd = PerformanceCalculator.calculate_max_drawdown(equity_values)

        # Daily Returns, Sharpe, Sortino
        daily_returns = []
        for i in range(1, len(equity_values)):
            prev = equity_values[i - 1]
            curr = equity_values[i]
            r = (curr - prev) / prev if prev > 0 else 0.0
            daily_returns.append(r)

        sharpe = PerformanceCalculator.calculate_sharpe(daily_returns, periods_per_year=252)
        sortino = PerformanceCalculator.calculate_sortino(daily_returns, periods_per_year=252)

        # Trade Statistics
        closed_trades = self.broker.closed_trades
        total_trades = len(closed_trades)
        winning_trades = [t for t in closed_trades if t["net_pnl"] > 0]
        losing_trades = [t for t in closed_trades if t["net_pnl"] < 0]
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = round((win_count / total_trades * 100.0), 2) if total_trades > 0 else 0.0

        total_gross_wins = sum(t["gross_pnl"] for t in winning_trades)
        total_gross_losses = abs(sum(t["gross_pnl"] for t in losing_trades))
        profit_factor = round(total_gross_wins / total_gross_losses, 2) if total_gross_losses > 0 else (99.0 if total_gross_wins > 0 else 0.0)

        # Exposure / Cash Drag Ratio
        avg_exposure = sum(p.get("exposure_ratio", 0.0) for p in curve) / len(curve) if curve else 0.0

        # Benchmark Comparison
        benchmark_curve = self._compute_benchmark_curve(timeline)
        benchmark_cagr = 0.0
        benchmark_return_pct = 0.0
        if benchmark_curve:
            b_start = benchmark_curve[0]["value"]
            b_end = benchmark_curve[-1]["value"]
            benchmark_return_pct = round(((b_end - b_start) / b_start) * 100.0, 2) if b_start > 0 else 0.0
            benchmark_cagr = PerformanceCalculator.calculate_cagr(b_start, b_end, years)

        # Asset Contribution Breakdown
        asset_contributions = self._compute_asset_contributions()

        # Monthly Returns Matrix
        monthly_returns = self._compute_monthly_returns(curve)

        return {
            "initial_capital": self.initial_capital,
            "final_equity": round(final_equity, 2),
            "net_profit": net_profit,
            "return_pct": return_pct,
            "cagr": round(cagr * 100.0, 2),
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sortino, 2),
            "max_drawdown": round(max_dd * 100.0, 2),
            "total_trades": total_trades,
            "winning_trades": win_count,
            "losing_trades": loss_count,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_statutory_costs": round(self.broker.total_fees, 2),
            "avg_exposure_ratio": round(avg_exposure * 100.0, 2),
            "benchmark_cagr": round(benchmark_cagr * 100.0, 2),
            "benchmark_return_pct": benchmark_return_pct,
            "equity_curve": curve,
            "benchmark_curve": benchmark_curve,
            "asset_contributions": asset_contributions,
            "monthly_returns": monthly_returns,
            "trades": closed_trades,
        }

    def _compute_asset_contributions(self) -> List[Dict[str, Any]]:
        """Calculates alpha and trade metrics for each universe constituent."""
        trades_by_symbol = {}
        for t in self.broker.closed_trades:
            sym = t["symbol"]
            trades_by_symbol.setdefault(sym, []).append(t)

        contributions = []
        for symbol in self.universe_data.keys():
            sym_trades = trades_by_symbol.get(symbol, [])
            count = len(sym_trades)
            wins = len([t for t in sym_trades if t["net_pnl"] > 0])
            win_rate = round((wins / count * 100.0), 2) if count > 0 else 0.0
            net_pnl = round(sum(t["net_pnl"] for t in sym_trades), 2)
            alpha_contrib = round((net_pnl / self.initial_capital) * 100.0, 2)

            contributions.append({
                "symbol": symbol,
                "trade_count": count,
                "win_rate": win_rate,
                "net_pnl": net_pnl,
                "alpha_contribution_pct": alpha_contrib,
            })

        # Sort descending by net P&L contribution
        return sorted(contributions, key=lambda c: c["net_pnl"], reverse=True)

    def _compute_benchmark_curve(self, timeline: List[str]) -> List[Dict[str, Any]]:
        """Normalizes benchmark data to initial_capital across the backtest timeline."""
        if self.benchmark_data is None or self.benchmark_data.empty:
            return []

        df = self.benchmark_data.copy()
        df["ts_str"] = df["timestamp"].apply(lambda t: t.isoformat() if hasattr(t, "isoformat") else str(t))
        df = df.set_index("ts_str")

        curve = []
        first_close = None

        for ts in timeline:
            if ts in df.index:
                row = df.loc[ts]
                close = float(row["close"] if not isinstance(row, pd.DataFrame) else row["close"].iloc[-1])
                if first_close is None and close > 0:
                    first_close = close
                norm_val = (close / first_close) * self.initial_capital if first_close else self.initial_capital
                curve.append({"timestamp": ts, "value": round(norm_val, 2)})
            elif curve:
                curve.append({"timestamp": ts, "value": curve[-1]["value"]})
            else:
                curve.append({"timestamp": ts, "value": self.initial_capital})

        return curve

    def _compute_monthly_returns(self, curve: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Groups equity curve points by Year and Month to produce a return heatmap matrix."""
        if not curve or len(curve) < 2:
            return {}

        monthly_buckets: Dict[str, List[float]] = {}
        for p in curve:
            ts = p["timestamp"]
            year_month = ts[:7]  # YYYY-MM
            monthly_buckets.setdefault(year_month, []).append(p["equity"])

        matrix: Dict[str, Dict[str, float]] = {}
        prev_close = self.initial_capital

        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        for ym in sorted(monthly_buckets.keys()):
            parts = ym.split("-")
            if len(parts) != 2:
                continue
            year, m_num = parts[0], int(parts[1])
            m_label = month_names[m_num - 1]

            month_close = monthly_buckets[ym][-1]
            m_return = ((month_close - prev_close) / prev_close) * 100.0 if prev_close > 0 else 0.0

            matrix.setdefault(year, {})[m_label] = round(m_return, 2)
            prev_close = month_close

        return matrix

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "initial_capital": self.initial_capital,
            "final_equity": self.initial_capital,
            "net_profit": 0.0,
            "return_pct": 0.0,
            "cagr": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_statutory_costs": 0.0,
            "avg_exposure_ratio": 0.0,
            "benchmark_cagr": 0.0,
            "benchmark_return_pct": 0.0,
            "equity_curve": [],
            "benchmark_curve": [],
            "asset_contributions": [],
            "monthly_returns": {},
            "trades": [],
        }
