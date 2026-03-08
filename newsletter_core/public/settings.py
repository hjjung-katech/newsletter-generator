"""Public settings accessors for runtime adapters."""

from __future__ import annotations

from newsletter.centralized_settings import get_settings
from newsletter.config_manager import config_manager, get_config_manager


def get_llm_config() -> dict:
    return get_config_manager().get_llm_config()


def get_major_news_sources() -> dict:
    return get_config_manager().get_major_news_sources()


def get_all_major_news_sources() -> list:
    sources = get_major_news_sources()
    return [*sources["tier1"], *sources["tier2"]]


__all__ = [
    "config_manager",
    "get_all_major_news_sources",
    "get_config_manager",
    "get_llm_config",
    "get_major_news_sources",
    "get_settings",
]
