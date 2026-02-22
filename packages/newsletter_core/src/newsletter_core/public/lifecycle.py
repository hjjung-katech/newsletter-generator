"""Public lifecycle primitives for runtime adapters."""

from __future__ import annotations

from newsletter.utils.shutdown_manager import (
    ShutdownPhase,
    get_shutdown_manager,
    is_shutdown_requested,
    register_shutdown_task,
)

__all__ = [
    "ShutdownPhase",
    "get_shutdown_manager",
    "is_shutdown_requested",
    "register_shutdown_task",
]
