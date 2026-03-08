"""Small in-process rate limit helpers for the canonical Flask runtime."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0


class SlidingWindowRateLimiter:
    """Track request bursts per key without introducing external dependencies."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
        now: float | None = None,
    ) -> RateLimitDecision:
        current_time = time.time() if now is None else now
        window_start = current_time - max(window_seconds, 1)

        with self._lock:
            events = self._events[key]
            while events and events[0] <= window_start:
                events.popleft()

            if len(events) >= max(limit, 1):
                retry_after = max(1, int(events[0] + window_seconds - current_time))
                return RateLimitDecision(allowed=False, retry_after_seconds=retry_after)

            events.append(current_time)
            return RateLimitDecision(allowed=True)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
