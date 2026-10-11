"""Global RateGovernor Specification & Token-Bucket Traffic Engine.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md Section 7 and plan/04_HISTORICAL_DOWNLOADER_ENGINE.md.
"""

from collections import deque
from datetime import datetime, timezone
import logging
import random
import threading
import time
from typing import Any, Callable, Deque, Dict, Optional, TypeVar

from config.settings import get_settings
from core.exceptions import RateLimitExceededError

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Priority Lanes
LANE_INTERACTIVE = 1    # High Priority: UI charts, quotes, option chain
LANE_SYNC = 2           # Medium Priority: EOD incremental sync, alerts
LANE_BACKFILL = 3       # Low Priority: Historical multi-year batch backfill

# 429 Throttle Constants
THROTTLE_RATE_PER_MIN = 120
THROTTLE_DURATION_SEC = 300.0   # 5 minutes
MAX_429_RETRIES = 5
BASE_429_BACKOFF_SEC = 2.0


class RateGovernor:
    """Global singleton rate governor enforcing Fyers v3 API rate limits and quotas.
    
    Architecture:
    - Bucket A (Burst): Capacity 10 tokens, refill 10 tokens/sec.
    - Bucket B (Sustained Minute Window): Rolling 60-second limit capped at 180 req/min (under 200 hard cap).
    - Daily Quota: Soft-stop cap at 90,000 req/day (under 100,000 hard broker cap).
    - Three-lane priority scheduler: Lane 1 (Interactive) preempts Lane 2 (Sync) and Lane 3 (Backfill).
    - Dynamic 429 throttle: On HTTP 429, throttles target to 120 req/min for 5 minutes with exponential jitter.
    """

    def __init__(
        self,
        target_per_min: Optional[int] = None,
        burst_per_sec: Optional[int] = None,
        daily_cap: Optional[int] = None,
        time_provider: Optional[Callable[[], float]] = None,
        sleep_provider: Optional[Callable[[float], None]] = None,
    ) -> None:
        try:
            settings = get_settings()
            default_target = settings.RATE_GOVERNOR_TARGET_PER_MIN
            default_burst = settings.RATE_GOVERNOR_BURST_PER_SEC
            default_daily = settings.RATE_GOVERNOR_DAILY_CAP
        except Exception:
            default_target = 180
            default_burst = 10
            default_daily = 90000

        self.target_per_min: int = target_per_min if target_per_min is not None else default_target
        self.burst_per_sec: int = burst_per_sec if burst_per_sec is not None else default_burst
        self.daily_cap: int = daily_cap if daily_cap is not None else default_daily

        # Pluggable time functions for zero-delay unit testing
        self._time_func: Callable[[], float] = time_provider or time.time
        self._sleep_func: Callable[[float], None] = sleep_provider or time.sleep

        # Thread synchronization
        self._lock = threading.RLock()
        self._cond = threading.Condition(self._lock)
        self._waiting_counts: Dict[int, int] = {
            LANE_INTERACTIVE: 0,
            LANE_SYNC: 0,
            LANE_BACKFILL: 0,
        }

        # Burst token bucket state
        self._burst_tokens: float = float(self.burst_per_sec)
        self._last_burst_update: float = self._time_func()

        # Rolling minute window history (timestamps)
        self._minute_window: Deque[float] = deque()

        # Daily request tracking
        self._current_day_str: str = self._get_today_str()
        self._daily_count: int = 0

        # 429 adaptive throttling state
        self._throttled_until: float = 0.0

    def _get_today_str(self) -> str:
        """Returns current date string in UTC (YYYY-MM-DD)."""
        return datetime.fromtimestamp(self._time_func(), tz=timezone.utc).strftime("%Y-%m-%d")

    @property
    def effective_target_per_min(self) -> int:
        """Returns effective sustained target, reducing to 120 req/min if 429 throttle is active."""
        with self._lock:
            now = self._time_func()
            if now < self._throttled_until:
                return THROTTLE_RATE_PER_MIN
            return self.target_per_min

    @property
    def is_throttled(self) -> bool:
        """Checks whether 429 throttle is currently active."""
        with self._lock:
            return self._time_func() < self._throttled_until

    @property
    def daily_count(self) -> int:
        """Returns total requests executed today."""
        with self._lock:
            self._check_day_rollover()
            return self._daily_count

    def trigger_429_throttle(self) -> None:
        """Activates adaptive rate reduction to 120 req/min for 5 minutes."""
        with self._lock:
            now = self._time_func()
            self._throttled_until = now + THROTTLE_DURATION_SEC
            logger.warning(
                "RateGovernor: HTTP 429 detected! Throttling sustained rate to %d req/min for %.0f seconds.",
                THROTTLE_RATE_PER_MIN,
                THROTTLE_DURATION_SEC,
            )
            self._cond.notify_all()

    def reset_throttle(self) -> None:
        """Resets 429 throttle back to normal target rate."""
        with self._lock:
            self._throttled_until = 0.0
            self._cond.notify_all()

    def _check_day_rollover(self) -> None:
        """Resets daily counter at UTC midnight."""
        today = self._get_today_str()
        if today != self._current_day_str:
            self._current_day_str = today
            self._daily_count = 0

    def _refill_burst_tokens(self, now: float) -> None:
        """Refills burst tokens proportional to elapsed time."""
        elapsed = max(0.0, now - self._last_burst_update)
        self._last_burst_update = now
        self._burst_tokens = min(
            float(self.burst_per_sec),
            self._burst_tokens + (elapsed * float(self.burst_per_sec))
        )

    def _purge_minute_window(self, now: float) -> None:
        """Removes timestamps older than 60 seconds from minute window."""
        cutoff = now - 60.0
        while self._minute_window and self._minute_window[0] <= cutoff:
            self._minute_window.popleft()

    def _calculate_delay(self, now: float) -> float:
        """Calculates seconds to wait before a token is available across burst and minute windows."""
        self._refill_burst_tokens(now)
        self._purge_minute_window(now)

        # 1. Burst delay: need at least 1 token
        burst_delay = 0.0
        if self._burst_tokens < 1.0:
            needed = 1.0 - self._burst_tokens
            burst_delay = needed / float(self.burst_per_sec)

        # 2. Minute window delay: must not exceed effective_target_per_min
        minute_delay = 0.0
        target = self.effective_target_per_min
        if len(self._minute_window) >= target:
            oldest = self._minute_window[0]
            minute_delay = max(0.0, (oldest + 60.0) - now + 0.001)

        return max(burst_delay, minute_delay)

    def acquire(self, priority_lane: int = LANE_BACKFILL, timeout: Optional[float] = None) -> bool:
        """Acquires permission to execute a broker API call adhering to priority lane and limits.
        
        Args:
            priority_lane: 1 (Interactive UI), 2 (EOD Sync), 3 (Backfill).
            timeout: Optional maximum seconds to wait before giving up.
            
        Returns:
            True if permission acquired.
            
        Raises:
            RateLimitExceededError: If daily quota cap (90,000) is exceeded.
            TimeoutError: If timeout expires while waiting.
        """
        if priority_lane not in self._waiting_counts:
            priority_lane = LANE_BACKFILL

        start_time = self._time_func()

        with self._lock:
            # Check daily quota
            self._check_day_rollover()
            if self._daily_count >= self.daily_cap:
                raise RateLimitExceededError(
                    f"Daily request quota reached: {self._daily_count}/{self.daily_cap}. "
                    "Halting to prevent broker account suspension."
                )

            self._waiting_counts[priority_lane] += 1
            try:
                while True:
                    now = self._time_func()

                    # Check overall timeout
                    if timeout is not None:
                        elapsed = now - start_time
                        if elapsed >= timeout:
                            raise TimeoutError(f"RateGovernor acquisition timed out after {timeout:.2f}s")

                    # Check preemption: higher priority lanes always go first
                    has_higher_priority = any(
                        self._waiting_counts[lane] > 0
                        for lane in range(1, priority_lane)
                    )

                    if has_higher_priority:
                        # Sleep briefly waiting for higher priority to drain
                        wait_budget = 0.02
                        if timeout is not None:
                            remaining = timeout - (now - start_time)
                            wait_budget = min(wait_budget, remaining)
                        if self._sleep_func != time.sleep:
                            self._sleep_func(wait_budget)
                            self._cond.notify_all()
                        else:
                            self._cond.wait(timeout=wait_budget)
                        continue

                    # Calculate traffic delay
                    delay = self._calculate_delay(now)
                    if delay <= 0.0001:
                        # Token available! Consume and record
                        self._burst_tokens -= 1.0
                        self._minute_window.append(now)
                        self._daily_count += 1
                        return True

                    # Wait for token
                    wait_budget = delay
                    if timeout is not None:
                        remaining = timeout - (now - start_time)
                        if remaining <= 0:
                            raise TimeoutError(f"RateGovernor acquisition timed out after {timeout:.2f}s")
                        wait_budget = min(wait_budget, remaining)

                    if self._sleep_func != time.sleep:
                        self._sleep_func(wait_budget)
                        self._cond.notify_all()
                    else:
                        # Release lock temporarily during sleep
                        self._cond.wait(timeout=wait_budget)
            finally:
                self._waiting_counts[priority_lane] -= 1
                self._cond.notify_all()

    def execute(
        self,
        priority_lane: int,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Executes a request through the rate governor with priority queuing and automated 429 recovery.
        
        Args:
            priority_lane: 1 (Interactive UI), 2 (EOD Sync), 3 (Backfill).
            func: Target callable performing upstream API request.
            *args, **kwargs: Arguments passed to func.
            
        Returns:
            Result of func.
        """
        retry_count = 0

        while True:
            self.acquire(priority_lane=priority_lane)

            try:
                result = func(*args, **kwargs)

                # Inspect response payload for Fyers error envelope s == 'error' and code == 429
                if isinstance(result, dict):
                    status = result.get("s")
                    code = result.get("code")
                    if (status == "error" and code == 429) or code == 429:
                        self._handle_429_detected(retry_count)
                        retry_count += 1
                        if retry_count > MAX_429_RETRIES:
                            raise RateLimitExceededError("Exceeded max retries (5) following HTTP 429 responses.")
                        continue

                return result

            except Exception as exc:
                # Check if exception represents HTTP 429
                is_429 = False
                error_str = str(exc)
                if "429" in error_str or "Too Many Requests" in error_str:
                    is_429 = True
                status_code = getattr(exc, "status_code", None)
                if status_code == 429:
                    is_429 = True

                if is_429:
                    self._handle_429_detected(retry_count)
                    retry_count += 1
                    if retry_count > MAX_429_RETRIES:
                        raise RateLimitExceededError("Exceeded max retries (5) following HTTP 429 errors.") from exc
                    continue

                raise exc

    def _handle_429_detected(self, retry_count: int) -> None:
        """Throttles target and applies exponential backoff with randomized jitter."""
        self.trigger_429_throttle()
        jitter = random.uniform(0.2, 0.5)
        backoff_sec = (BASE_429_BACKOFF_SEC * (2 ** retry_count)) + jitter
        logger.warning(
            "RateGovernor: Backing off for %.2fs (attempt %d/%d) following 429 response",
            backoff_sec,
            retry_count + 1,
            MAX_429_RETRIES,
        )
        self._sleep_func(backoff_sec)


# Global singleton instance
_GLOBAL_RATE_GOVERNOR: Optional[RateGovernor] = None
_GLOBAL_GOVERNOR_LOCK = threading.Lock()


def get_rate_governor() -> RateGovernor:
    """Returns singleton instance of RateGovernor."""
    global _GLOBAL_RATE_GOVERNOR
    with _GLOBAL_GOVERNOR_LOCK:
        if _GLOBAL_RATE_GOVERNOR is None:
            _GLOBAL_RATE_GOVERNOR = RateGovernor()
        return _GLOBAL_RATE_GOVERNOR


def reset_rate_governor() -> None:
    """Resets global singleton instance (primarily for testing)."""
    global _GLOBAL_RATE_GOVERNOR
    with _GLOBAL_GOVERNOR_LOCK:
        _GLOBAL_RATE_GOVERNOR = None
