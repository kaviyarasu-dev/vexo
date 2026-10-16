import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from services.pattern_recognition_service import PatternRecognitionService, PatternSignal


@pytest.fixture
def service():
    return PatternRecognitionService()


def test_bullish_engulfing_detection(service):
    # Candle 0: neutral
    # Candle 1: bearish (100 -> 90)
    # Candle 2: bullish engulfing (opens <= 90, closes >= 100)
    df = pd.DataFrame({
        "timestamp": [
            datetime(2024, 1, 1, 9, 15),
            datetime(2024, 1, 1, 9, 20),
            datetime(2024, 1, 1, 9, 25),
            datetime(2024, 1, 1, 9, 30)
        ],
        "open": [95.0, 100.0, 89.0, 103.0],
        "high": [96.0, 101.0, 103.0, 105.0],
        "low": [94.0, 89.0, 88.0, 102.0],
        "close": [95.0, 90.0, 102.0, 104.0],
        "volume": [1000, 1200, 2500, 1100]
    })

    signals = service.scan_all(df, enabled_patterns=["bullish_engulfing"])
    assert len(signals) == 1
    sig = signals[0]
    assert sig.pattern_id == "bullish_engulfing"
    assert sig.sentiment == "bullish"
    assert sig.position == "belowBar"
    assert sig.badge_text == "BE"


def test_bearish_engulfing_detection(service):
    # Candle 1: bullish (90 -> 100)
    # Candle 2: bearish engulfing (opens >= 100, closes <= 90)
    df = pd.DataFrame({
        "timestamp": [
            datetime(2024, 1, 1, 9, 15),
            datetime(2024, 1, 1, 9, 20),
            datetime(2024, 1, 1, 9, 25),
        ],
        "open": [85.0, 90.0, 102.0],
        "high": [86.0, 101.0, 103.0],
        "low": [84.0, 89.0, 87.0],
        "close": [85.0, 100.0, 88.0],
        "volume": [1000, 1200, 2500]
    })

    signals = service.scan_all(df, enabled_patterns=["bearish_engulfing"])
    assert len(signals) == 1
    sig = signals[0]
    assert sig.pattern_id == "bearish_engulfing"
    assert sig.sentiment == "bearish"
    assert sig.position == "aboveBar"


def test_hammer_detection(service):
    # Candle with small body at top (100 -> 101) and long lower shadow (low 96)
    df = pd.DataFrame({
        "timestamp": [
            datetime(2024, 1, 1, 9, 15),
            datetime(2024, 1, 1, 9, 20),
            datetime(2024, 1, 1, 9, 25),
        ],
        "open": [105.0, 103.0, 100.0],
        "high": [106.0, 104.0, 101.2],
        "low": [104.0, 101.0, 96.0],
        "close": [104.0, 102.0, 101.0],
        "volume": [1000, 1000, 1500]
    })

    signals = service.scan_all(df, enabled_patterns=["hammer"])
    assert len(signals) >= 1
    sig = [s for s in signals if s.pattern_id == "hammer"][0]
    assert sig.sentiment == "bullish"
    assert sig.position == "belowBar"
    assert sig.badge_text == "HAM"


def test_doji_detection(service):
    # Candle with identical open and close (100.0 -> 100.02)
    df = pd.DataFrame({
        "timestamp": [
            datetime(2024, 1, 1, 9, 15),
            datetime(2024, 1, 1, 9, 20),
            datetime(2024, 1, 1, 9, 25),
        ],
        "open": [98.0, 100.0, 102.0],
        "high": [99.0, 102.0, 103.0],
        "low": [97.0, 98.0, 101.0],
        "close": [98.0, 100.02, 102.5],
        "volume": [1000, 1000, 1000]
    })

    signals = service.scan_all(df, enabled_patterns=["doji"])
    assert len(signals) >= 1
    sig = [s for s in signals if s.pattern_id == "doji"][0]
    assert sig.sentiment == "neutral"
    assert sig.shape == "circle"


def test_morning_star_detection(service):
    # 3 candles:
    # 0: Large red candle (100 -> 90)
    # 1: Small star (88 -> 87)
    # 2: Decisive green candle closing past midpoint 95 (88 -> 96)
    df = pd.DataFrame({
        "timestamp": [
            datetime(2024, 1, 1, 9, 15),
            datetime(2024, 1, 1, 9, 20),
            datetime(2024, 1, 1, 9, 25),
        ],
        "open": [100.0, 88.0, 88.0],
        "high": [101.0, 89.0, 97.0],
        "low": [89.0, 86.0, 87.0],
        "close": [90.0, 87.0, 96.0],
        "volume": [2000, 1000, 2500]
    })

    signals = service.scan_all(df, enabled_patterns=["morning_star"])
    assert len(signals) == 1
    assert signals[0].pattern_id == "morning_star"
    assert signals[0].sentiment == "bullish"


def test_to_chart_markers(service):
    df = pd.DataFrame({
        "timestamp": [
            datetime(2024, 1, 1, 9, 15),
            datetime(2024, 1, 1, 9, 20),
            datetime(2024, 1, 1, 9, 25),
        ],
        "open": [90.0, 85.0, 84.0],
        "high": [91.0, 86.0, 92.0],
        "low": [89.0, 84.0, 83.0],
        "close": [89.0, 84.0, 91.0],
        "volume": [1000, 1200, 2000]
    })

    signals = service.scan_all(df)
    markers = service.to_chart_markers(signals)
    assert isinstance(markers, list)
    if len(markers) > 0:
        m = markers[0]
        assert "time" in m
        assert "position" in m
        assert "color" in m
        assert "shape" in m
        assert "text" in m
        assert "customData" in m
        assert "description" in m["customData"]
