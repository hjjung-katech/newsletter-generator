"""Import-only tests to guard against dotenv side effects."""

from __future__ import annotations

import importlib
import sys

import dotenv
import pytest


def _clear_module_cache() -> None:
    prefixes = (
        "newsletter.config",
        "newsletter.config_manager",
        "newsletter.centralized_settings",
        "newsletter_core.public.settings",
    )
    for name in list(sys.modules):
        if name.startswith(prefixes):
            del sys.modules[name]


@pytest.mark.unit
def test_config_manager_import_does_not_call_load_dotenv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0}

    def _fake_load_dotenv(*_args, **_kwargs):
        calls["count"] += 1
        return False

    monkeypatch.setattr(dotenv, "load_dotenv", _fake_load_dotenv)
    _clear_module_cache()
    importlib.import_module("newsletter.config_manager")
    assert calls["count"] == 0


@pytest.mark.unit
def test_centralized_settings_import_does_not_call_load_dotenv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0}

    def _fake_load_dotenv(*_args, **_kwargs):
        calls["count"] += 1
        return False

    monkeypatch.setattr(dotenv, "load_dotenv", _fake_load_dotenv)
    _clear_module_cache()
    importlib.import_module("newsletter.centralized_settings")
    assert calls["count"] == 0


@pytest.mark.unit
def test_legacy_config_import_is_lazy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_module_cache()
    config_manager_module = importlib.import_module("newsletter.config_manager")
    calls = {"count": 0}

    def _fake_init(self) -> None:
        calls["count"] += 1
        self._initialized = True

    monkeypatch.setattr(config_manager_module.ConfigManager, "__init__", _fake_init)
    importlib.import_module("newsletter.config")
    assert calls["count"] == 0


@pytest.mark.unit
def test_legacy_config_attributes_resolve_through_public_accessors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _DummyConfigManager:
        SERPER_API_KEY = "serper-test-key"
        ADDITIONAL_RSS_FEEDS = "https://example.com/rss.xml"

        def get_llm_config(self) -> dict:
            return {"default_provider": "gemini"}

        def get_major_news_sources(self) -> dict:
            return {"tier1": ["A"], "tier2": ["B"]}

    class _DummySettings:
        mock_mode = True

    _clear_module_cache()
    public_settings = importlib.import_module("newsletter_core.public.settings")
    monkeypatch.setattr(
        public_settings, "get_config_manager", lambda: _DummyConfigManager()
    )
    monkeypatch.setattr(public_settings, "get_settings", lambda: _DummySettings())

    legacy_config = importlib.import_module("newsletter.config")

    assert legacy_config.SERPER_API_KEY == "serper-test-key"
    assert legacy_config.ADDITIONAL_RSS_FEEDS == "https://example.com/rss.xml"
    assert legacy_config.LLM_CONFIG == {"default_provider": "gemini"}
    assert legacy_config.MAJOR_NEWS_SOURCES == {"tier1": ["A"], "tier2": ["B"]}
    assert legacy_config.ALL_MAJOR_NEWS_SOURCES == ["A", "B"]
    assert legacy_config.MOCK_MODE is True
