"""Unit tests for newsletter_core.infrastructure.platform._paths."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from newsletter_core.infrastructure.platform._paths import (
    resolve_database_path,
    resolve_env_file_path,
    resolve_project_root,
    resolve_static_dir,
    resolve_template_dir,
)

pytestmark = [pytest.mark.unit]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_dev_web_dir(tmp_path: Path) -> Path:
    """Create a minimal web directory layout under *tmp_path* and return the
    fake ``__file__`` path that callers should pass as *_web_file*."""
    project_root = tmp_path / "project"
    web_dir = project_root / "web"
    (web_dir / "templates").mkdir(parents=True)
    (web_dir / "static").mkdir(parents=True)
    return web_dir / "runtime_paths.py"


# ---------------------------------------------------------------------------
# Dev-mode (non-frozen) tests
# ---------------------------------------------------------------------------


class TestPathResolution:
    def test_resolve_template_dir_dev_mode(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        web_file = _setup_dev_web_dir(tmp_path)
        monkeypatch.delattr(sys, "frozen", raising=False)
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)

        result = resolve_template_dir(str(web_file))

        assert result.endswith("templates")

    def test_resolve_static_dir_dev_mode(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        web_file = _setup_dev_web_dir(tmp_path)
        monkeypatch.delattr(sys, "frozen", raising=False)
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)

        result = resolve_static_dir(str(web_file))

        assert result.endswith("static")

    def test_resolve_database_path_dev_mode(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        web_file = _setup_dev_web_dir(tmp_path)
        monkeypatch.delattr(sys, "frozen", raising=False)
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)

        result = resolve_database_path(str(web_file))

        assert result.endswith("storage.db")

    def test_resolve_env_file_path_dev_mode(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        web_file = _setup_dev_web_dir(tmp_path)
        monkeypatch.delattr(sys, "frozen", raising=False)
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)

        result = resolve_env_file_path(str(web_file))

        assert result.endswith(".env")

    def test_resolve_project_root_dev_mode(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        web_file = _setup_dev_web_dir(tmp_path)
        monkeypatch.delattr(sys, "frozen", raising=False)
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)

        result = resolve_project_root(str(web_file))

        # Should be the parent of the web/ directory
        assert Path(result).is_dir()
        assert Path(result) == tmp_path / "project"

    def test_resolve_template_dir_returns_string(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        web_file = _setup_dev_web_dir(tmp_path)
        monkeypatch.delattr(sys, "frozen", raising=False)
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)

        result = resolve_template_dir(str(web_file))

        assert isinstance(result, str)

    def test_resolve_database_path_under_project_root(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        web_file = _setup_dev_web_dir(tmp_path)
        monkeypatch.delattr(sys, "frozen", raising=False)
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)

        project_root = resolve_project_root(str(web_file))
        db_path = resolve_database_path(str(web_file))

        assert db_path.startswith(project_root)

    def test_resolve_env_file_path_under_project_root(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        web_file = _setup_dev_web_dir(tmp_path)
        monkeypatch.delattr(sys, "frozen", raising=False)
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)

        project_root = resolve_project_root(str(web_file))
        env_path = resolve_env_file_path(str(web_file))

        assert env_path.startswith(project_root)

    # -----------------------------------------------------------------------
    # Frozen-mode tests
    # -----------------------------------------------------------------------

    def test_resolve_template_dir_frozen_mode(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        bundle_dir = tmp_path / "bundle"
        exe_dir = tmp_path / "exe"
        (exe_dir / "templates").mkdir(parents=True)
        (bundle_dir / "templates").mkdir(parents=True)

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)
        monkeypatch.setattr(sys, "executable", str(exe_dir / "app"))

        result = resolve_template_dir()

        # Prefers exe_dir/templates when it exists
        assert result == str(exe_dir / "templates")
        assert "templates" in result

    def test_resolve_template_dir_frozen_falls_back_to_bundle(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        bundle_dir = tmp_path / "bundle"
        exe_dir = tmp_path / "exe"
        # Only bundle has templates, not exe_dir
        (bundle_dir / "templates").mkdir(parents=True)
        exe_dir.mkdir(parents=True)

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)
        monkeypatch.setattr(sys, "executable", str(exe_dir / "app"))

        result = resolve_template_dir()

        assert str(tmp_path) in result
        assert "templates" in result

    def test_resolve_static_dir_frozen_mode(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        bundle_dir = tmp_path / "bundle"
        exe_dir = tmp_path / "exe"
        (exe_dir / "static").mkdir(parents=True)
        (bundle_dir / "static").mkdir(parents=True)

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)
        monkeypatch.setattr(sys, "executable", str(exe_dir / "app"))

        result = resolve_static_dir()

        assert result == str(exe_dir / "static")
        assert "static" in result

    def test_resolve_database_path_frozen_mode(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        bundle_dir = tmp_path / "bundle"
        exe_dir = tmp_path / "exe"
        exe_dir.mkdir(parents=True)
        bundle_dir.mkdir(parents=True)

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)
        monkeypatch.setattr(sys, "executable", str(exe_dir / "app"))

        result = resolve_database_path()

        assert result.endswith("storage.db")
        assert str(exe_dir) in result

    def test_resolve_env_file_path_frozen_mode(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        bundle_dir = tmp_path / "bundle"
        exe_dir = tmp_path / "exe"
        exe_dir.mkdir(parents=True)
        bundle_dir.mkdir(parents=True)

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)
        monkeypatch.setattr(sys, "executable", str(exe_dir / "app"))

        result = resolve_env_file_path()

        assert result.endswith(".env")
        assert str(exe_dir) in result

    def test_resolve_project_root_frozen_mode(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        bundle_dir = tmp_path / "bundle"
        bundle_dir.mkdir(parents=True)

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)
        monkeypatch.setattr(sys, "executable", str(tmp_path / "exe" / "app"))

        result = resolve_project_root()

        # In frozen mode, project root is bundle_root (i.e. _MEIPASS)
        assert result == str(bundle_dir)

    # -----------------------------------------------------------------------
    # No _web_file fallback (package-root based)
    # -----------------------------------------------------------------------

    def test_resolve_project_root_no_web_file_returns_directory(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delattr(sys, "frozen", raising=False)
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)

        result = resolve_project_root()

        assert Path(result).is_dir()

    def test_resolve_template_dir_no_web_file_returns_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delattr(sys, "frozen", raising=False)
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)

        result = resolve_template_dir()

        assert isinstance(result, str)
        assert "templates" in result
