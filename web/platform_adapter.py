"""Minimal platform helpers for web runtime policy decisions.

This module delegates to :mod:`newsletter_core.public.platform` and exists
solely for backward compatibility with existing ``from web.platform_adapter``
imports.
"""

from __future__ import annotations

from newsletter_core.public.platform import get_platform_adapter as _get


def get_platform_name() -> str:
    """Return the current OS name as reported by Python."""

    return str(_get().name)


def is_windows() -> bool:
    """Return whether the current runtime is Windows."""

    return bool(_get().is_windows)


def is_queue_enabled_for_platform() -> bool:
    """Mirror the current queue policy without changing app behavior yet."""

    return bool(_get().is_queue_supported())
