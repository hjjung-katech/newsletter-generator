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
        "newsletter.settings",
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
    _clear_module_cache()
    public_settings = importlib.import_module("newsletter_core.public.settings")
    monkeypatch.setattr(
        public_settings,
        "get_setting_value",
        lambda name, default=None: {
            "SERPER_API_KEY": "serper-test-key",
            "ADDITIONAL_RSS_FEEDS": "https://example.com/rss.xml",
            "EMAIL_SENDER": "sender@example.com",
            "POSTMARK_SERVER_TOKEN": "postmark-test-token",
            "MOCK_MODE": True,
        }.get(name, default),
    )
    monkeypatch.setattr(
        public_settings, "get_llm_config", lambda: {"default_provider": "gemini"}
    )
    monkeypatch.setattr(
        public_settings,
        "get_major_news_sources",
        lambda: {"tier1": ["A"], "tier2": ["B"]},
    )
    monkeypatch.setattr(
        public_settings,
        "get_newsletter_settings",
        lambda: {"newsletter_title": "Configured Title"},
    )
    monkeypatch.setattr(
        public_settings,
        "validate_email_config",
        lambda: {
            "postmark_token_configured": True,
            "from_email_configured": True,
            "ready": True,
        },
    )

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
def test_legacy_settings_import_is_lazy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_module_cache()
    centralized_settings = importlib.import_module("newsletter.centralized_settings")
    calls = {"count": 0}

    def _fake_get_settings():
        calls["count"] += 1
        raise AssertionError("get_settings should not run at import time")

    monkeypatch.setattr(centralized_settings, "get_settings", _fake_get_settings)
    importlib.import_module("newsletter.settings")
    assert calls["count"] == 0


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
