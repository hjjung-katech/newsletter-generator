"""Lazy compatibility layer for legacy config imports.

New runtime code should prefer `newsletter_core.public.settings`.
"""

from __future__ import annotations

from typing import Any

from newsletter_core.public.settings import (
    get_all_major_news_sources,
    get_llm_config,
    get_major_news_sources,
    get_setting_value,
    get_settings,
)

_CONFIG_MANAGER_FIELDS = {
    "ADDITIONAL_RSS_FEEDS",
    "ANTHROPIC_API_KEY",
    "EMAIL_SENDER",
    "GEMINI_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "NAVER_CLIENT_ID",
    "NAVER_CLIENT_SECRET",
    "OPENAI_API_KEY",
    "POSTMARK_SERVER_TOKEN",
    "SERPER_API_KEY",
}

__all__ = sorted(
    _CONFIG_MANAGER_FIELDS
    | {
        "ALL_MAJOR_NEWS_SOURCES",
        "LLM_CONFIG",
        "MAJOR_NEWS_SOURCES",
        "MOCK_MODE",
    }
)


def _cfg(name: str, default: Any = None) -> Any:
    """Safely read compatibility attributes from centralized settings."""
    return get_setting_value(name, default)


def __getattr__(name: str) -> Any:
    if name in _CONFIG_MANAGER_FIELDS:
        default = "" if name == "ADDITIONAL_RSS_FEEDS" else None
        return _cfg(name, default)
    if name == "LLM_CONFIG":
        return get_llm_config()
    if name == "MAJOR_NEWS_SOURCES":
        return get_major_news_sources()
    if name == "ALL_MAJOR_NEWS_SOURCES":
        return get_all_major_news_sources()
    if name == "MOCK_MODE":
        return bool(get_settings().mock_mode)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
