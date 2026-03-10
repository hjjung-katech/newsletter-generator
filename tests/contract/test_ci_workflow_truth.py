"""Contract tests for CI workflow truthfulness and gate coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_main_ci_enforces_release_and_platform_contracts() -> None:
    workflow = _read_text(".github/workflows/main-ci.yml")

    required_entries = [
        "name: Release Preflight",
        "name: Source Smoke (${{ matrix.os }})",
        "name: Container Smoke (ubuntu-latest)",
        "os: [ubuntu-latest, macos-latest, windows-latest]",
        "git fetch --force --tags origin",
        "python scripts/release_preflight.py",
        "python scripts/validate_release_manifest.py",
        "Create required directories",
        ".local/state/web",
        "python -m pytest",
        "python -m scripts.devtools.dev_entrypoint smoke web",
        "tests/contract/test_packaging_release_truth.py",
        "tests/contract/test_support_policy_consistency.py",
        "tests/contract/test_ci_workflow_truth.py",
        "tests/unit_tests/test_validate_release_manifest.py",
        "tests/unit_tests/test_web_import_side_effects.py",
        "tests/unit_tests/web/test_runtime_paths.py",
        "tests/contract/test_web_runtime_contract.py",
        "docker build -t newsletter-generator:ci .",
        "scripts/devtools/web_health_smoke.py --mode http",
    ]

    for entry in required_entries:
        assert entry in workflow


def test_active_docs_describe_ci_gate_split_truthfully() -> None:
    ci_guide = _read_text("docs/dev/CI_CD_GUIDE.md")
    support_policy = _read_text("docs/reference/support-policy.md")
    workflow_readme = _read_text(".github/workflows/README.md")

    for text in (ci_guide, workflow_readme):
        assert "policy-check" in text
        assert "docs-quality" in text
        assert "Code Quality & Security" in text
        assert "Unit Tests - ubuntu-latest-py3.11" in text
        assert "Unit Tests - ubuntu-latest-py3.12" in text
        assert "Release Preflight" in text
        assert "Source Smoke (ubuntu-latest)" in text
        assert "Source Smoke (macos-latest)" in text
        assert "Source Smoke (windows-latest)" in text
        assert "Build Check (ubuntu-latest)" in text
        assert "Build Check (windows-latest)" in text
        assert "Container Smoke (ubuntu-latest)" in text

    assert "macOS source smoke + runtime subset" in ci_guide
    assert "Windows source smoke + runtime subset" in ci_guide
    assert "Linux container smoke" in ci_guide
    assert "Mock API Tests" in ci_guide
    assert "branch protection required check" in ci_guide
    assert "branch protection required check" in support_policy
    assert (
        "macOS | 2차 지원 | source/smoke 중심 | source smoke + runtime subset"
        in support_policy
    )
    assert (
        "Windows | 1차 지원 | 정식 지원 | source smoke + runtime subset + PyInstaller build"
        in support_policy
    )


def test_release_ci_platform_manifest_tracks_new_ci_truth_files() -> None:
    manifest = _read_text(".release/manifests/release-ci-platform.txt")

    required_entries = [
        "docs/dev/CI_CD_GUIDE.md",
        "scripts/devtools/dev_entrypoint.py",
        "scripts/devtools/web_health_smoke.py",
        "tests/contract/test_ci_workflow_truth.py",
        "tests/unit_tests/test_dev_entrypoint.py",
        "tests/unit_tests/test_web_health_smoke.py",
    ]

    for entry in required_entries:
        assert entry in manifest
