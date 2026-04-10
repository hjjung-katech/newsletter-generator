"""Windows platform adapter implementation."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List


class WindowsPlatformAdapter:
    """Adapter for Windows-specific runtime behavior."""

    @property
    def name(self) -> str:  # noqa: D401
        return "Windows"

    @property
    def is_windows(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # UTF-8 I/O configuration
    # ------------------------------------------------------------------

    def configure_utf8_io(self) -> None:
        """Set environment variables, locale, and stream encoding to UTF-8.

        Consolidates the duplicated logic previously found in:
        - ``newsletter/cli.py:_configure_windows_utf8_io()``
        - ``scripts/devtools/run_tests.py`` (module-level block)
        - ``run_ci_checks.py`` (module-level block)
        - ``web/runtime_hook.py`` (module-level block)
        """

        if not sys.platform.startswith("win"):
            return  # safety guard when called outside Windows

        import io
        import locale

        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        os.environ.setdefault("PYTHONUTF8", "1")

        try:
            locale.setlocale(locale.LC_ALL, "ko_KR.UTF-8")
        except locale.Error:
            try:
                locale.setlocale(locale.LC_ALL, ".65001")
            except locale.Error:
                pass

        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        else:  # pragma: no cover - legacy Python fallback
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, encoding="utf-8", errors="replace"
            )
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer, encoding="utf-8", errors="replace"
            )

        if hasattr(sys, "_setdefaultencoding"):  # pragma: no cover
            sys._setdefaultencoding("utf-8")

    # ------------------------------------------------------------------
    # Queue support
    # ------------------------------------------------------------------

    def is_queue_supported(self) -> bool:
        return False

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def signal_names(self) -> List[str]:
        return ["SIGINT", "SIGTERM", "SIGBREAK"]

    # ------------------------------------------------------------------
    # Virtual-environment paths
    # ------------------------------------------------------------------

    def venv_python_path(self, venv_dir: Path) -> Path:
        return venv_dir / "Scripts" / "python.exe"
