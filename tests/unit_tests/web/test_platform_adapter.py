from __future__ import annotations

import platform

import pytest

from web.platform_adapter import (
    get_platform_name,
    is_queue_enabled_for_platform,
    is_windows,
)


@pytest.mark.unit
def test_windows_platform_reports_disabled_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    assert get_platform_name() == "Windows"
    assert is_windows() is True
    assert is_queue_enabled_for_platform() is False


@pytest.mark.unit
def test_non_windows_platform_reports_enabled_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Linux")

    assert get_platform_name() == "Linux"
    assert is_windows() is False
    assert is_queue_enabled_for_platform() is True


@pytest.mark.unit
def test_platform_detection_rechecks_runtime_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = iter(["Darwin", "Windows"])
    monkeypatch.setattr(platform, "system", lambda: next(values))

    assert get_platform_name() == "Darwin"
    assert is_windows() is True
