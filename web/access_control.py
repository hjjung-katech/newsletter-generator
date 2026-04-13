"""Minimal access control for sensitive Flask operational routes.

Token model
-----------
``ADMIN_API_TOKEN`` (root/bootstrap token) — grants all scopes.  Used as the
single shared credential in existing deployments and remains fully
backward-compatible.

Scoped tokens — each grants access only to the named scope:

  * ``ADMIN_API_TOKEN_DATA``     — read/write history, analytics, archive,
                                    presets, approvals, source-policies
  * ``ADMIN_API_TOKEN_SCHEDULE`` — schedule management endpoints
  * ``ADMIN_API_TOKEN_EMAIL``    — email send/config/test endpoints
  * ``ADMIN_API_TOKEN_OPS``      — ops diagnostics endpoints

Using scoped tokens reduces the blast radius of a leak: an email-service token
cannot access schedule management, and vice versa.  Different deployments or
automation systems should each receive the smallest token that satisfies their
needs.

Auth flow (production-like runtimes)
-------------------------------------
1. Rate-limit check (shared sliding-window limiter).
2. Find all configured tokens from environment.
3. Determine the required scope for the requested path.
4. Walk token list, compare with ``hmac.compare_digest`` (constant-time).
5. If a matching token is found and it holds the required scope → 200.
   If matching but wrong scope → 403 (Insufficient token scope).
   If no match at all → 401 (Admin API token required).
   If no tokens configured at all → 503 (misconfiguration).

Quota / Abuse observability
----------------------------
Rate-limit violations on ``/api/generate`` and ``/newsletter`` are recorded
in a per-process ``_QuotaAbuseTracker`` stored in
``app.extensions["quota_abuse_tracker"]``.  The ``/api/ops/quota-abuse``
endpoint (requires ``SCOPE_OPS``) exposes these events to operators without
requiring direct database or log access.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from hmac import compare_digest
from typing import Any, Mapping

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue

try:
    from redis_rate_limiter import RedisRateLimiter
except ImportError:  # pragma: no cover
    from web.redis_rate_limiter import RedisRateLimiter

LOGGER = logging.getLogger(__name__)

ADMIN_TOKEN_ENV_VAR = "ADMIN_API_TOKEN"  # nosec B105
ADMIN_TOKEN_HEADER = "X-Admin-Token"  # nosec B105
DEFAULT_GENERATE_RATE_LIMIT = 5
DEFAULT_GENERATE_WINDOW_SECONDS = 60
DEFAULT_NEWSLETTER_RATE_LIMIT = 5
DEFAULT_NEWSLETTER_WINDOW_SECONDS = 60
DEFAULT_PROTECTED_RATE_LIMIT = 30
DEFAULT_PROTECTED_WINDOW_SECONDS = 60
DEFAULT_GENERATE_MAX_BODY_BYTES = 32 * 1024
_QUOTA_ABUSE_TRACKER_MAXLEN = 1000

# ---------------------------------------------------------------------------
# Scope constants
# ---------------------------------------------------------------------------

SCOPE_DATA = "data"
SCOPE_SCHEDULE = "schedule"
SCOPE_EMAIL = "email"
SCOPE_OPS = "ops"

ALL_SCOPES: frozenset[str] = frozenset(
    {SCOPE_DATA, SCOPE_SCHEDULE, SCOPE_EMAIL, SCOPE_OPS}
)

# Map each protected route prefix to its required scope.
_ROUTE_SCOPE_MAP: dict[str, str] = {
    "/api/history": SCOPE_DATA,
    "/api/analytics": SCOPE_DATA,
    "/api/presets": SCOPE_DATA,
    "/api/approvals": SCOPE_DATA,
    "/api/source-policies": SCOPE_DATA,
    "/api/archive": SCOPE_DATA,
    "/api/schedule": SCOPE_SCHEDULE,
    "/api/schedules": SCOPE_SCHEDULE,
    "/api/send-email": SCOPE_EMAIL,
    "/api/email-config": SCOPE_EMAIL,
    "/api/test-email": SCOPE_EMAIL,
    "/api/ops": SCOPE_OPS,
}

# Scoped token env-var names (one per scope).
_SCOPED_TOKEN_ENV_VARS: dict[str, str] = {  # nosec B105
    SCOPE_DATA: "ADMIN_API_TOKEN_DATA",
    SCOPE_SCHEDULE: "ADMIN_API_TOKEN_SCHEDULE",
    SCOPE_EMAIL: "ADMIN_API_TOKEN_EMAIL",
    SCOPE_OPS: "ADMIN_API_TOKEN_OPS",
}

# Derived from _ROUTE_SCOPE_MAP so the two stay in sync automatically.
_PROTECTED_PREFIXES: tuple[str, ...] = tuple(_ROUTE_SCOPE_MAP.keys())


def _is_dev_like(app: Flask, environ: Mapping[str, str] | None = None) -> bool:
    env = environ or os.environ
    if app.config.get("TESTING"):
        return True

    explicit_runtime = next(
        (
            str(value or "").strip().lower()
            for value in (
                app.config.get("ENV"),
                env.get("APP_ENV"),
                env.get("FLASK_ENV"),
            )
            if str(value or "").strip()
        ),
        "",
    )
    if explicit_runtime in {"production", "prod"}:
        return False
    if explicit_runtime in {"development", "dev", "testing", "test", "local"}:
        return True

    fallback_runtime = str(env.get("ENVIRONMENT", "") or "").strip().lower()
    if fallback_runtime in {"production", "prod"}:
        return False
    if fallback_runtime in {"development", "dev", "testing", "test", "local"}:
        return True

    return False


def is_protected_route(
    path: str, prefixes: tuple[str, ...] = _PROTECTED_PREFIXES
) -> bool:
    """Return whether the request path should require the admin API token."""
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in prefixes)


@dataclass(frozen=True)
class _TokenConfig:
    """A configured token with its granted scopes and a human-readable label."""

    value: str
    scopes: frozenset[str]
    label: str


@dataclass(frozen=True)
class AbuseEvent:
    """A single rate-limit violation event recorded for ops observability."""

    timestamp: str  # ISO-8601 UTC
    client_id: str  # IP or X-Forwarded-For first segment
    path: str  # request path that triggered the limit
    retry_after_seconds: int


class _QuotaAbuseTracker:
    """Thread-safe bounded ring buffer for rate-limit violation events.

    Stored in ``app.extensions["quota_abuse_tracker"]`` by
    ``configure_access_control()``.  The ``/api/ops/quota-abuse`` endpoint
    reads from it without importing this class directly.
    """

    def __init__(self, maxlen: int = _QUOTA_ABUSE_TRACKER_MAXLEN) -> None:
        self._lock = threading.Lock()
        self._events: deque[AbuseEvent] = deque(maxlen=maxlen)
        self._total: int = 0  # cumulative count, not capped by maxlen

    def record(self, event: AbuseEvent) -> None:
        with self._lock:
            self._events.append(event)
            self._total += 1

    def recent(self, limit: int = 100) -> list[AbuseEvent]:
        with self._lock:
            events = list(self._events)
        return events[-limit:]

    @property
    def total_recorded(self) -> int:
        with self._lock:
            return self._total


def _record_abuse_event(
    tracker: _QuotaAbuseTracker,
    client_id: str,
    path: str,
    retry_after_seconds: int,
) -> None:
    """Log and record a rate-limit violation event."""
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    LOGGER.warning(
        "abuse.rate_limit_exceeded path=%s client=%s retry_after_seconds=%d",
        path,
        client_id,
        retry_after_seconds,
    )
    tracker.record(
        AbuseEvent(
            timestamp=timestamp,
            client_id=client_id,
            path=path,
            retry_after_seconds=retry_after_seconds,
        )
    )


def _resolve_all_token_configs(
    environ: Mapping[str, str] | None = None,
) -> list[_TokenConfig]:
    """Return every token configured in the environment.

    The root ``ADMIN_API_TOKEN`` is granted ``ALL_SCOPES``.  Each scoped token
    (``ADMIN_API_TOKEN_<SCOPE>``) is granted only the corresponding scope.
    """
    env = environ or os.environ
    configs: list[_TokenConfig] = []

    root_token = env.get(ADMIN_TOKEN_ENV_VAR, "").strip()
    if root_token:
        configs.append(_TokenConfig(value=root_token, scopes=ALL_SCOPES, label="root"))

    for scope, env_var in _SCOPED_TOKEN_ENV_VARS.items():
        scoped_token = env.get(env_var, "").strip()
        if scoped_token:
            configs.append(
                _TokenConfig(
                    value=scoped_token,
                    scopes=frozenset({scope}),
                    label=env_var,
                )
            )

    return configs


def _scope_for_path(path: str) -> str | None:
    """Return the scope required for *path*, or ``None`` if no mapping exists."""
    for prefix, scope in _ROUTE_SCOPE_MAP.items():
        if path == prefix or path.startswith(f"{prefix}/"):
            return scope
    return None


def _check_token_auth(
    provided: str,
    required_scope: str,
    configs: list[_TokenConfig],
) -> tuple[bool, str | None]:
    """Constant-time multi-token check.

    Scans every config to avoid short-circuit timing leaks.

    Returns:
        (authorized, label): ``(True, label)`` if a token matched and holds the
        required scope; ``(False, label)`` if a token matched but lacks scope;
        ``(False, None)`` if no token matched.
    """
    matched_label: str | None = None
    scope_granted: bool = False

    for config in configs:
        if compare_digest(provided, config.value):
            matched_label = config.label
            if required_scope in config.scopes:
                scope_granted = True

    return (scope_granted and matched_label is not None), matched_label


# ---------------------------------------------------------------------------
# Legacy single-token helpers — kept for internal backward compat only.
# ---------------------------------------------------------------------------


def _resolve_expected_admin_token(
    environ: Mapping[str, str] | None = None
) -> str | None:
    env = environ or os.environ
    token = env.get(ADMIN_TOKEN_ENV_VAR, "").strip()
    return token or None


def _resolve_provided_admin_token() -> str | None:
    explicit_token = str(request.headers.get(ADMIN_TOKEN_HEADER, "")).strip()
    if explicit_token:
        return explicit_token

    auth_header = str(request.headers.get("Authorization", "")).strip()
    if auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ").strip() or None

    return None


def _client_identifier() -> str:
    forwarded_for = str(request.headers.get("X-Forwarded-For", "")).strip()
    if forwarded_for:
        return forwarded_for.split(",")[0].strip() or "unknown"

    return str(request.remote_addr or "unknown")


def _rate_limit_response(
    *,
    message: str,
    retry_after_seconds: int,
) -> ResponseReturnValue:
    response = jsonify(
        {
            "error": message,
            "retry_after_seconds": retry_after_seconds,
        }
    )
    response.status_code = 429
    response.headers["Retry-After"] = str(retry_after_seconds)
    return response


def configure_access_control(
    app: Flask,
    *,
    environ: Mapping[str, str] | None = None,
    prefixes: tuple[str, ...] = _PROTECTED_PREFIXES,
    generate_rate_limit: int = DEFAULT_GENERATE_RATE_LIMIT,
    generate_window_seconds: int = DEFAULT_GENERATE_WINDOW_SECONDS,
    newsletter_rate_limit: int = DEFAULT_NEWSLETTER_RATE_LIMIT,
    newsletter_window_seconds: int = DEFAULT_NEWSLETTER_WINDOW_SECONDS,
    protected_rate_limit: int = DEFAULT_PROTECTED_RATE_LIMIT,
    protected_window_seconds: int = DEFAULT_PROTECTED_WINDOW_SECONDS,
    generate_max_body_bytes: int = DEFAULT_GENERATE_MAX_BODY_BYTES,
    get_redis_conn: Callable[[], Any] | None = None,
) -> None:
    """Register rate limiting and admin-token guard for operational routes.

    ``get_redis_conn`` — optional callable that returns a live Redis connection.
    When provided, rate limiting uses a shared Redis sliding-window counter so
    all worker processes enforce a single consistent limit.  When ``None`` (or
    when Redis is unavailable at request time), each process falls back to its
    own in-process ``SlidingWindowRateLimiter``.

    Rate-limit violations on generation endpoints are recorded in
    ``app.extensions["quota_abuse_tracker"]`` for ops observability.
    """
    env = environ or os.environ
    generate_limiter = RedisRateLimiter(get_redis=get_redis_conn)
    newsletter_limiter = RedisRateLimiter(get_redis=get_redis_conn)
    protected_limiter = RedisRateLimiter(get_redis=get_redis_conn)
    abuse_tracker = _QuotaAbuseTracker()
    app.extensions.setdefault("request_limiters", {})
    app.extensions["request_limiters"]["generate"] = generate_limiter
    app.extensions["request_limiters"]["newsletter"] = newsletter_limiter
    app.extensions["request_limiters"]["protected"] = protected_limiter
    app.extensions["quota_abuse_tracker"] = abuse_tracker

    @app.before_request  # type: ignore[untyped-decorator]
    def require_admin_api_token() -> ResponseReturnValue | None:
        if request.method == "OPTIONS":
            return None

        if _is_dev_like(app, env):
            return None

        client_identifier = _client_identifier()

        if request.path == "/api/generate":
            content_length = int(request.content_length or 0)
            if content_length > generate_max_body_bytes:
                return (
                    jsonify({"error": "Generate request body is too large"}),
                    413,
                )

            decision = generate_limiter.check(
                f"generate:{client_identifier}",
                limit=generate_rate_limit,
                window_seconds=generate_window_seconds,
            )
            if not decision.allowed:
                _record_abuse_event(
                    abuse_tracker,
                    client_identifier,
                    request.path,
                    decision.retry_after_seconds,
                )
                return _rate_limit_response(
                    message="Generate rate limit exceeded",
                    retry_after_seconds=decision.retry_after_seconds,
                )
            return None

        if request.path == "/newsletter":
            decision = newsletter_limiter.check(
                f"newsletter:{client_identifier}",
                limit=newsletter_rate_limit,
                window_seconds=newsletter_window_seconds,
            )
            if not decision.allowed:
                _record_abuse_event(
                    abuse_tracker,
                    client_identifier,
                    request.path,
                    decision.retry_after_seconds,
                )
                return _rate_limit_response(
                    message="Newsletter rate limit exceeded",
                    retry_after_seconds=decision.retry_after_seconds,
                )
            return None

        if not is_protected_route(request.path, prefixes):
            return None

        decision = protected_limiter.check(
            f"protected:{client_identifier}",
            limit=protected_rate_limit,
            window_seconds=protected_window_seconds,
        )
        if not decision.allowed:
            return _rate_limit_response(
                message="Protected route rate limit exceeded",
                retry_after_seconds=decision.retry_after_seconds,
            )

        configs = _resolve_all_token_configs(env)
        if not configs:
            LOGGER.error(
                "Protected web routes are enabled without %s configured.",
                ADMIN_TOKEN_ENV_VAR,
            )
            return (
                jsonify(
                    {"error": f"{ADMIN_TOKEN_ENV_VAR} is required for protected routes"}
                ),
                503,
            )

        provided_token = _resolve_provided_admin_token()
        if not provided_token:
            return jsonify({"error": "Admin API token required"}), 401

        required_scope = _scope_for_path(request.path)
        if required_scope is None:
            # Protected prefix with no scope mapping — fail closed.
            LOGGER.warning(
                "Protected route %s has no scope mapping; denying access.",
                request.path,
            )
            return jsonify({"error": "Admin API token required"}), 401

        authorized, token_label = _check_token_auth(
            provided_token, required_scope, configs
        )
        if authorized:
            LOGGER.debug(
                "Request authorized: path=%s scope=%s token=%s",
                request.path,
                required_scope,
                token_label,
            )
            return None

        if token_label is not None:
            # Token was recognised but lacks the required scope.
            LOGGER.warning(
                "Token %s lacks scope '%s' required for path %s",
                token_label,
                required_scope,
                request.path,
            )
            return (
                jsonify(
                    {
                        "error": "Insufficient token scope",
                        "required_scope": required_scope,
                    }
                ),
                403,
            )

        return jsonify({"error": "Admin API token required"}), 401
