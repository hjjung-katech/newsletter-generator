"""Public API for platform-specific behavior.

Usage::

    from newsletter_core.public.platform import get_platform_adapter

    adapter = get_platform_adapter()
    adapter.configure_utf8_io()
"""

from __future__ import annotations

from newsletter_core.infrastructure.platform._frozen import (
    get_bundle_root,
    is_frozen,
    is_frozen_any,
)
from newsletter_core.infrastructure.platform._protocol import PlatformAdapter
from newsletter_core.infrastructure.platform._resolver import get_platform_adapter

__all__ = [
    "PlatformAdapter",
    "get_platform_adapter",
    "is_frozen",
    "is_frozen_any",
    "get_bundle_root",
]
