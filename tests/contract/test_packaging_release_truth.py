"""Contract tests for packaging and release truthfulness."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _read_pyproject() -> dict:
    return tomllib.loads(_read_text("pyproject.toml"))


def _read_manifest_entries(relative_path: str) -> list[str]:
    entries: list[str] = []
    for raw in _read_text(relative_path).splitlines():
        candidate = raw.strip()
        if not candidate or candidate.startswith("#"):
            continue
        entries.append(candidate)
    return entries


def test_support_policy_separates_packaging_target_from_release_channel() -> None:
    support_policy = _read_text("docs/reference/support-policy.md")

    assert "Linux server packaging" in support_policy
    assert "Dockerfile 기반 Linux container image" in support_policy
    assert "Railway/Nixpacks source deploy" in support_policy
    assert (
        "정식 release surface는 `dist/newsletter_web.exe`, `release-metadata.json`, `SHA256SUMS.txt`, `support-bundle.zip`"
        in support_policy
    )
    assert (
        "`update-manifest.json`은 release-gated/update-channel 경로에서만 추가"
        in support_policy
    )


def test_installation_and_release_docs_match_artifact_contract() -> None:
    installation = _read_text("docs/setup/INSTALLATION.md")
    railway = _read_text("docs/setup/RAILWAY_DEPLOYMENT.md")
    pyinstaller = _read_text("docs/setup/PYINSTALLER_WINDOWS.md")

    assert (
        "wheel/sdist는 `newsletter`/`newsletter_core` Python package subset 빌드 산출물"
        in installation
    )
    assert "루트 `Dockerfile`이 canonical container packaging target" in installation
    assert "Railway/Nixpacks는 현재 promoted release channel truth" in railway
    assert "Windows canonical desktop release surface" in pyinstaller
    assert "`dist\\SHA256SUMS.txt`" in pyinstaller
    assert "release-gated 경로에서만 생성" in pyinstaller


def test_pyproject_metadata_matches_non_end_user_packaging_contract() -> None:
    pyproject = _read_pyproject()
    project = pyproject["project"]
    classifiers = set(project["classifiers"])
    package_find = pyproject["tool"]["setuptools"]["packages"]["find"]

    assert project["license"] == "MIT"
    assert "License :: OSI Approved :: MIT License" not in classifiers
    assert pyproject["tool"]["setuptools"]["include-package-data"] is True
    assert package_find["include"] == [
        "newsletter",
        "newsletter.*",
        "newsletter_core",
        "newsletter_core.*",
    ]
    assert package_find["exclude"] == ["tests*"]
    assert package_find["namespaces"] is True
    assert pyproject["tool"]["setuptools"]["package-data"]["newsletter"] == [
        "templates/*.html",
        "templates/*.txt",
    ]


def test_release_manifests_match_existing_truth_files() -> None:
    packaging_manifest = _read_manifest_entries(
        ".release/manifests/release-packaging-policy.txt"
    )
    runtime_manifest = _read_manifest_entries(
        ".release/manifests/release-runtime-binary.txt"
    )

    assert "requirements-minimal.txt" not in runtime_manifest
    assert "pyproject.toml" in packaging_manifest
    assert "Dockerfile" in packaging_manifest
    assert "docs/reference/support-policy.md" in packaging_manifest
    assert "tests/contract/test_packaging_release_truth.py" in packaging_manifest

    for manifest_path in sorted((REPO_ROOT / ".release" / "manifests").glob("*.txt")):
        relative_manifest = str(manifest_path.relative_to(REPO_ROOT))
        for entry in _read_manifest_entries(relative_manifest):
            assert (REPO_ROOT / entry).exists(), entry


def test_packaging_configs_use_module_entrypoints_instead_of_web_cwd_shelling() -> None:
    dockerfile = _read_text("Dockerfile")
    railway = _read_text("railway.yml")
    nixpacks = _read_text("nixpacks.toml")

    assert "web.app:app" in dockerfile
    assert "cd web &&" not in dockerfile
    assert "web.app:app" in railway
    assert "python -m web.worker" in railway
    assert "python -m web.schedule_runner --interval 300" in railway
    assert "cd web &&" not in railway
    assert "web.app:app" in nixpacks
