"""Import-only tests to guard against dotenv side effects."""

from __future__ import annotations

import importlib
import sys

import dotenv
import pytest


def _clear_module_cache() -> None:
    prefixes = (
        "newsletter.config_manager",
        "newsletter.centralized_settings",
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
