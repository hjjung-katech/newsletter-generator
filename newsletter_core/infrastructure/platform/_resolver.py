"""Resolve the correct platform adapter for the current OS."""

from __future__ import annotations

import platform

from newsletter_core.infrastructure.platform._protocol import PlatformAdapter


def get_platform_adapter() -> PlatformAdapter:
    """Return a :class:`PlatformAdapter` matching the current operating system.

    Uses lazy imports so that Windows-only modules (e.g. ``ctypes.windll``)
    are never loaded on Unix.
    """

    if platform.system() == "Windows":
        from newsletter_core.infrastructure.platform._windows import (
            WindowsPlatformAdapter,
        )

        return WindowsPlatformAdapter()

    from newsletter_core.infrastructure.platform._unix import UnixPlatformAdapter

    return UnixPlatformAdapter()
