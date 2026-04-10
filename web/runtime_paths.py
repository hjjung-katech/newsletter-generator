"""
Runtime-aware path helpers for web app bootstrap.

This module keeps filesystem decisions deterministic between development mode
and PyInstaller one-file runtime.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

from newsletter_core.infrastructure.platform._frozen import (
    get_bundle_root as _core_bundle_root,
)
from newsletter_core.infrastructure.platform._frozen import is_frozen_any as _is_frozen


def _bundle_root() -> Path:
    if _is_frozen():
        return _core_bundle_root()
    return Path(__file__).resolve().parent


def _web_dir() -> Path:
    return Path(__file__).resolve().parent


def _project_root() -> Path:
    if _is_frozen():
        return _bundle_root()
    return _web_dir().parent


def _first_existing_dir(candidates: Iterable[Path]) -> Path:
    candidate_list = list(candidates)
    for candidate in candidate_list:
        if candidate.is_dir():
            return candidate
    return candidate_list[0]


def resolve_template_dir() -> str:
    web_dir = _web_dir()
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


def resolve_static_dir() -> str:
    web_dir = _web_dir()
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


def resolve_database_path() -> str:
    if _is_frozen():
        return str(Path(sys.executable).resolve().parent / "storage.db")
    return str(_project_root() / ".local" / "state" / "web" / "storage.db")


def resolve_project_root() -> str:
    return str(_project_root())


def resolve_env_file_path() -> str:
    if _is_frozen():
        return str(Path(sys.executable).resolve().parent / ".env")
    return str(Path(resolve_project_root()) / ".env")
