"""
Portfolio Allocation and Position Sizing Models.
Supports Equal Weight, Volatility-Adjusted (Inverse ATR), and Fixed Amount sizing.
"""

from abc import ABC, abstractmethod
from typing import Optional


class AllocationModel(ABC):
    """Abstract Base Class for portfolio position sizing algorithms."""

    @abstractmethod
    def calculate_quantity(
        self,
        symbol: str,
        price: float,
        atr: Optional[float],
        available_cash: float,
        remaining_slots: int,
        portfolio_value: float,
        slippage_rate: float = 0.0,
    ) -> int:
        """
        Calculate integer share quantity to purchase.

        Args:
            symbol: Stock ticker symbol.
            price: Current or expected execution price (unadjusted).
            atr: 14-period Average True Range volatility (if available).
            available_cash: Current unallocated cash in portfolio.
            remaining_slots: Available open position slots (max_positions - current_positions).
            portfolio_value: Total MTM portfolio equity (cash + open positions).
            slippage_rate: Estimated slippage factor (e.g. 0.0005 for 5 bps).

        Returns:
            Integer number of shares to buy (>= 0).
        """
        pass


class EqualWeightAllocator(AllocationModel):
    """
    Allocates capital equally across available slots.
    Either dynamically based on available_cash / remaining_slots,
    or fixed percentage of total portfolio equity.
    """

    def __init__(self, weight_pct: Optional[float] = None):
        """
        Args:
            weight_pct: Optional target % of portfolio value per position (e.g. 10.0 for 10%).
                        If None, divides available cash evenly among remaining slots.
        """
        self.weight_pct = weight_pct

    def calculate_quantity(
        self,
        symbol: str,
        price: float,
        atr: Optional[float],
        available_cash: float,
        remaining_slots: int,
        portfolio_value: float,
        slippage_rate: float = 0.0,
    ) -> int:
        if price <= 0 or available_cash <= 0 or remaining_slots <= 0:
            return 0

        effective_price = price * (1.0 + slippage_rate)
        if effective_price <= 0:
            return 0

        if self.weight_pct is not None and self.weight_pct > 0:
            target_capital = portfolio_value * (self.weight_pct / 100.0)
            allocated_capital = min(available_cash, target_capital)
        else:
            allocated_capital = available_cash / float(remaining_slots)

        qty = int(allocated_capital // effective_price)
        return max(0, qty)


class InverseATRAllocator(AllocationModel):
    """
    Volatility-adjusted position sizing (Inverse ATR).
    Higher volatility stocks receive smaller position sizes; lower volatility stocks receive larger sizes.
    Bounded by maximum capital per slot to prevent cash depletion.
    """

    def __init__(self, risk_pct: float = 1.0, atr_multiplier: float = 2.0):
        """
        Args:
            risk_pct: Max % of portfolio equity to risk on a single trade (default 1.0%).
            atr_multiplier: Multiple of ATR representing the stop distance (default 2.0x).
        """
        self.risk_pct = risk_pct
        self.atr_multiplier = atr_multiplier

    def calculate_quantity(
        self,
        symbol: str,
        price: float,
        atr: Optional[float],
        available_cash: float,
        remaining_slots: int,
        portfolio_value: float,
        slippage_rate: float = 0.0,
    ) -> int:
        if price <= 0 or available_cash <= 0 or remaining_slots <= 0:
            return 0

        effective_price = price * (1.0 + slippage_rate)
        if effective_price <= 0:
            return 0

        max_slot_capital = available_cash / float(remaining_slots)
        max_qty_by_cash = int(max_slot_capital // effective_price)

        # If ATR is missing or invalid, fall back to equal weight cash split
        if atr is None or atr <= 0:
            return max(0, max_qty_by_cash)

        risk_budget = portfolio_value * (self.risk_pct / 100.0)
        risk_per_share = atr * self.atr_multiplier

        if risk_per_share <= 0:
            return max(0, max_qty_by_cash)

        target_qty = int(risk_budget // risk_per_share)
        final_qty = min(target_qty, max_qty_by_cash)
        return max(0, final_qty)


class FixedAmountAllocator(AllocationModel):
    """
    Allocates a fixed rupee amount per trade slot (e.g. ₹1,00,000 per stock).
    Capped by currently available unallocated cash.
    """

    def __init__(self, fixed_amount: float = 100000.0):
        """
        Args:
            fixed_amount: Rupee amount to allocate per position.
        """
        self.fixed_amount = fixed_amount

    def calculate_quantity(
        self,
        symbol: str,
        price: float,
        atr: Optional[float],
        available_cash: float,
        remaining_slots: int,
        portfolio_value: float,
        slippage_rate: float = 0.0,
    ) -> int:
        if price <= 0 or available_cash <= 0 or remaining_slots <= 0:
            return 0

        effective_price = price * (1.0 + slippage_rate)
        if effective_price <= 0:
            return 0

        target_capital = min(available_cash, self.fixed_amount)
        qty = int(target_capital // effective_price)
        return max(0, qty)


def create_allocator(model_name: str, **kwargs) -> AllocationModel:
    """Factory helper to instantiate an AllocationModel by name."""
    name = (model_name or "EQUAL_WEIGHT").upper()
    if name == "EQUAL_WEIGHT":
        weight_pct = kwargs.get("weight_pct")
        if weight_pct is not None:
            weight_pct = float(weight_pct)
        return EqualWeightAllocator(weight_pct=weight_pct)
    elif name == "INVERSE_ATR":
        risk_pct = float(kwargs.get("risk_pct", 1.0))
        atr_multiplier = float(kwargs.get("atr_multiplier", 2.0))
        return InverseATRAllocator(risk_pct=risk_pct, atr_multiplier=atr_multiplier)
    elif name == "FIXED_AMOUNT":
        fixed_amount = float(kwargs.get("fixed_amount", 100000.0))
        return FixedAmountAllocator(fixed_amount=fixed_amount)
    else:
        raise ValueError(f"Unknown allocation model: {model_name}. Supported: EQUAL_WEIGHT, INVERSE_ATR, FIXED_AMOUNT")
