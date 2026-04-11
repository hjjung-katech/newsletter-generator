"""Unified PyInstaller / frozen-binary detection.

Consolidates the duplicated logic previously found in:
- ``web/runtime_paths.py:_is_frozen()``
- ``web/binary_compatibility.py:is_frozen()``
- ``web/path_manager.py:PathManager._is_frozen``
"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """Strict check: running inside a PyInstaller bundle with ``_MEIPASS``."""

    return bool(getattr(sys, "frozen", False)) and hasattr(sys, "_MEIPASS")


def is_frozen_any() -> bool:
    """Lenient check: ``sys.frozen`` is set (any bundler, not just PyInstaller)."""

    return bool(getattr(sys, "frozen", False))


def get_bundle_root() -> Path:
    """Return the bundle root directory.

    * When frozen with ``_MEIPASS`` → that temporary extraction directory.
    * Otherwise → the parent of *this* file (i.e. the ``platform`` package dir).
    """

    if is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent
