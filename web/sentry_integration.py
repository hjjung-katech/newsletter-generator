"""
Sentry initialization helpers for the Flask web runtime.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from newsletter_core.public.settings import get_setting_value

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
        print("[WARN] Sentry SDK not installed, skipping Sentry integration")
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
        print(f"[WARN] Sentry initialization failed: {exc}")
        return callbacks


def setup_sentry() -> SentryCallbacks:
    callbacks: SentryCallbacks = (
        _noop_set_sentry_user_context,
        _noop_set_sentry_tags,
    )

    dsn = get_setting_value("SENTRY_DSN")
    if not dsn:
        print("[INFO] Sentry DSN not configured, skipping Sentry integration")
        return callbacks

    return _init_sentry(
        dsn=str(dsn),
        traces_sample_rate=float(get_setting_value("SENTRY_TRACES_SAMPLE_RATE", 0.1)),
        environment=str(get_setting_value("ENVIRONMENT", "production")),
        release=str(get_setting_value("APP_VERSION", "1.0.0")),
        profiles_sample_rate=float(
            get_setting_value("SENTRY_PROFILES_SAMPLE_RATE", 0.1)
        ),
        success_label="[OK] Sentry initialized successfully",
    )
