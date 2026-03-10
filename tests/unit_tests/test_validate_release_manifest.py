"""Unit tests for release manifest validation helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_release_manifest as manifest_validator  # noqa: E402


def test_find_duplicate_entries_returns_unique_duplicates() -> None:
    duplicates = manifest_validator.find_duplicate_entries(
        ["a.txt", "b.txt", "a.txt", "a.txt", "b.txt"]
    )

    assert duplicates == ["a.txt", "b.txt"]


def test_find_missing_manifest_paths_flags_stale_entries(tmp_path: Path) -> None:
    existing = tmp_path / "present.txt"
    existing.write_text("ok", encoding="utf-8")

    missing = manifest_validator.find_missing_manifest_paths(
        ["present.txt", "missing.txt"], repo_root=tmp_path
    )

    assert missing == ["missing.txt"]


def test_find_out_of_scope_files_flags_missing_manifest_entries() -> None:
    extra = manifest_validator.find_out_of_scope_files(
        {"pyproject.toml", "docs/reference/support-policy.md"},
        {"pyproject.toml"},
    )

    assert extra == ["docs/reference/support-policy.md"]


def test_validate_manifest_inventory_detects_duplicate_and_missing_paths(
    tmp_path: Path,
) -> None:
    (tmp_path / "existing.txt").write_text("ok", encoding="utf-8")
    manifest = tmp_path / "manifest.txt"
    manifest.write_text(
        "existing.txt\nmissing.txt\nexisting.txt\n",
        encoding="utf-8",
    )

    duplicates, missing = manifest_validator.validate_manifest_inventory(
        manifest, repo_root=tmp_path
    )

    assert duplicates == ["existing.txt"]
    assert missing == ["missing.txt"]
