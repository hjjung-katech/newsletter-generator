"""Unix (macOS / Linux) platform adapter implementation."""

from __future__ import annotations

import platform
from pathlib import Path
from typing import List


class UnixPlatformAdapter:
    """Adapter for Unix-like systems (macOS and Linux)."""

    @property
    def name(self) -> str:  # noqa: D401
        return platform.system()  # "Darwin" or "Linux"

    @property
    def is_windows(self) -> bool:
        return False

    def configure_utf8_io(self) -> None:
        """No-op on Unix — UTF-8 is the default encoding."""

    def is_queue_supported(self) -> bool:
        return True

    def signal_names(self) -> List[str]:
        return ["SIGINT", "SIGTERM"]

    def venv_python_path(self, venv_dir: Path) -> Path:
        return venv_dir / "bin" / "python"
