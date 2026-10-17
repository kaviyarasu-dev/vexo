"""OrderBlock Levels Ladder and Liquidity Sweep Pools Engine.
Calculates zone level ladder (Z, S1-S4, R1-R4), live Risk-to-Reward (R:R), and detects equal high/low liquidity pools.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

from services.orderblock.zone_engine import OrderBlockZone, Candle5m

logger = logging.getLogger(__name__)


@dataclass
class LevelsLadder:
    z_price: float
    invalidation_price: float
    risk: float
    reward: float
    risk_reward_ratio: float
    s1: float
    s2: float
    s3: float
    s4: float
    r1: float
    r2: float
    r3: float
    r4: float


@dataclass
class LiquidityPool:
    pool_type: str  # "EQUAL_HIGHS" or "EQUAL_LOWS"
    price_level: float
    touches: int
    timestamps: List[datetime] = field(default_factory=list)
    variance_pct: float = 0.0


class OrderBlockLiquidityEngine:
    """Computes Fibonacci/structural level ladders, R:R metrics, and resting liquidity sweeps."""

    def compute_levels(
        self,
        zone: OrderBlockZone,
        day_high: float,
        day_low: float,
        current_price: float
    ) -> LevelsLadder:
        """Calculates institutional levels ladder and live R:R ratio for an active zone."""
        if zone.block_type == "BULLISH":
            z_price = zone.top_price
            inval = zone.invalidation_price
            risk = max(0.05, abs(z_price - inval))

            # Target levels
            r1 = z_price + 1.0 * risk
            # Map R2 to day's high or 2x risk extension
            r2 = max(day_high, z_price + 2.0 * risk) if day_high > z_price else (z_price + 2.0 * risk)
            r3 = z_price + 3.0 * risk
            r4 = z_price + 4.0 * risk

            # Stop / Invalidation ladder
            s1 = inval
            s2 = inval - 0.5 * risk
            s3 = inval - 1.0 * risk
            s4 = inval - 2.0 * risk

            reward = abs(r2 - z_price)
            rr = (reward / risk) if risk > 0 else 0.0

            return LevelsLadder(
                z_price=round(z_price, 2),
                invalidation_price=round(inval, 2),
                risk=round(risk, 2),
                reward=round(reward, 2),
                risk_reward_ratio=round(rr, 2),
                s1=round(s1, 2),
                s2=round(s2, 2),
                s3=round(s3, 2),
                s4=round(s4, 2),
                r1=round(r1, 2),
                r2=round(r2, 2),
                r3=round(r3, 2),
                r4=round(r4, 2)
            )

        else:  # BEARISH
            z_price = zone.bottom_price
            inval = zone.invalidation_price
            risk = max(0.05, abs(inval - z_price))

            # Invalidation ladder
            r1 = inval
            r2 = inval + 0.5 * risk
            r3 = inval + 1.0 * risk
            r4 = inval + 2.0 * risk

            # Downside targets
            s1 = z_price - 1.0 * risk
            # Map S2 to day's low or 2x risk extension
            s2 = min(day_low, z_price - 2.0 * risk) if (day_low < z_price and day_low > 0) else (z_price - 2.0 * risk)
            s3 = z_price - 3.0 * risk
            s4 = z_price - 4.0 * risk

            reward = abs(z_price - s2)
            rr = (reward / risk) if risk > 0 else 0.0

            return LevelsLadder(
                z_price=round(z_price, 2),
                invalidation_price=round(inval, 2),
                risk=round(risk, 2),
                reward=round(reward, 2),
                risk_reward_ratio=round(rr, 2),
                s1=round(s1, 2),
                s2=round(s2, 2),
                s3=round(s3, 2),
                s4=round(s4, 2),
                r1=round(r1, 2),
                r2=round(r2, 2),
                r3=round(r3, 2),
                r4=round(r4, 2)
            )

    def detect_liquidity_pools(
        self,
        symbol: str,
        candles: List[Candle5m],
        tolerance_pct: float = 0.001
    ) -> List[LiquidityPool]:
        """Scans for Equal Highs (EQH) and Equal Lows (EQL) within price tolerance (default 0.1%)."""
        if len(candles) < 2:
            return []

        pools: List[LiquidityPool] = []

        # Equal Highs clustering
        visited_highs = set()
        for i in range(len(candles)):
            if i in visited_highs:
                continue
            cluster_idxs = [i]
            h_base = candles[i].high

            for j in range(i + 1, len(candles)):
                h_comp = candles[j].high
                if h_base > 0:
                    diff = abs(h_base - h_comp) / h_base
                    if diff <= tolerance_pct:
                        cluster_idxs.append(j)

            if len(cluster_idxs) >= 2:
                visited_highs.update(cluster_idxs)
                cluster_highs = [candles[idx].high for idx in cluster_idxs]
                avg_high = sum(cluster_highs) / len(cluster_highs)
                variance = (max(cluster_highs) - min(cluster_highs)) / avg_high if avg_high > 0 else 0.0
                pools.append(LiquidityPool(
                    pool_type="EQUAL_HIGHS",
                    price_level=round(avg_high, 2),
                    touches=len(cluster_idxs),
                    timestamps=[candles[idx].timestamp for idx in cluster_idxs],
                    variance_pct=round(variance * 100, 3)
                ))

        # Equal Lows clustering
        visited_lows = set()
        for i in range(len(candles)):
            if i in visited_lows:
                continue
            cluster_idxs = [i]
            l_base = candles[i].low

            for j in range(i + 1, len(candles)):
                l_comp = candles[j].low
                if l_base > 0:
                    diff = abs(l_base - l_comp) / l_base
                    if diff <= tolerance_pct:
                        cluster_idxs.append(j)

            if len(cluster_idxs) >= 2:
                visited_lows.update(cluster_idxs)
                cluster_lows = [candles[idx].low for idx in cluster_idxs]
                avg_low = sum(cluster_lows) / len(cluster_lows)
                variance = (max(cluster_lows) - min(cluster_lows)) / avg_low if avg_low > 0 else 0.0
                pools.append(LiquidityPool(
                    pool_type="EQUAL_LOWS",
                    price_level=round(avg_low, 2),
                    touches=len(cluster_idxs),
                    timestamps=[candles[idx].timestamp for idx in cluster_idxs],
                    variance_pct=round(variance * 100, 3)
                ))

        return pools
