"""OrderBlock Boards & Picks Engine.
Maintains Top 20 Bullish/Bearish boards, minute-over-minute rank deltas, and Top 3 Picks with 2-sector cap.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
import pytz

from services.orderblock.strength_engine import StockStrengthMetric

IST = pytz.timezone("Asia/Kolkata")


@dataclass
class BoardItem:
    symbol: str
    sector: str
    score: float
    side: str
    rank: int
    prev_rank: Optional[int] = None
    rank_delta: int = 0
    is_new_top10: bool = False
    is_event_risk: bool = False
    current_price: float = 0.0
    day_move_pct: float = 0.0


@dataclass
class PickCandidate:
    symbol: str
    sector: str
    score: float
    side: str
    rank: int
    status: str  # "PICKED", "NOT PICKED: Sector Cap Exceeded", "NOT PICKED: Outside Top 3", "NOT PICKED: Event Risk Excluded"
    rule_reason: str = ""
    current_price: float = 0.0
    day_move_pct: float = 0.0


@dataclass
class BoardsSnapshot:
    timestamp: datetime
    bullish: List[BoardItem]
    bearish: List[BoardItem]
    bullish_picks: List[PickCandidate]
    bearish_picks: List[PickCandidate]


class OrderBlockBoardsEngine:
    """Manages Top 20 boards ranking, delta shifts, and algorithmic shortlist picks."""

    def __init__(self) -> None:
        self._prev_bullish_ranks: Dict[str, int] = {}
        self._prev_bearish_ranks: Dict[str, int] = {}

    def select_picks(
        self,
        metrics: List[StockStrengthMetric],
        side: str,
        max_picks: int = 3,
        max_per_sector: int = 2
    ) -> List[PickCandidate]:
        """Selects up to 3 picks enforcing a maximum 2 stocks per sector and event-risk exclusion."""
        candidates = [m for m in metrics if m.side == side and m.score > 0]
        # Sort descending by strength score
        candidates.sort(key=lambda x: x.score, reverse=True)

        picks: List[PickCandidate] = []
        sector_counts: Dict[str, int] = {}
        picked_count = 0

        for rank, item in enumerate(candidates, start=1):
            sec = item.sector or "General"
            
            # Event risk exclusion
            if item.is_event_risk:
                picks.append(PickCandidate(
                    symbol=item.symbol,
                    sector=sec,
                    score=item.score,
                    side=side,
                    rank=rank,
                    status="NOT PICKED: Event Risk Excluded",
                    rule_reason=item.event_risk_reason or "Abnormal drop detected",
                    current_price=item.current_price,
                    day_move_pct=item.day_move_pct
                ))
                continue

            current_sec_count = sector_counts.get(sec, 0)
            
            if picked_count < max_picks:
                if current_sec_count < max_per_sector:
                    # Qualified pick
                    sector_counts[sec] = current_sec_count + 1
                    picked_count += 1
                    picks.append(PickCandidate(
                        symbol=item.symbol,
                        sector=sec,
                        score=item.score,
                        side=side,
                        rank=rank,
                        status="PICKED",
                        rule_reason=f"Rank #{rank} | Sector {sec} ({sector_counts[sec]}/{max_per_sector})",
                        current_price=item.current_price,
                        day_move_pct=item.day_move_pct
                    ))
                else:
                    # Sector cap exceeded
                    picks.append(PickCandidate(
                        symbol=item.symbol,
                        sector=sec,
                        score=item.score,
                        side=side,
                        rank=rank,
                        status="NOT PICKED: Sector Cap Exceeded",
                        rule_reason=f"Sector '{sec}' already has {max_per_sector} picks",
                        current_price=item.current_price,
                        day_move_pct=item.day_move_pct
                    ))
            else:
                # Outside top picks
                picks.append(PickCandidate(
                    symbol=item.symbol,
                    sector=sec,
                    score=item.score,
                    side=side,
                    rank=rank,
                    status="NOT PICKED: Outside Top 3",
                    rule_reason=f"Rank #{rank} outside top {max_picks} allocation",
                    current_price=item.current_price,
                    day_move_pct=item.day_move_pct
                ))

        return picks

    def update_boards(self, metrics: List[StockStrengthMetric], top_n: int = 20) -> BoardsSnapshot:
        """Ranks Top N Bullish and Bearish equities, tracks rank deltas and flags new entrants."""
        bullish_metrics = [m for m in metrics if m.side == "BULLISH" and m.score > 0]
        bearish_metrics = [m for m in metrics if m.side == "BEARISH" and m.score > 0]

        bullish_metrics.sort(key=lambda x: x.score, reverse=True)
        bearish_metrics.sort(key=lambda x: x.score, reverse=True)

        bullish_items: List[BoardItem] = []
        new_bullish_ranks: Dict[str, int] = {}
        for rank, m in enumerate(bullish_metrics[:top_n], start=1):
            prev = self._prev_bullish_ranks.get(m.symbol)
            delta = (prev - rank) if prev is not None else 0
            is_new_10 = (rank <= 10) and (prev is None or prev > 10)
            
            bullish_items.append(BoardItem(
                symbol=m.symbol,
                sector=m.sector,
                score=m.score,
                side="BULLISH",
                rank=rank,
                prev_rank=prev,
                rank_delta=delta,
                is_new_top10=is_new_10,
                is_event_risk=m.is_event_risk,
                current_price=m.current_price,
                day_move_pct=m.day_move_pct
            ))
            new_bullish_ranks[m.symbol] = rank

        bearish_items: List[BoardItem] = []
        new_bearish_ranks: Dict[str, int] = {}
        for rank, m in enumerate(bearish_metrics[:top_n], start=1):
            prev = self._prev_bearish_ranks.get(m.symbol)
            delta = (prev - rank) if prev is not None else 0
            is_new_10 = (rank <= 10) and (prev is None or prev > 10)
            
            bearish_items.append(BoardItem(
                symbol=m.symbol,
                sector=m.sector,
                score=m.score,
                side="BEARISH",
                rank=rank,
                prev_rank=prev,
                rank_delta=delta,
                is_new_top10=is_new_10,
                is_event_risk=m.is_event_risk,
                current_price=m.current_price,
                day_move_pct=m.day_move_pct
            ))
            new_bearish_ranks[m.symbol] = rank

        # Update cache for next interval
        self._prev_bullish_ranks = new_bullish_ranks
        self._prev_bearish_ranks = new_bearish_ranks

        # Select Picks
        bullish_picks = self.select_picks(bullish_metrics, side="BULLISH", max_picks=3, max_per_sector=2)
        bearish_picks = self.select_picks(bearish_metrics, side="BEARISH", max_picks=3, max_per_sector=2)

        return BoardsSnapshot(
            timestamp=datetime.now(IST),
            bullish=bullish_items,
            bearish=bearish_items,
            bullish_picks=bullish_picks,
            bearish_picks=bearish_picks
        )
