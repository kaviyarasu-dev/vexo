"""Unit tests for Market X-Ray, Market Breadth, Sector Flow, and 4-Point Alignment logic."""

import pytest


def compute_market_breadth(metrics):
    """Calculates macro market breadth advances, declines, and ratio."""
    advances = sum(1 for m in metrics if m.get("day_move_pct", 0) > 0)
    declines = sum(1 for m in metrics if m.get("day_move_pct", 0) < 0)
    unchanged = sum(1 for m in metrics if m.get("day_move_pct", 0) == 0)
    total = len(metrics)
    ratio = round((advances / max(1, advances + declines)) * 100.0, 1)
    return {
        "advances": advances,
        "declines": declines,
        "unchanged": unchanged,
        "total": total,
        "ratio": ratio
    }


def map_xray_coordinates(day_move_pct, strength_score, canvas_w, canvas_h, padding=40):
    """Maps day_move_pct (-6% to +6%) to X and strength_score (0 to 5.0) to Y coordinates."""
    # Clamp day_move between -6.0 and +6.0
    clamped_move = max(-6.0, min(6.0, float(day_move_pct)))
    # X axis: -6% -> padding, 0% -> canvas_w / 2, +6% -> canvas_w - padding
    usable_w = canvas_w - (2 * padding)
    x = padding + ((clamped_move + 6.0) / 12.0) * usable_w

    # Clamp strength between 0.0 and 5.0
    clamped_strength = max(0.0, min(5.0, float(strength_score)))
    # Y axis: 5.0 -> padding (top), 0.0 -> canvas_h - padding (bottom)
    usable_h = canvas_h - (2 * padding)
    y = (canvas_h - padding) - (clamped_strength / 5.0) * usable_h

    return round(x, 1), round(y, 1)


def aggregate_sector_flow(metrics):
    """Ranks sectors by net flow and computes green/red participation counts."""
    sectors = {}
    for m in metrics:
        sec = m.get("sector") or "General"
        score = float(m.get("strength_score", 0))
        move = float(m.get("day_move_pct", 0))
        side = m.get("side", "NEUTRAL")

        if sec not in sectors:
            sectors[sec] = {
                "sector": sec,
                "scores": [],
                "moves": [],
                "green_count": 0,
                "red_count": 0,
                "stocks": []
            }

        sectors[sec]["scores"].append(score if side == "BULLISH" else -score)
        sectors[sec]["moves"].append(move)
        if move > 0:
            sectors[sec]["green_count"] += 1
        elif move < 0:
            sectors[sec]["red_count"] += 1
        sectors[sec]["stocks"].append({"symbol": m.get("symbol"), "move": move, "score": score})

    result = []
    for sec, data in sectors.items():
        total_stk = len(data["stocks"])
        avg_score = sum(data["scores"]) / total_stk if total_stk else 0.0
        avg_move = sum(data["moves"]) / total_stk if total_stk else 0.0
        result.append({
            "sector": sec,
            "avg_strength": round(avg_score, 2),
            "avg_move": round(avg_move, 2),
            "green_count": data["green_count"],
            "red_count": data["red_count"],
            "total_stocks": total_stk,
            "participation_pct": round((data["green_count"] / max(1, total_stk)) * 100, 1)
        })

    result.sort(key=lambda s: s["avg_strength"], reverse=True)
    return result


def evaluate_4point_alignment(is_top20, sector_concordant, breadth_concordant, vwap_concordant):
    """Evaluates 4-point alignment check: Board presence, Sector flow, Macro breadth, and VWAP position."""
    score = sum([
        1 if is_top20 else 0,
        1 if sector_concordant else 0,
        1 if breadth_concordant else 0,
        1 if vwap_concordant else 0
    ])

    if score == 4:
        return {"score": 4, "badge": "4/4 Full Edge", "color": "green", "action": "FULL_SIZE"}
    elif score == 3:
        return {"score": 3, "badge": "3/4 Half Size", "color": "yellow", "action": "HALF_SIZE"}
    else:
        return {"score": score, "badge": f"≤2/4 Pass ({score}/4)", "color": "dim", "action": "PASS"}


def test_breadth_ratio_calculation():
    """Validates advance/decline ratio calculation across market snapshot."""
    metrics = [
        {"day_move_pct": 1.5},
        {"day_move_pct": 2.1},
        {"day_move_pct": -0.8},
        {"day_move_pct": 0.0},
        {"day_move_pct": -1.2},
    ]
    b = compute_market_breadth(metrics)
    assert b["advances"] == 2
    assert b["declines"] == 2
    assert b["unchanged"] == 1
    assert b["total"] == 5
    assert b["ratio"] == 50.0


