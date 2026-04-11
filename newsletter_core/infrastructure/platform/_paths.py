"""Centralised path-resolution helpers for web-app bootstrap.

Owns the logic that was previously scattered across ``web/runtime_paths.py``.
All frozen-state detection is delegated to ``_frozen.py``.

When called from ``web/runtime_paths``, the optional ``_web_file`` argument
should be ``__file__`` of that module so that monkeypatching in tests continues
to work correctly (the test suite patches ``runtime_paths.__file__``).
When called directly (e.g. from ``__init__.py`` or third-party callers),
``_web_file`` defaults to ``None`` and paths are derived from the real
``web/`` directory relative to the package root.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, Optional

from newsletter_core.infrastructure.platform._frozen import (
    get_bundle_root as _get_bundle_root,
)
from newsletter_core.infrastructure.platform._frozen import is_frozen_any as _is_frozen

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _package_root() -> Path:
    """Return the project root by walking up from *this* file.

    Layout: newsletter_core/infrastructure/platform/_paths.py
    parents[0] = platform/
    parents[1] = infrastructure/
    parents[2] = newsletter_core/
    parents[3] = <project-root>
    """
    return Path(__file__).resolve().parents[3]


def _bundle_root() -> Path:
    if _is_frozen():
        return Path(_get_bundle_root())
    return _package_root()


def _resolve_web_dir(web_file: Optional[str]) -> Path:
    """Return the ``web/`` directory.

    * If *web_file* is provided (e.g. ``__file__`` from ``runtime_paths.py``)
      the parent of that file is used — this makes monkeypatching in tests work.
    * Otherwise the real ``web/`` sibling of the package root is used.
    """
    if web_file is not None:
        return Path(web_file).resolve().parent
    return _package_root() / "web"


def _resolve_project_root(web_file: Optional[str]) -> Path:
    if _is_frozen():
        return Path(_get_bundle_root())
    return _resolve_web_dir(web_file).parent


def _first_existing_dir(candidates: Iterable[Path]) -> Path:
    candidate_list = list(candidates)
    for candidate in candidate_list:
        if candidate.is_dir():
            return candidate
    return candidate_list[0]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_template_dir(_web_file: Optional[str] = None) -> str:
    web_dir = _resolve_web_dir(_web_file)
    if _is_frozen():
        bundle_root = _bundle_root()
        exe_dir = Path(sys.executable).resolve().parent
        return str(
            _first_existing_dir(
                [
                    exe_dir / "templates",
                    bundle_root / "templates",
                    bundle_root / "web" / "templates",
                ]
            )
        )
    return str(
        _first_existing_dir([web_dir / "templates", web_dir.parent / "templates"])
    )


def resolve_static_dir(_web_file: Optional[str] = None) -> str:
    web_dir = _resolve_web_dir(_web_file)
    if _is_frozen():
        bundle_root = _bundle_root()
        exe_dir = Path(sys.executable).resolve().parent
        return str(
            _first_existing_dir(
                [
                    exe_dir / "static",
                    bundle_root / "static",
                    bundle_root / "web" / "static",
                ]
            )
        )
    return str(_first_existing_dir([web_dir / "static", web_dir.parent / "static"]))


def resolve_database_path(_web_file: Optional[str] = None) -> str:
    if _is_frozen():
        return str(Path(sys.executable).resolve().parent / "storage.db")
    return str(
        _resolve_project_root(_web_file) / ".local" / "state" / "web" / "storage.db"
    )


def resolve_project_root(_web_file: Optional[str] = None) -> str:
    return str(_resolve_project_root(_web_file))


def resolve_env_file_path(_web_file: Optional[str] = None) -> str:
    if _is_frozen():
        return str(Path(sys.executable).resolve().parent / ".env")
    return str(Path(resolve_project_root(_web_file)) / ".env")
