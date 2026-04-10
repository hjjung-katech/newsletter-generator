from __future__ import annotations

import platform

import pytest

import newsletter_core.infrastructure.platform._resolver as _resolver_mod
import newsletter_core.infrastructure.platform._unix as _unix_mod
from web.platform_adapter import (
    get_platform_name,
    is_queue_enabled_for_platform,
    is_windows,
)


def _patch_platform(monkeypatch: pytest.MonkeyPatch, fn):
    """Patch platform.system across all modules that use it."""
    monkeypatch.setattr(platform, "system", fn)
    monkeypatch.setattr(_resolver_mod.platform, "system", fn)
    monkeypatch.setattr(_unix_mod.platform, "system", fn)


@pytest.mark.unit
def test_windows_platform_reports_disabled_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_platform(monkeypatch, lambda: "Windows")

    assert get_platform_name() == "Windows"
    assert is_windows() is True
    assert is_queue_enabled_for_platform() is False


@pytest.mark.unit
def test_non_windows_platform_reports_enabled_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_platform(monkeypatch, lambda: "Linux")

    assert get_platform_name() == "Linux"
    assert is_windows() is False
    assert is_queue_enabled_for_platform() is True


@pytest.mark.unit
def test_platform_detection_rechecks_runtime_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that each call re-evaluates the platform via the adapter."""
    _patch_platform(monkeypatch, lambda: "Darwin")
    assert get_platform_name() == "Darwin"
    assert is_windows() is False

    _patch_platform(monkeypatch, lambda: "Windows")
    assert get_platform_name() == "Windows"
    assert is_windows() is True
