"""
Sentry initialization helpers for the Flask web runtime.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any

SentryUserContextSetter = Callable[..., None]
SentryTagSetter = Callable[..., None]
SentryCallbacks = tuple[SentryUserContextSetter, SentryTagSetter]


def _noop_set_sentry_user_context(*args: Any, **kwargs: Any) -> None:
    del args, kwargs


def _noop_set_sentry_tags(**kwargs: Any) -> None:
    del kwargs


def _build_callbacks(sentry_sdk_module: Any) -> SentryCallbacks:
    def set_sentry_user_context(
        user_id: Any = None, email: Any = None, **kwargs: Any
    ) -> None:
        sentry_sdk_module.set_user({"id": user_id, "email": email, **kwargs})

    def set_sentry_tags(**tags: Any) -> None:
        for key, value in tags.items():
            sentry_sdk_module.set_tag(key, value)

    return set_sentry_user_context, set_sentry_tags


def _init_sentry(
    *,
    dsn: str,
    traces_sample_rate: float,
    environment: str,
    release: str,
    profiles_sample_rate: float,
    success_label: str,
) -> SentryCallbacks:
    callbacks: SentryCallbacks = (
        _noop_set_sentry_user_context,
        _noop_set_sentry_tags,
    )

    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError:
        print("⚠️  Sentry SDK not installed, skipping Sentry integration")
        return callbacks

    try:
        logging_integration = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR,
        )

        sentry_sdk.init(
            dsn=dsn,
            integrations=[
                FlaskIntegration(transaction_style="endpoint"),
                logging_integration,
            ],
            traces_sample_rate=traces_sample_rate,
            environment=environment,
            release=release,
            profiles_sample_rate=profiles_sample_rate,
            before_send=lambda event, hint: (
                event if event.get("level") != "info" else None
            ),
        )
        print(success_label)
        return _build_callbacks(sentry_sdk)
    except Exception as exc:
        print(f"⚠️  Sentry initialization failed: {exc}")
        return callbacks


def setup_sentry() -> SentryCallbacks:
    callbacks: SentryCallbacks = (
        _noop_set_sentry_user_context,
        _noop_set_sentry_tags,
    )

    try:
        from newsletter_core.public.settings import get_settings

        settings = get_settings()
        if settings.sentry_dsn:
            return _init_sentry(
                dsn=settings.sentry_dsn,
                traces_sample_rate=settings.sentry_traces_sample_rate,
                environment=settings.environment,
                release=settings.app_version,
                profiles_sample_rate=settings.sentry_profiles_sample_rate,
                success_label="✅ Sentry initialized successfully",
            )

        print("ℹ️  Sentry DSN not configured, skipping Sentry integration")
        return callbacks
    except Exception as exc:
        print(
            f"⚠️  Centralized settings unavailable, checking legacy SENTRY_DSN: {exc}"
        )

    legacy_dsn = os.getenv("SENTRY_DSN")
    if not legacy_dsn:
        print("ℹ️  Legacy SENTRY_DSN not configured, skipping Sentry integration")
        return callbacks

    return _init_sentry(
        dsn=legacy_dsn,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        environment=os.getenv("ENVIRONMENT", "production"),
        release=os.getenv("APP_VERSION", "1.0.0"),
        profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1")),
        success_label="✅ Sentry initialized successfully (legacy mode)",
    )
