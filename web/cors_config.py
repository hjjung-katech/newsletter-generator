"""CORS configuration helpers for the canonical Flask runtime."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping, Sequence

from flask import Flask
from flask_cors import CORS

LOGGER = logging.getLogger(__name__)

_DEV_ALLOWED_ORIGINS: tuple[str, ...] = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def _is_dev_like(app: Flask, environ: Mapping[str, str] | None = None) -> bool:
    env = environ or os.environ
    if app.config.get("TESTING"):
        return True

    for value in (
        app.config.get("ENV"),
        env.get("APP_ENV"),
        env.get("FLASK_ENV"),
        env.get("ENVIRONMENT"),
    ):
        if str(value or "").strip().lower() in {
            "development",
            "dev",
            "testing",
            "test",
            "local",
        }:
            return True

    return False


def resolve_allowed_cors_origins(
    app: Flask, environ: Mapping[str, str] | None = None
) -> tuple[str, ...]:
    """Return the allowed cross-origin origins for the Flask runtime."""
    env = environ or os.environ
    configured_origins = [
        origin.strip()
        for origin in env.get("ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]

    if not configured_origins:
        return _DEV_ALLOWED_ORIGINS if _is_dev_like(app, env) else ()

    if configured_origins == ["*"]:
        if _is_dev_like(app, env):
            return _DEV_ALLOWED_ORIGINS

        LOGGER.warning(
            "Ignoring wildcard ALLOWED_ORIGINS for canonical Flask runtime in non-development mode."
        )
        return ()

    # Preserve input order while removing duplicates.
    return tuple(dict.fromkeys(configured_origins))


def configure_cors(app: Flask, environ: Mapping[str, str] | None = None) -> CORS | None:
    """Apply restrictive CORS settings when explicit origins are available."""
    origins = resolve_allowed_cors_origins(app, environ)
    if not origins:
        return None

    resources: dict[str, dict[str, Sequence[str]]] = {
        r"/api/*": {"origins": origins},
        r"/health": {"origins": origins},
    }

    return CORS(
        app,
        resources=resources,
        supports_credentials=False,
        methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Idempotency-Key"],
        max_age=600,
    )
