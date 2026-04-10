"""Platform adapter protocol definition."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Protocol, runtime_checkable


@runtime_checkable
class PlatformAdapter(Protocol):
    """Abstraction over OS-specific runtime behavior.

    Implementations exist for Windows and Unix (macOS / Linux).
    """

    @property
    def name(self) -> str:
        """OS name as reported by *platform.system()* (e.g. ``"Windows"``)."""
        ...  # pragma: no cover

    @property
    def is_windows(self) -> bool:
        """``True`` when running on Windows."""
        ...  # pragma: no cover

    def configure_utf8_io(self) -> None:
        """Ensure *stdout* / *stderr* use UTF-8 encoding.

        On Windows this sets locale, env-vars and reconfigures streams.
        On Unix this is a no-op.
        """
        ...  # pragma: no cover

    def is_queue_supported(self) -> bool:
        """Return whether a Redis / RQ task queue is supported on this OS."""
        ...  # pragma: no cover

    def signal_names(self) -> List[str]:
        """Signal names to register for graceful shutdown."""
        ...  # pragma: no cover

    def venv_python_path(self, venv_dir: Path) -> Path:
        """Return the Python interpreter path inside *venv_dir*."""
        ...  # pragma: no cover
