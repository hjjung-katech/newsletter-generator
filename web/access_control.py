"""Minimal access control for sensitive Flask operational routes."""

from __future__ import annotations

import logging
import os
from hmac import compare_digest
from typing import Mapping

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue

LOGGER = logging.getLogger(__name__)

ADMIN_TOKEN_ENV_VAR = "ADMIN_API_TOKEN"  # nosec B105
ADMIN_TOKEN_HEADER = "X-Admin-Token"  # nosec B105

_PROTECTED_PREFIXES: tuple[str, ...] = (
    "/api/history",
    "/api/analytics",
    "/api/presets",
    "/api/approvals",
    "/api/source-policies",
    "/api/schedule",
    "/api/schedules",
    "/api/send-email",
    "/api/email-config",
    "/api/test-email",
)


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


def configure_access_control(
    app: Flask,
    *,
    environ: Mapping[str, str] | None = None,
    prefixes: tuple[str, ...] = _PROTECTED_PREFIXES,
) -> None:
    """Register a minimal admin-token guard for sensitive operational routes."""
    env = environ or os.environ

    @app.before_request  # type: ignore[untyped-decorator]
    def require_admin_api_token() -> ResponseReturnValue | None:
        if request.method == "OPTIONS" or not is_protected_route(
            request.path, prefixes
        ):
            return None

        if _is_dev_like(app, env):
            return None

        expected_token = _resolve_expected_admin_token(env)
        if not expected_token:
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
        if not provided_token or not compare_digest(provided_token, expected_token):
            return jsonify({"error": "Admin API token required"}), 401

        return None
