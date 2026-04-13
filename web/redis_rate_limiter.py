"""Redis-backed sliding window rate limiter with in-process fallback.

Design
------
Uses a Redis sorted set (ZSET) per (bucket, client) key to track request
timestamps within a rolling window.  A Lua script makes each check atomic:

1. Remove entries older than ``window_start`` (ZREMRANGEBYSCORE).
2. Count remaining entries (ZCARD).
3a. If under the limit: record the new request (ZADD) → return allowed.
3b. If at or over the limit: compute ``retry_after`` from the oldest entry
    (ZRANGE + ZSCORE) → return denied.

Fallback
--------
If ``get_redis_conn`` is not configured, or if the Redis call raises any
exception, the limiter transparently falls back to the in-process
``SlidingWindowRateLimiter``.  In degraded mode each worker process limits
independently (pre-RR-27 behaviour).  A WARNING is logged on each fallback
to make degraded mode observable.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

try:
    from request_limits import RateLimitDecision, SlidingWindowRateLimiter
except ImportError:  # pragma: no cover
    from web.request_limits import RateLimitDecision, SlidingWindowRateLimiter

LOGGER = logging.getLogger(__name__)

# Atomic sliding-window check via Lua.  Executed as a single Redis command,
# so no WATCH/MULTI/EXEC overhead is needed.
_SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window_start = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local window_seconds = tonumber(ARGV[4])
local member = ARGV[5]

-- Evict timestamps outside the rolling window.
redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)

local count = redis.call('ZCARD', key)

if count < limit then
    -- Record this request and refresh TTL.
    redis.call('ZADD', key, now, member)
    redis.call('EXPIRE', key, window_seconds + 1)
    return {1, 0}
else
    -- Compute how long until the oldest entry ages out.
    local oldest = redis.call('ZRANGE', key, 0, 0)
    local retry_after = 1
    if #oldest > 0 then
        local oldest_score = tonumber(redis.call('ZSCORE', key, oldest[1]))
        if oldest_score then
            retry_after = math.ceil(oldest_score + window_seconds - now)
            if retry_after < 1 then retry_after = 1 end
        end
    end
    return {0, retry_after}
end
"""


class RedisRateLimiter:
    """Sliding-window rate limiter backed by Redis with in-process fallback.

    Args:
        get_redis: Optional callable that returns a live Redis connection
            (or ``None`` when Redis is unavailable).  Called once per
            ``check()`` invocation, so reconnections are transparent.
    """

    def __init__(self, get_redis: Callable[[], Any] | None = None) -> None:
        self._get_redis = get_redis
        self._fallback = SlidingWindowRateLimiter()

    def check(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
        now: float | None = None,
    ) -> RateLimitDecision:
        """Check and record one request against the sliding window.

        Falls back to in-process limiter when Redis is unavailable.
        """
        conn = self._get_redis() if self._get_redis is not None else None
        if conn is None:
            return self._fallback.check(
                key, limit=limit, window_seconds=window_seconds, now=now
            )
        try:
            return self._check_redis(
                conn, key, limit=limit, window_seconds=window_seconds, now=now
            )
        except Exception:
            LOGGER.warning(
                "Redis rate-limit check failed for key %r; falling back to in-process limiter.",
                key,
                exc_info=True,
            )
            return self._fallback.check(
                key, limit=limit, window_seconds=window_seconds, now=now
            )

    def _check_redis(
        self,
        conn: Any,
        key: str,
        *,
        limit: int,
        window_seconds: int,
        now: float | None = None,
    ) -> RateLimitDecision:
        current = time.time() if now is None else now
        window_start = current - max(window_seconds, 1)
        # Unique member prevents ZADD from overwriting a previous entry that
        # happens to have the same timestamp (possible under high concurrency).
        member = f"{current}:{uuid.uuid4().hex}"
        redis_key = f"rl:{key}"

        result = conn.eval(
            _SLIDING_WINDOW_LUA,
            1,  # numkeys
            redis_key,
            current,
            window_start,
            max(limit, 1),
            max(window_seconds, 1),
            member,
        )
        allowed = bool(result[0])
        retry_after = int(result[1])
        return RateLimitDecision(allowed=allowed, retry_after_seconds=retry_after)

    def reset(self) -> None:
        """Reset the in-process fallback limiter (used by tests)."""
        self._fallback.reset()
