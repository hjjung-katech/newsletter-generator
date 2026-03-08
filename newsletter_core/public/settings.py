"""Public settings accessors for runtime adapters."""

from __future__ import annotations

import os
from typing import Any

from newsletter.centralized_settings import (
    clear_settings_cache,
    get_settings,
    is_running_in_pytest,
)

_SETTING_ALIASES = {
    "POSTMARK_FROM_EMAIL": "email_sender",
}

_SECRET_FIELDS = {
    "anthropic_api_key",
    "gemini_api_key",
    "google_client_secret",
    "openai_api_key",
    "postmark_server_token",
    "serper_api_key",
}


def _normalize_setting_key(name: str) -> str:
    key = str(name or "").strip()
    if not key:
        return ""
    return _SETTING_ALIASES.get(key.upper(), key.lower())


def get_setting_value(name: str, default: Any = None) -> Any:
    """Read a runtime setting by env-style or attribute-style key."""
    key = _normalize_setting_key(name)
    if not key:
        return default

    env_name = str(name or "").strip().upper()
    if is_running_in_pytest() and env_name and env_name in os.environ:
        clear_settings_cache()

    try:
        value = getattr(get_settings(), key)
    except Exception:
        return default

    if value is None:
        return default
    if key in _SECRET_FIELDS:
        return value.get_secret_value()
    return value


def get_llm_config() -> dict[str, Any]:
    return get_config_manager().get_llm_config()


def get_major_news_sources() -> dict[str, Any]:
    return get_config_manager().get_major_news_sources()


def get_all_major_news_sources() -> list[str]:
    sources = get_major_news_sources()
    return [*sources["tier1"], *sources["tier2"]]


def get_newsletter_settings() -> dict[str, Any]:
    return get_config_manager().get_newsletter_settings()


def get_email_config() -> tuple[str | None, str | None]:
    return (
        get_setting_value("POSTMARK_SERVER_TOKEN"),
        get_setting_value("EMAIL_SENDER"),
    )


def validate_email_config() -> dict[str, bool]:
    return get_config_manager().validate_email_config()


def get_config_manager() -> Any:
    from newsletter.config_manager import get_config_manager as _get_config_manager

    return _get_config_manager()


class _LazyConfigManager:
    """Lazy proxy to avoid eager config manager initialization at import time."""

    def __getattr__(self, item: str) -> Any:
        return getattr(get_config_manager(), item)

    def __repr__(self) -> str:  # pragma: no cover
        return "<LazyConfigManager proxy>"


config_manager = _LazyConfigManager()


__all__ = [
    "config_manager",
    "get_all_major_news_sources",
    "get_config_manager",
    "get_email_config",
    "get_llm_config",
    "get_major_news_sources",
    "get_newsletter_settings",
    "get_setting_value",
    "get_settings",
    "validate_email_config",
]
