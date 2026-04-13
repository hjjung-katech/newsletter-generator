"""Unit tests for RedisRateLimiter.

Tests cover:
- In-process fallback when no Redis connection is provided.
- In-process fallback when Redis raises an exception.
- Redis-backed sliding window via a fake Redis stub.
- reset() delegates to the in-process fallback.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from redis_rate_limiter import RedisRateLimiter  # noqa: E402
from request_limits import RateLimitDecision  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeRedis:
    """Minimal Redis stub that executes the Lua sliding-window script in Python.

    Rather than running actual Lua, we implement the same semantics directly
    so the tests remain dependency-free and deterministic.
    """

    def __init__(self) -> None:
        self._zsets: dict[str, dict[str, float]] = {}
        self._ttls: dict[str, float] = {}

    def eval(
        self,
        _script: str,
        _numkeys: int,
        key: str,
        now: float,
        window_start: float,
        limit: int,
        window_seconds: int,
        member: str,
    ) -> list[int]:
        # ZREMRANGEBYSCORE: evict old entries
        zset = self._zsets.get(key, {})
        zset = {m: s for m, s in zset.items() if s > window_start}

        count = len(zset)
        if count < limit:
            zset[member] = now
            self._zsets[key] = zset
            self._ttls[key] = now + window_seconds + 1
            return [1, 0]
        else:
            if zset:
                oldest_score = min(zset.values())
                retry_after = max(1, int(oldest_score + window_seconds - now) + 1)
            else:
                retry_after = 1
            self._zsets[key] = zset
            return [0, retry_after]

    def reset_all(self) -> None:
        self._zsets.clear()
        self._ttls.clear()


# ---------------------------------------------------------------------------
# Fallback behaviour (no Redis)
# ---------------------------------------------------------------------------


def test_no_redis_conn_uses_in_process_fallback() -> None:
    limiter = RedisRateLimiter(get_redis=None)
    result = limiter.check("k", limit=3, window_seconds=60)
    assert result.allowed is True


def test_no_redis_conn_enforces_in_process_limit() -> None:
    limiter = RedisRateLimiter(get_redis=None)
    for _ in range(3):
        limiter.check("k", limit=3, window_seconds=60)

    result = limiter.check("k", limit=3, window_seconds=60)
    assert result.allowed is False
    assert result.retry_after_seconds >= 1


def test_redis_exception_falls_back_to_in_process() -> None:
    broken_conn = MagicMock()
    broken_conn.eval.side_effect = ConnectionError("Redis down")

    limiter = RedisRateLimiter(get_redis=lambda: broken_conn)
    result = limiter.check("k", limit=3, window_seconds=60)
    assert result.allowed is True  # fallback allows the request


def test_redis_none_getter_falls_back() -> None:
    limiter = RedisRateLimiter(get_redis=lambda: None)
    result = limiter.check("k", limit=2, window_seconds=60)
    assert result.allowed is True


# ---------------------------------------------------------------------------
# Redis-backed behaviour
# ---------------------------------------------------------------------------


def test_redis_allows_requests_under_limit() -> None:
    fake = _FakeRedis()
    limiter = RedisRateLimiter(get_redis=lambda: fake)
    t = time.time()
    for i in range(3):
        result = limiter.check("ip:1.2.3.4", limit=3, window_seconds=60, now=t + i)
        assert result.allowed is True, f"request {i} should be allowed"


def test_redis_denies_request_at_limit() -> None:
    fake = _FakeRedis()
    limiter = RedisRateLimiter(get_redis=lambda: fake)
    t = time.time()
    for _ in range(3):
        limiter.check("ip:1.2.3.4", limit=3, window_seconds=60, now=t)

    result = limiter.check("ip:1.2.3.4", limit=3, window_seconds=60, now=t)
    assert result.allowed is False
    assert result.retry_after_seconds >= 1


def test_redis_allows_after_window_expires() -> None:
    fake = _FakeRedis()
    limiter = RedisRateLimiter(get_redis=lambda: fake)
    t = time.time()
    for _ in range(2):
        limiter.check("ip:1.2.3.4", limit=2, window_seconds=10, now=t)

    denied = limiter.check("ip:1.2.3.4", limit=2, window_seconds=10, now=t)
    assert denied.allowed is False

    # Advance time past window
    allowed = limiter.check("ip:1.2.3.4", limit=2, window_seconds=10, now=t + 11)
    assert allowed.allowed is True


def test_redis_isolates_different_keys() -> None:
    fake = _FakeRedis()
    limiter = RedisRateLimiter(get_redis=lambda: fake)
    t = time.time()
    for _ in range(2):
        limiter.check("ip:1.1.1.1", limit=2, window_seconds=60, now=t)

    limiter.check("ip:1.1.1.1", limit=2, window_seconds=60, now=t)  # denied

    # Different key is unaffected
    result = limiter.check("ip:2.2.2.2", limit=2, window_seconds=60, now=t)
    assert result.allowed is True


def test_redis_retry_after_is_positive() -> None:
    fake = _FakeRedis()
    limiter = RedisRateLimiter(get_redis=lambda: fake)
    t = time.time()
    for _ in range(1):
        limiter.check("k", limit=1, window_seconds=30, now=t)

    result = limiter.check("k", limit=1, window_seconds=30, now=t)
    assert result.allowed is False
    assert result.retry_after_seconds >= 1


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------


def test_reset_clears_in_process_fallback() -> None:
    limiter = RedisRateLimiter(get_redis=None)
    for _ in range(3):
        limiter.check("k", limit=3, window_seconds=60)

    denied = limiter.check("k", limit=3, window_seconds=60)
    assert denied.allowed is False

    limiter.reset()
    result = limiter.check("k", limit=3, window_seconds=60)
    assert result.allowed is True


def test_reset_with_redis_still_resets_fallback() -> None:
    fake = _FakeRedis()
    limiter = RedisRateLimiter(get_redis=lambda: fake)
    # Drive the fallback to its limit by temporarily making Redis unavailable
    broken = MagicMock()
    broken.eval.side_effect = RuntimeError("temp error")
    limiter_broken = RedisRateLimiter(get_redis=lambda: broken)
    for _ in range(3):
        limiter_broken.check("k", limit=3, window_seconds=60)
    denied = limiter_broken.check("k", limit=3, window_seconds=60)
    assert denied.allowed is False

    limiter_broken.reset()
    result = limiter_broken.check("k", limit=3, window_seconds=60)
    assert result.allowed is True