def test_xray_coordinate_mapping():
    """Maps day move and strength score to canvas X/Y bounded box."""
    canvas_w = 800
    canvas_h = 400
    padding = 40

    # Center origin: 0% move and 0.0 strength
    x_mid, y_bot = map_xray_coordinates(0.0, 0.0, canvas_w, canvas_h, padding)
    assert x_mid == 400.0  # Exactly center width
    assert y_bot == 360.0  # Exactly canvas_h - padding (bottom)

    # Extreme bull: +6% move and 5.0 strength
    x_max, y_top = map_xray_coordinates(6.0, 5.0, canvas_w, canvas_h, padding)
    assert x_max == 760.0  # canvas_w - padding
    assert y_top == 40.0   # padding (top)

    # Extreme bear: -6% move and 5.0 strength
    x_min, y_top_bear = map_xray_coordinates(-6.0, 5.0, canvas_w, canvas_h, padding)
    assert x_min == 40.0
    assert y_top_bear == 40.0


def test_sector_flow_aggregation():
    """Aggregates constituent stocks into sector ranking and participation counts."""
    metrics = [
        {"symbol": "NSE:TCS-EQ", "sector": "IT", "strength_score": 2.5, "day_move_pct": 1.8, "side": "BULLISH"},
        {"symbol": "NSE:INFY-EQ", "sector": "IT", "strength_score": 2.0, "day_move_pct": 1.2, "side": "BULLISH"},
        {"symbol": "NSE:WIPRO-EQ", "sector": "IT", "strength_score": 1.5, "day_move_pct": -0.2, "side": "BULLISH"},
        {"symbol": "NSE:HDFCBANK-EQ", "sector": "Banking", "strength_score": 1.0, "day_move_pct": -1.5, "side": "BEARISH"},
        {"symbol": "NSE:ICICIBANK-EQ", "sector": "Banking", "strength_score": 1.8, "day_move_pct": -2.0, "side": "BEARISH"},
    ]

    flows = aggregate_sector_flow(metrics)
    assert len(flows) == 2
    assert flows[0]["sector"] == "IT"
    assert flows[0]["green_count"] == 2
    assert flows[0]["red_count"] == 1
    assert flows[0]["total_stocks"] == 3

    assert flows[1]["sector"] == "Banking"
    assert flows[1]["red_count"] == 2
    assert flows[1]["green_count"] == 0


def test_alignment_check_evaluation():
    """Validates 4/4 Full Edge, 3/4 Half Size, and <=2/4 Pass transitions."""
    # 4/4 Full Edge
    res4 = evaluate_4point_alignment(is_top20=True, sector_concordant=True, breadth_concordant=True, vwap_concordant=True)
    assert res4["score"] == 4
    assert res4["action"] == "FULL_SIZE"
    assert "Full Edge" in res4["badge"]

    # 3/4 Half Size
    res3 = evaluate_4point_alignment(is_top20=True, sector_concordant=True, breadth_concordant=True, vwap_concordant=False)
    assert res3["score"] == 3
    assert res3["action"] == "HALF_SIZE"
    assert "Half Size" in res3["badge"]

    # <=2/4 Pass
    res2 = evaluate_4point_alignment(is_top20=True, sector_concordant=False, breadth_concordant=False, vwap_concordant=True)
    assert res2["score"] == 2
    assert res2["action"] == "PASS"
    assert "Pass" in res2["badge"]


def test_orderblock_dashboard_js_syntax():
    """Verify static/js/orderblock_dashboard.js exists and passes node syntax check."""
    import os
    import subprocess
    path = "static/js/orderblock_dashboard.js"
    assert os.path.exists(path), f"{path} must exist"
    res = subprocess.run(["node", "-c", path], capture_output=True, text=True)
    assert res.returncode == 0, f"Syntax check failed on {path}: {res.stderr}"


def test_orderblock_dashboard_contracts():
    """Verify static/js/orderblock_dashboard.js contains polling, high-DPI scaling, and DOM bindings."""
    path = "static/js/orderblock_dashboard.js"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Endpoints & Polling
    assert "/api/v1/orderblock/boards" in content
    assert "/api/v1/orderblock/market-picture" in content
    assert "pollInterval" in content or "setInterval" in content

    # Canvas & High-DPI
    assert "market-xray-canvas" in content
    assert "devicePixelRatio" in content
    assert "mapCoordinates" in content or "map_xray" in content

    # DOM Bindings
    assert "breadth-bar-advances" in content
    assert "bullish-picks-container" in content
    assert "tbody-bullish-board" in content
    assert "sector-flow-container" in content
    assert "chart-alignment-badge" in content

