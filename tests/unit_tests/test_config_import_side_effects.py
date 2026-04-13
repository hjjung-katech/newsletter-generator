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
        "newsletter.config_manager",
        "newsletter.centralized_settings",
        "newsletter.cli",
        "newsletter.graph",
        "newsletter_core.application.graph_composition",
        "newsletter_core.application.graph_node_helpers",
        "newsletter.llm_factory",
        "newsletter_core.application.graph_workflow",
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


@pytest.mark.unit
def test_graph_workflow_helper_import_does_not_call_load_dotenv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0}

    def _fake_load_dotenv(*_args, **_kwargs):
        calls["count"] += 1
        return False

    monkeypatch.setattr(dotenv, "load_dotenv", _fake_load_dotenv)
    _clear_module_cache()
    importlib.import_module("newsletter_core.application.graph_workflow")
    assert calls["count"] == 0


@pytest.mark.unit
def test_graph_node_helper_import_does_not_call_load_dotenv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0}

    def _fake_load_dotenv(*_args, **_kwargs):
        calls["count"] += 1
        return False

    monkeypatch.setattr(dotenv, "load_dotenv", _fake_load_dotenv)
    _clear_module_cache()
    importlib.import_module("newsletter_core.application.graph_node_helpers")
    assert calls["count"] == 0


@pytest.mark.unit
def test_graph_composition_helper_import_does_not_call_load_dotenv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0}

    def _fake_load_dotenv(*_args, **_kwargs):
        calls["count"] += 1
        return False

    monkeypatch.setattr(dotenv, "load_dotenv", _fake_load_dotenv)
    _clear_module_cache()
    importlib.import_module("newsletter_core.application.graph_composition")
    assert calls["count"] == 0
