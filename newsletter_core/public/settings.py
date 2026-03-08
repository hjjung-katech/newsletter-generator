"""Public settings accessors for runtime adapters."""

from __future__ import annotations

from typing import Any

from newsletter.centralized_settings import get_settings
from newsletter.config_manager import config_manager, get_config_manager


def get_llm_config() -> dict:
    return get_config_manager().get_llm_config()


def get_major_news_sources() -> dict:
    return get_config_manager().get_major_news_sources()


def get_all_major_news_sources() -> list:
    sources = get_major_news_sources()
    return [*sources["tier1"], *sources["tier2"]]


def get_newsletter_settings() -> dict[str, Any]:
    return get_config_manager().get_newsletter_settings()


def get_email_config() -> tuple[str | None, str | None]:
    try:
        settings = get_settings()
        return (
            settings.postmark_server_token.get_secret_value()
            if settings.postmark_server_token
            else None,
            settings.email_sender,
        )
    except Exception:
        manager = get_config_manager()
        return manager.POSTMARK_SERVER_TOKEN, manager.EMAIL_SENDER


def validate_email_config() -> dict[str, bool]:
    return get_config_manager().validate_email_config()


__all__ = [
    "config_manager",
    "get_email_config",
    "get_all_major_news_sources",
    "get_config_manager",
    "get_llm_config",
    "get_major_news_sources",
    "get_newsletter_settings",
    "get_settings",
    "validate_email_config",
]
