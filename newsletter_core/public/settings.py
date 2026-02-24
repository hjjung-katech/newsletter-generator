"""Public settings accessors for runtime adapters."""

from __future__ import annotations

from newsletter.centralized_settings import get_settings
from newsletter.config_manager import config_manager

__all__ = ["config_manager", "get_settings"]
