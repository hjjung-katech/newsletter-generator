"""
Platform-specific signal handler registration.

Provides :func:`setup_signal_handlers` which wires platform-appropriate
POSIX signals and, on Windows, the Windows Console Control Handler.
This module has no dependency on ShutdownManager; callers pass in
callbacks so the two remain decoupled.
"""

from __future__ import annotations

import signal
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from newsletter_core.infrastructure.platform._protocol import PlatformAdapter


def setup_signal_handlers(
    signal_handler: Callable[[int, Any], None],
    console_event_handler: Callable[[int], bool],
    adapter: "PlatformAdapter",
) -> Optional[Any]:
    """Register platform-appropriate signal handlers.

    Registers *signal_handler(signum, frame)* for each name returned by
    ``adapter.signal_names()``.  On Windows, also registers
    *console_event_handler(ctrl_type)* via ``SetConsoleCtrlHandler``.

    Returns the Windows console handler object (caller must keep a reference
    to prevent garbage collection) or ``None`` on non-Windows platforms.
    """
    for sig_name in adapter.signal_names():
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, signal_handler)
        except (OSError, ValueError):
            pass

    if adapter.is_windows:
        return _register_windows_console_handler(console_event_handler)

    return None


def _register_windows_console_handler(
    event_handler: Callable[[int], bool],
) -> Optional[Any]:
    """Register *event_handler* with ``SetConsoleCtrlHandler``.

    Returns the ctypes handler object (keep alive!) or ``None`` if
    registration fails or ctypes is unavailable.
    """
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        HANDLER_ROUTINE = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)
        handler = HANDLER_ROUTINE(event_handler)
        if kernel32.SetConsoleCtrlHandler(handler, True):
            return handler
        return None
    except Exception:
        return None
