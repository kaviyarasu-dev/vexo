"""Unit tests for Global RateGovernor.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md Section 7 and plan/04_HISTORICAL_DOWNLOADER_ENGINE.md.
"""

import threading
import time
import pytest

from core.exceptions import RateLimitExceededError
from core.rate_governor import (
    LANE_BACKFILL,
    LANE_INTERACTIVE,
    LANE_SYNC,
    RateGovernor,
)


def test_rate_governor_defaults():
    """Verify DoD Item 1: target_per_min == 180 and burst_per_sec == 10."""
    rg = RateGovernor()
    assert rg.target_per_min == 180
    assert rg.burst_per_sec == 10
    assert rg.daily_cap == 90000


def test_burst_bucket_capacity_and_refill():
    """Verify burst bucket allows up to burst_per_sec tokens immediately, then throttles."""
    current_time = 1000.0

    def mock_time():
        return current_time

    def mock_sleep(sec):
        nonlocal current_time
        current_time += sec

    rg = RateGovernor(
        target_per_min=180,
        burst_per_sec=10,
        daily_cap=1000,
        time_provider=mock_time,
        sleep_provider=mock_sleep,
    )

    # 10 burst tokens should be acquired with zero simulated time elapsed
    for _ in range(10):
        assert rg.acquire(priority_lane=LANE_BACKFILL)
    assert current_time == 1000.0

    # 11th token must require a delay for burst refill (1 token takes 0.1s)
    rg.acquire(priority_lane=LANE_BACKFILL)
    assert current_time >= 1000.1


def test_sustained_minute_rate_limit():
    """Verify sustained rolling window enforces target_per_min."""
    current_time = 2000.0

    def mock_time():
        return current_time

    def mock_sleep(sec):
        nonlocal current_time
        current_time += sec

    # Governor with target 3 per min
    rg = RateGovernor(
        target_per_min=3,
        burst_per_sec=10,
        daily_cap=1000,
        time_provider=mock_time,
        sleep_provider=mock_sleep,
    )

    # Acquire 3 tokens immediately
    for _ in range(3):
        rg.acquire(priority_lane=LANE_BACKFILL)
    assert current_time == 2000.0

    # 4th token must wait until the 60s window from 1st token rolls over
    rg.acquire(priority_lane=LANE_BACKFILL)
    assert current_time >= 2060.0


def test_priority_preemption():
    """Verify Lane 1 (Interactive) preempts Lane 3 (Backfill)."""
    current_time = 3000.0

    def mock_time():
        return current_time

    def mock_sleep(sec):
        nonlocal current_time
        current_time += sec

    rg = RateGovernor(
        target_per_min=180,
        burst_per_sec=10,
        daily_cap=1000,
        time_provider=mock_time,
        sleep_provider=mock_sleep,
    )

    execution_order = []

    def task_lane3():
        # Lane 3 acquires
        rg.acquire(priority_lane=LANE_BACKFILL)
        execution_order.append("LANE3")

    def task_lane1():
        # Lane 1 acquires
        rg.acquire(priority_lane=LANE_INTERACTIVE)
        execution_order.append("LANE1")

    # Empty burst tokens so threads must wait
    for _ in range(10):
        rg.acquire(priority_lane=LANE_BACKFILL)

    t3 = threading.Thread(target=task_lane3)
    t1 = threading.Thread(target=task_lane1)

    # Start Lane 3 first, then Lane 1
    t3.start()
    time.sleep(0.01)
    t1.start()
    time.sleep(0.01)

    # Advance time to allow token refill
    current_time += 1.0

    t3.join(timeout=2)
    t1.join(timeout=2)

    # Both completed
    assert len(execution_order) == 2


def test_429_adaptive_throttling():
    """Verify HTTP 429 detection throttles target to 120 req/min for 5 minutes."""
    current_time = 4000.0

    def mock_time():
        return current_time

    def mock_sleep(sec):
        nonlocal current_time
        current_time += sec

    rg = RateGovernor(
        target_per_min=180,
        burst_per_sec=10,
        daily_cap=1000,
        time_provider=mock_time,
        sleep_provider=mock_sleep,
    )

    assert not rg.is_throttled
    assert rg.effective_target_per_min == 180

    rg.trigger_429_throttle()

    assert rg.is_throttled
    assert rg.effective_target_per_min == 120

    # Advance time beyond 300 seconds (5 minutes)
    current_time += 301.0
    assert not rg.is_throttled
    assert rg.effective_target_per_min == 180


def test_execute_with_429_recovery():
    """Verify execute() retries on 429 response envelope and activates throttle."""
    current_time = 5000.0

    def mock_time():
        return current_time

    def mock_sleep(sec):
        nonlocal current_time
        current_time += sec

    rg = RateGovernor(
        target_per_min=180,
        burst_per_sec=10,
        daily_cap=1000,
        time_provider=mock_time,
        sleep_provider=mock_sleep,
    )

    call_count = 0

    def flaky_api():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"s": "error", "code": 429, "message": "Too Many Requests"}
        return {"s": "ok", "candles": [[1704080700, 100, 105, 95, 102, 500]]}

    res = rg.execute(priority_lane=LANE_BACKFILL, func=flaky_api)
    assert call_count == 2
    assert res["s"] == "ok"
    assert rg.is_throttled


def test_daily_quota_breach_raises_error():
    """Verify exceeding daily cap raises RateLimitExceededError."""
    rg = RateGovernor(
        target_per_min=180,
        burst_per_sec=10,
        daily_cap=3,
    )

    # 3 allowed
    rg.acquire(priority_lane=LANE_BACKFILL)
    rg.acquire(priority_lane=LANE_BACKFILL)
    rg.acquire(priority_lane=LANE_BACKFILL)
    assert rg.daily_count == 3

    # 4th exceeds daily cap
    with pytest.raises(RateLimitExceededError):
        rg.acquire(priority_lane=LANE_BACKFILL)
