"""
Unit Tests for Portfolio / Multi-Stock Basket Backtest Engine, Allocator, and PortfolioBroker.
Validates multi-asset chronological synchronization, position sizing models, contention ranking,
lookahead bias prevention, FIFO lot matching, and Indian statutory tax deductions.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from core.exceptions import LookaheadBiasError
from services.backtest.cost_model import IndianEquityCostModel
from services.backtest.allocation import (
    EqualWeightAllocator,
    InverseATRAllocator,
    FixedAmountAllocator,
    create_allocator,
)
from services.backtest.portfolio_broker import PortfolioBroker, PortfolioPosition
from services.backtest.portfolio_engine import PortfolioEngine, SignalContentionResolver


# ============================================================================
# 1. Position Sizing & Allocation Models Tests
# ============================================================================

def test_equal_weight_allocator_dynamic_cash_split():
    allocator = EqualWeightAllocator()
    # ₹10,00,000 cash, 5 remaining slots -> ₹2,00,000 per slot
    # Price = ₹1,000, 0 slippage -> 200 shares
    qty = allocator.calculate_quantity(
        symbol="NSE:RELIANCE-EQ",
        price=1000.0,
        atr=25.0,
        available_cash=1000000.0,
        remaining_slots=5,
        portfolio_value=1000000.0,
        slippage_rate=0.0,
    )
    assert qty == 200


def test_equal_weight_allocator_fixed_weight_pct():
    # Target 15% of portfolio value per slot
    allocator = EqualWeightAllocator(weight_pct=15.0)
    # Portfolio = ₹10,00,000 -> ₹1,50,000 allocation. Price = ₹500 -> 300 shares
    qty = allocator.calculate_quantity(
        symbol="NSE:TCS-EQ",
        price=500.0,
        atr=15.0,
        available_cash=1000000.0,
        remaining_slots=3,
        portfolio_value=1000000.0,
        slippage_rate=0.0,
    )
    assert qty == 300


def test_equal_weight_allocator_slippage_and_cash_cap():
    allocator = EqualWeightAllocator()
    # Price = ₹1000, Slippage 5 bps (0.0005) -> Effective price = ₹1000.50
    # Available cash = ₹50,000, remaining slots = 1 -> ₹50,000 // 1000.50 = 49 shares
    qty = allocator.calculate_quantity(
        symbol="NSE:INFY-EQ",
        price=1000.0,
        atr=20.0,
        available_cash=50000.0,
        remaining_slots=1,
        portfolio_value=50000.0,
        slippage_rate=0.0005,
    )
    assert qty == 49


def test_equal_weight_allocator_zero_or_negative():
    allocator = EqualWeightAllocator()
    assert allocator.calculate_quantity("S", price=0.0, atr=10.0, available_cash=100000.0, remaining_slots=2, portfolio_value=100000.0) == 0
    assert allocator.calculate_quantity("S", price=100.0, atr=10.0, available_cash=0.0, remaining_slots=2, portfolio_value=100000.0) == 0
    assert allocator.calculate_quantity("S", price=100.0, atr=10.0, available_cash=100000.0, remaining_slots=0, portfolio_value=100000.0) == 0


def test_inverse_atr_allocator_volatility_scaling():
    # 1% risk on ₹10,00,000 = ₹10,000 risk budget. ATR multiplier = 2.0x
    allocator = InverseATRAllocator(risk_pct=1.0, atr_multiplier=2.0)

    # Stock A (Low volatility): ATR = 20 -> Stop distance = ₹40 -> Target = 10000 // 40 = 250 shares
    qty_low_vol = allocator.calculate_quantity(
        symbol="NSE:LOWVOL-EQ",
        price=500.0,
        atr=20.0,
        available_cash=1000000.0,
        remaining_slots=2,
        portfolio_value=1000000.0,
    )
    assert qty_low_vol == 250

    # Stock B (High volatility): ATR = 50 -> Stop distance = ₹100 -> Target = 10000 // 100 = 100 shares
    qty_high_vol = allocator.calculate_quantity(
        symbol="NSE:HIGHVOL-EQ",
        price=500.0,
        atr=50.0,
        available_cash=1000000.0,
        remaining_slots=2,
        portfolio_value=1000000.0,
    )
    assert qty_high_vol == 100
    assert qty_low_vol > qty_high_vol


def test_inverse_atr_allocator_fallback_and_cash_cap():
    allocator = InverseATRAllocator(risk_pct=1.0, atr_multiplier=2.0)
    # If ATR is None, falls back to slot cash cap
    # Cash = ₹1,00,000, 2 slots -> ₹50,000. Price = ₹1,000 -> 50 shares
    qty = allocator.calculate_quantity(
        symbol="NSE:NOATR-EQ",
        price=1000.0,
        atr=None,
        available_cash=100000.0,
        remaining_slots=2,
        portfolio_value=100000.0,
    )
    assert qty == 50


def test_fixed_amount_allocator():
    allocator = FixedAmountAllocator(fixed_amount=200000.0)
    # Price = ₹2,000 -> ₹2,00,000 // 2000 = 100 shares
    qty = allocator.calculate_quantity(
        symbol="NSE:FIXED-EQ",
        price=2000.0,
        atr=30.0,
        available_cash=1000000.0,
        remaining_slots=5,
        portfolio_value=1000000.0,
    )
    assert qty == 100

    # Cash constraint: Available cash only ₹75,000 < ₹2,00,000 -> ₹75,000 // 2000 = 37 shares
    qty_constrained = allocator.calculate_quantity(
        symbol="NSE:FIXED-EQ",
        price=2000.0,
        atr=30.0,
        available_cash=75000.0,
        remaining_slots=5,
        portfolio_value=1000000.0,
    )
    assert qty_constrained == 37


def test_create_allocator_factory():
    a1 = create_allocator("EQUAL_WEIGHT", weight_pct=10.0)
    assert isinstance(a1, EqualWeightAllocator)
    assert a1.weight_pct == 10.0

    a2 = create_allocator("INVERSE_ATR", risk_pct=1.5, atr_multiplier=3.0)
    assert isinstance(a2, InverseATRAllocator)
    assert a2.risk_pct == 1.5
    assert a2.atr_multiplier == 3.0

    a3 = create_allocator("FIXED_AMOUNT", fixed_amount=50000.0)
    assert isinstance(a3, FixedAmountAllocator)
    assert a3.fixed_amount == 50000.0

    with pytest.raises(ValueError):
        create_allocator("NON_EXISTENT_MODEL")


# ============================================================================
# 2. Signal Contention Resolver Tests
# ============================================================================

def test_signal_contention_resolver_rsi():
    candidates = [
        {"symbol": "NSE:A", "bar": {"rsi": 28.5}, "rank_value": 28.5},
        {"symbol": "NSE:B", "bar": {"rsi": 18.2}, "rank_value": 18.2},
        {"symbol": "NSE:C", "bar": {"rsi": 24.0}, "rank_value": 24.0},
    ]
    ranked = SignalContentionResolver.rank_candidates(candidates, metric="RSI_OVERSOLD")
    # Lowest RSI first: B (18.2), C (24.0), A (28.5)
    assert [c["symbol"] for c in ranked] == ["NSE:B", "NSE:C", "NSE:A"]


def test_signal_contention_resolver_roc_momentum():
    candidates = [
        {"symbol": "NSE:A", "bar": {"roc": 4.5}, "rank_value": 4.5},
        {"symbol": "NSE:B", "bar": {"roc": 15.2}, "rank_value": 15.2},
        {"symbol": "NSE:C", "bar": {"roc": -2.0}, "rank_value": -2.0},
    ]
    ranked = SignalContentionResolver.rank_candidates(candidates, metric="ROC_MOMENTUM")
    # Highest ROC first: B (15.2), A (4.5), C (-2.0)
    assert [c["symbol"] for c in ranked] == ["NSE:B", "NSE:A", "NSE:C"]


def test_signal_contention_resolver_volume_surge():
    candidates = [
        {"symbol": "NSE:A", "bar": {"volume_ratio": 1.1}, "rank_value": 1.1},
        {"symbol": "NSE:B", "bar": {"volume_ratio": 3.8}, "rank_value": 3.8},
        {"symbol": "NSE:C", "bar": {"volume_ratio": 2.2}, "rank_value": 2.2},
    ]
    ranked = SignalContentionResolver.rank_candidates(candidates, metric="VOLUME_SURGE")
    # Highest volume ratio first: B (3.8), C (2.2), A (1.1)
    assert [c["symbol"] for c in ranked] == ["NSE:B", "NSE:C", "NSE:A"]


def test_signal_contention_resolver_auto_fallback():
    candidates = [
        {"symbol": "NSE:ZED", "bar": {}},
        {"symbol": "NSE:ALPHA", "bar": {}},
        {"symbol": "NSE:BETA", "bar": {}},
    ]
    ranked = SignalContentionResolver.rank_candidates(candidates, metric="AUTO")
    assert [c["symbol"] for c in ranked] == ["NSE:ALPHA", "NSE:BETA", "NSE:ZED"]


# ============================================================================
# 3. PortfolioBroker Tests
# ============================================================================

def test_portfolio_broker_lookahead_bias_guard():
    broker = PortfolioBroker(initial_capital=1000000.0, cost_model=IndianEquityCostModel())
    with pytest.raises(LookaheadBiasError):
        broker.order("NSE:RELIANCE-EQ", "BUY", 100, execution_price=2500.0)


def test_portfolio_broker_buy_and_sell_fifo_matching():
    cost_model = IndianEquityCostModel(slippage_bps=0.0)
    broker = PortfolioBroker(initial_capital=1000000.0, cost_model=cost_model, slippage_bps=0.0)

    # Bar 0: Schedule BUY for 100 shares of RELIANCE
    broker.order("NSE:RELIANCE-EQ", "BUY", 100)

    # Bar 1: Process orders at OPEN = ₹2,000
    bar_1 = {
        "NSE:RELIANCE-EQ": pd.Series({
            "timestamp": "2023-01-02",
            "open": 2000.0,
            "high": 2050.0,
            "low": 1990.0,
            "close": 2040.0,
        })
    }
    broker.process_orders(bar_1, bar_idx=1)

    assert "NSE:RELIANCE-EQ" in broker.open_positions
    pos = broker.open_positions["NSE:RELIANCE-EQ"]
    assert pos.qty == 100
    assert pos.entry_price == 2000.0
    # Cash reduced by trade value (₹2,00,000) + buy taxes
    assert broker.cash < 800000.0

    # Bar 2: Schedule SELL for 100 shares of RELIANCE
    broker.order("NSE:RELIANCE-EQ", "SELL", 100)

    # Bar 3: Process sell order at OPEN = ₹2,200
    bar_3 = {
        "NSE:RELIANCE-EQ": pd.Series({
            "timestamp": "2023-01-04",
            "open": 2200.0,
            "high": 2220.0,
            "low": 2180.0,
            "close": 2210.0,
        })
    }
    broker.process_orders(bar_3, bar_idx=3)

    assert "NSE:RELIANCE-EQ" not in broker.open_positions
    assert len(broker.closed_trades) == 1
    trade = broker.closed_trades[0]
    assert trade["symbol"] == "NSE:RELIANCE-EQ"
    assert trade["qty"] == 100
    assert trade["entry_price"] == 2000.0
    assert trade["exit_price"] == 2200.0
    assert trade["gross_pnl"] == 20000.0  # (2200 - 2000) * 100
    assert trade["fees"] > 0.0
    assert trade["net_pnl"] < trade["gross_pnl"]
    assert broker.cash > 1000000.0  # Profitable net return


def test_portfolio_broker_stop_loss_trigger():
    cost_model = IndianEquityCostModel(slippage_bps=0.0)
    broker = PortfolioBroker(
        initial_capital=500000.0,
        cost_model=cost_model,
        slippage_bps=0.0,
        stop_loss_pct=5.0,  # 5% SL
    )

    broker.order("NSE:INFY-EQ", "BUY", 100)
    bar_1 = {
        "NSE:INFY-EQ": pd.Series({
            "timestamp": "2023-01-02",
            "open": 1000.0,
            "high": 1020.0,
            "low": 990.0,
            "close": 1010.0,
        })
    }
    broker.process_orders(bar_1, bar_idx=1)
    assert "NSE:INFY-EQ" in broker.open_positions

    # Bar 2: Low drops to ₹940 (Breaches ₹950 SL threshold)
    bar_2 = {
        "NSE:INFY-EQ": pd.Series({
            "timestamp": "2023-01-03",
            "open": 980.0,
            "high": 985.0,
            "low": 940.0,
            "close": 945.0,
        })
    }
    broker.check_risk_exits(bar_2, bar_idx=2)

    # Position closed automatically on Stop Loss
    assert "NSE:INFY-EQ" not in broker.open_positions
    assert len(broker.closed_trades) == 1
    assert broker.closed_trades[0]["exit_reason"] == "STOP_LOSS"
    assert broker.closed_trades[0]["exit_price"] <= 950.0


def test_portfolio_broker_take_profit_trigger():
    cost_model = IndianEquityCostModel(slippage_bps=0.0)
    broker = PortfolioBroker(
        initial_capital=500000.0,
        cost_model=cost_model,
        slippage_bps=0.0,
        take_profit_pct=10.0,  # 10% TP
    )

    broker.order("NSE:TCS-EQ", "BUY", 50)
    bar_1 = {
        "NSE:TCS-EQ": pd.Series({
            "timestamp": "2023-01-02",
            "open": 3000.0,
            "high": 3050.0,
            "low": 2990.0,
            "close": 3020.0,
        })
    }
    broker.process_orders(bar_1, bar_idx=1)

    # Bar 2: High touches ₹3350 (Breaches ₹3300 TP threshold)
    bar_2 = {
        "NSE:TCS-EQ": pd.Series({
            "timestamp": "2023-01-03",
            "open": 3100.0,
            "high": 3350.0,
            "low": 3090.0,
            "close": 3320.0,
        })
    }
    broker.check_risk_exits(bar_2, bar_idx=2)

    assert "NSE:TCS-EQ" not in broker.open_positions
    assert len(broker.closed_trades) == 1
    assert broker.closed_trades[0]["exit_reason"] == "TAKE_PROFIT"
    assert broker.closed_trades[0]["exit_price"] >= 3300.0


def test_portfolio_broker_insufficient_cash_downsizing():
    cost_model = IndianEquityCostModel(slippage_bps=0.0)
    # Only ₹50,000 cash available
    broker = PortfolioBroker(initial_capital=50000.0, cost_model=cost_model, slippage_bps=0.0)

    # Request 100 shares of ₹1,000 stock = ₹1,00,000 (exceeds cash)
    broker.order("NSE:BIG-EQ", "BUY", 100)
    bar = {
        "NSE:BIG-EQ": pd.Series({
            "timestamp": "2023-01-02",
            "open": 1000.0,
            "high": 1010.0,
            "low": 990.0,
            "close": 1005.0,
        })
    }
    broker.process_orders(bar, bar_idx=1)

    # Automatically downsized to affordable shares without overdraft
    assert "NSE:BIG-EQ" in broker.open_positions
    pos = broker.open_positions["NSE:BIG-EQ"]
    assert pos.qty < 100
    assert pos.qty >= 40
    assert broker.cash >= 0.0  # Cash never negative!


# ============================================================================
# 4. End-to-End PortfolioEngine Simulation Tests
# ============================================================================

def _generate_synthetic_ohlcv(symbol: str, base_price: float, trend_pct: float, num_bars: int = 50) -> pd.DataFrame:
    """Helper to generate reproducible synthetic OHLCV data."""
    dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(num_bars)]
    prices = [base_price * (1.0 + trend_pct * (i / num_bars)) for i in range(num_bars)]

    data = []
    for i in range(num_bars):
        p = prices[i]
        data.append({
            "timestamp": dates[i].strftime("%Y-%m-%d"),
            "open": round(p * 0.995, 2),
            "high": round(p * 1.015, 2),
            "low": round(p * 0.985, 2),
            "close": round(p, 2),
            "volume": 100000 + i * 1000,
            "atr": round(p * 0.02, 2),
            "rsi": round(30.0 + (i % 40), 1),
            "roc": round((trend_pct * 100.0) / 2.0, 2),
            "volume_ratio": 1.2,
            "signal": 0,
        })
    return pd.DataFrame(data)


def test_portfolio_engine_multi_stock_simulation():
    # Universe of 3 stocks: Stock A, Stock B, Stock C
    df_a = _generate_synthetic_ohlcv("NSE:STOCK_A", base_price=100.0, trend_pct=0.20, num_bars=30)
    df_b = _generate_synthetic_ohlcv("NSE:STOCK_B", base_price=200.0, trend_pct=-0.10, num_bars=30)
    df_c = _generate_synthetic_ohlcv("NSE:STOCK_C", base_price=500.0, trend_pct=0.15, num_bars=30)

    # Strategy signals:
    # Bar 5: BUY Stock A and Stock B
    df_a.loc[5, "signal"] = 1
    df_b.loc[5, "signal"] = 1
    # Bar 15: SELL Stock A, BUY Stock C
    df_a.loc[15, "signal"] = -1
    df_c.loc[15, "signal"] = 1
    # Bar 22: SELL Stock B and Stock C
    df_b.loc[22, "signal"] = -1
    df_c.loc[22, "signal"] = -1

    universe = {
        "NSE:STOCK_A": df_a,
        "NSE:STOCK_B": df_b,
        "NSE:STOCK_C": df_c,
    }

    engine = PortfolioEngine(
        universe_data=universe,
        initial_capital=1000000.0,
        max_open_positions=2,  # Max 2 concurrent positions
        allocator=EqualWeightAllocator(),
        slippage_bps=5.0,
    )

    result = engine.run()

    assert result["initial_capital"] == 1000000.0
    assert result["total_trades"] >= 2
    assert len(result["equity_curve"]) == 30
    assert len(result["asset_contributions"]) == 3
    assert result["total_statutory_costs"] > 0.0

    # Verify asset contribution table structure
    contrib_symbols = [c["symbol"] for c in result["asset_contributions"]]
    assert "NSE:STOCK_A" in contrib_symbols
    assert "NSE:STOCK_B" in contrib_symbols
    assert "NSE:STOCK_C" in contrib_symbols

    # Verify trade records have all required fields
    for trade in result["trades"]:
        assert "symbol" in trade
        assert "entry_price" in trade
        assert "exit_price" in trade
        assert "gross_pnl" in trade
        assert "fees" in trade
        assert "net_pnl" in trade
        assert "holding_period_bars" in trade


def test_portfolio_engine_max_open_positions_contention():
    # Universe of 4 stocks
    universe = {
        f"NSE:STK_{i}": _generate_synthetic_ohlcv(f"NSE:STK_{i}", base_price=100.0 * (i + 1), trend_pct=0.05, num_bars=20)
        for i in range(4)
    }

    # All 4 stocks trigger BUY on bar 3
    universe["NSE:STK_0"].loc[3, "signal"] = 1
    universe["NSE:STK_0"].loc[3, "rsi"] = 15.0  # Deepest oversold

    universe["NSE:STK_1"].loc[3, "signal"] = 1
    universe["NSE:STK_1"].loc[3, "rsi"] = 22.0

    universe["NSE:STK_2"].loc[3, "signal"] = 1
    universe["NSE:STK_2"].loc[3, "rsi"] = 28.0

    universe["NSE:STK_3"].loc[3, "signal"] = 1
    universe["NSE:STK_3"].loc[3, "rsi"] = 29.0

    # Max concurrent positions = 2
    engine = PortfolioEngine(
        universe_data=universe,
        initial_capital=1000000.0,
        max_open_positions=2,
        ranking_metric="RSI_OVERSOLD",
    )

    result = engine.run()

    # Only top 2 RSI candidates (STK_0 with RSI 15.0 and STK_1 with RSI 22.0) should have been bought
    traded_symbols = set(t["symbol"] for t in result["trades"])
    assert "NSE:STK_0" in traded_symbols
    assert "NSE:STK_1" in traded_symbols
    assert "NSE:STK_2" not in traded_symbols
    assert "NSE:STK_3" not in traded_symbols


def test_portfolio_engine_empty_universe():
    engine = PortfolioEngine(universe_data={})
    result = engine.run()
    assert result["total_trades"] == 0
    assert result["final_equity"] == 1000000.0
    assert result["equity_curve"] == []
