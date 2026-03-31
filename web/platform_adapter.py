"""Minimal platform helpers for web runtime policy decisions."""

from __future__ import annotations

import platform


def get_platform_name() -> str:
    """Return the current OS name as reported by Python."""

    return platform.system()


def is_windows() -> bool:
    """Return whether the current runtime is Windows."""

    return get_platform_name() == "Windows"


def is_queue_enabled_for_platform() -> bool:
    """Mirror the current queue policy without changing app behavior yet."""

    return not is_windows()
