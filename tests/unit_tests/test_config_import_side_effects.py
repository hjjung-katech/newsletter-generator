"""Import-only tests to guard against dotenv side effects."""

from __future__ import annotations

import importlib
import os
import sys

import dotenv
import pytest


def _clear_module_cache() -> None:
    exact_names = {"newsletter"}
    prefixes = (
        "newsletter.config",
        "newsletter.config_manager",
        "newsletter.centralized_settings",
        "newsletter.cli",
        "newsletter.llm_factory",
        "newsletter_core.public.settings",
    )
    for name in list(sys.modules):
        if name in exact_names or name.startswith(prefixes):
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

        def get_newsletter_settings(self) -> dict:
            return {"newsletter_title": "Configured Title"}

        def validate_email_config(self) -> dict:
            return {
                "postmark_token_configured": True,
                "from_email_configured": True,
                "ready": True,
            }

    class _DummySecret:
        def get_secret_value(self) -> str:
            return "postmark-test-token"

    class _DummySettings:
        mock_mode = True
        email_sender = "sender@example.com"
        postmark_server_token = _DummySecret()

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
    assert public_settings.get_newsletter_settings() == {
        "newsletter_title": "Configured Title"
    }
    assert public_settings.get_email_config() == (
        "postmark-test-token",
        "sender@example.com",
    )
    assert public_settings.validate_email_config() == {
        "postmark_token_configured": True,
        "from_email_configured": True,
        "ready": True,
    }


@pytest.mark.unit
def test_package_import_does_not_set_generation_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GENERATION_DATE", raising=False)
    monkeypatch.delenv("GENERATION_TIMESTAMP", raising=False)
    _clear_module_cache()

    importlib.import_module("newsletter")

    assert "GENERATION_DATE" not in os.environ
    assert "GENERATION_TIMESTAMP" not in os.environ


@pytest.mark.unit
def test_cli_import_does_not_call_load_dotenv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0}

    def _fake_load_dotenv(*_args, **_kwargs):
        calls["count"] += 1
        return False

    monkeypatch.setattr(dotenv, "load_dotenv", _fake_load_dotenv)
    _clear_module_cache()
    importlib.import_module("newsletter.cli")
    assert calls["count"] == 0


@pytest.mark.unit
def test_llm_factory_import_does_not_mutate_google_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "GOOGLE_APPLICATION_CREDENTIALS", "/tmp/nonexistent-credentials.json"
    )
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "sample-project")
    monkeypatch.setenv("CLOUDSDK_CONFIG", "/tmp/gcloud-config")
    monkeypatch.setenv("GCLOUD_PROJECT", "sample-gcloud-project")
    before = {
        key: os.environ.get(key)
        for key in (
            "GOOGLE_APPLICATION_CREDENTIALS",
            "GOOGLE_CLOUD_PROJECT",
            "CLOUDSDK_CONFIG",
            "GCLOUD_PROJECT",
        )
    }

    _clear_module_cache()
    module = importlib.import_module("newsletter.llm_factory")

    after = {
        key: os.environ.get(key)
        for key in (
            "GOOGLE_APPLICATION_CREDENTIALS",
            "GOOGLE_CLOUD_PROJECT",
            "CLOUDSDK_CONFIG",
            "GCLOUD_PROJECT",
        )
    }

    assert after == before
    assert repr(module.llm_factory) == "<LazyLLMFactory proxy>"
