"""Unit tests for OrderBlock popup mathematics, percentile calculations, and API contracts."""

import pytest
from api.routers.orderblock import (
    calculate_mid_rank_percentile,
    format_rank_percentile,
    calculate_day_change_rs,
    calculate_conviction_rating,
    router
)


def test_mid_rank_percentile_ireda():
    """Verify rank #1 of 210 bullish yields p99.8 matching Screenshot 1."""
    p = calculate_mid_rank_percentile(rank=1, total_universe=210, side="BULLISH")
    assert p == 99.8
    label = format_rank_percentile(rank=1, total_universe=210, side="BULLISH", side_count=130)
    assert label == "p99.8 · #1/130"


def test_mid_rank_percentile_fortis():
    """Verify rank #1 of 210 bearish yields p0.2 with ex-⊘ suffix matching Screenshot 1."""
    p = calculate_mid_rank_percentile(rank=1, total_universe=210, side="BEARISH")
    assert p == 0.2
    label = format_rank_percentile(rank=1, total_universe=210, side="BEARISH", side_count=80, is_event_risk=True)
    assert label == "p0.2 · #1/80 ex-⊘"


def test_day_change_rupee_reconciliation():
    """Verify rupee change and % move reconciliation matching Screenshot 1."""
    # IREDA: ₹113.22, change +3.11, previous close 110.11
    diff, pct, formatted = calculate_day_change_rs(113.22, 110.11)
    assert diff == 3.11
    assert pct == 2.82
    assert formatted == "+2.82% · +3.11"

    # FORTIS: ₹837.85, change -39.50, previous close 877.35
    diff_f, pct_f, formatted_f = calculate_day_change_rs(837.85, 877.35)
    assert diff_f == -39.50
    assert pct_f == -4.50
    assert formatted_f == "-4.50% · -39.50"


def test_conviction_score_bounds():
    """Verify conviction rating generates proper 0-99 score and 1-5 dots."""
    score, dots = calculate_conviction_rating(strength_score=2.8, alignment_score=4, rr_ratio=2.7)
    assert 80 <= score <= 99
    assert dots == "●●●●●"

    low_score, low_dots = calculate_conviction_rating(strength_score=0.5, alignment_score=1, rr_ratio=0.8)
    assert low_score < 50
    assert len(low_dots) <= 3


def test_router_popup_endpoint_registered():
    """Verify /api/v1/orderblock/popup-data route is properly registered on orderblock APIRouter."""
    routes = [r.path for r in router.routes]
    assert "/api/v1/orderblock/popup-data" in routes, "/popup-data route must be registered on orderblock router"
    assert "/api/v1/orderblock/boards" in routes
    assert "/api/v1/orderblock/market-picture" in routes
