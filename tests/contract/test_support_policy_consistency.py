"""Contract tests for support policy and documentation truthfulness."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _read_pyproject() -> dict:
    return tomllib.loads(_read_text("pyproject.toml"))


def test_support_policy_is_listed_in_active_docs_hubs() -> None:
    assert "docs/reference/support-policy.md" in _read_text("README.md")
    assert "reference/support-policy.md" in _read_text("docs/README.md")
    assert "reference/support-policy.md" in _read_text("docs/DOCUMENT_INVENTORY.md")


def test_support_policy_freezes_option_b_contract() -> None:
    support_policy = _read_text("docs/reference/support-policy.md")

    required_phrases = [
        "Option B. Server parity + desktop exception",
        "Linux는 canonical production server다.",
        "Windows는 canonical native desktop bundle 대상이다.",
        "macOS는 2차 지원이며 source-based development와 smoke 중심이다.",
        "2026-06-30",
        "3.13 | experimental source-only",
        "PyPI는 정식 end-user 릴리즈 채널이 아니다",
        "canonical packaging target은 Dockerfile 기반 Linux container image",
        "promoted Docker image release lane은 아직 운영하지 않는다",
    ]

    for phrase in required_phrases:
        assert phrase in support_policy


def test_support_policy_documents_canonical_artifacts_and_entrypoints() -> None:
    support_policy = _read_text("docs/reference/support-policy.md")

    required_entries = [
        "`python -m web.app`",
        "`python -m newsletter ...`",
        "`dist/newsletter_web.exe`",
        "`release-metadata.json`",
        "`SHA256SUMS.txt`",
        "`support-bundle.zip`",
        "wheel/sdist",
        "Windows desktop 배포",
        "Linux server 운영",
    ]

    for entry in required_entries:
        assert entry in support_policy


def test_python_metadata_matches_support_contract() -> None:
    pyproject = _read_pyproject()
    project = pyproject["project"]
    classifiers = set(project["classifiers"])

    assert project["requires-python"] == ">=3.11"
    assert "Operating System :: OS Independent" not in classifiers
    assert "Programming Language :: Python :: 3.10" not in classifiers
    assert "Programming Language :: Python :: 3.11" in classifiers
    assert "Programming Language :: Python :: 3.12" in classifiers
    assert pyproject["tool"]["black"]["target-version"] == ["py311"]
    assert pyproject["tool"]["mypy"]["python_version"] == "3.11"


def test_workflow_count_docs_match_repository() -> None:
    workflow_files = sorted(
        path.name for path in (REPO_ROOT / ".github" / "workflows").glob("*.yml")
    )
    assert len(workflow_files) == 7

    ci_guide = _read_text("docs/dev/CI_CD_GUIDE.md")
    ci_guide_match = re.search(r"현재 운영 워크플로우는 아래 (\d+)개입니다\.", ci_guide)
    assert ci_guide_match is not None
    assert int(ci_guide_match.group(1)) == len(workflow_files)

    workflows_readme = _read_text(".github/workflows/README.md")
    workflows_match = re.search(r"canonical 워크플로우는 아래 (\d+)개입니다\.", workflows_readme)
    assert workflows_match is not None
    assert int(workflows_match.group(1)) == len(workflow_files)


def test_canonical_source_runtime_port_is_documented_as_8000() -> None:
    assert "PORT=8000" in _read_text(".env.example")

    web_app = _read_text("web/app.py")
    web_app_match = re.search(r'PORT", "(\d+)"\)', web_app)
    assert web_app_match is not None
    assert web_app_match.group(1) == "8000"

    assert "http://localhost:8000" in _read_text("docs/reference/web-api.md")
    assert "`8000`" in _read_text("docs/reference/environment-variables.md")
    assert "http://localhost:8000" in _read_text("docs/setup/LOCAL_SETUP.md")
    assert "http://localhost:8000" in _read_text("docs/user/email-sending.md")


def test_windows_exe_port_exception_is_documented_truthfully() -> None:
    web_exe_entrypoint = _read_text("scripts/devtools/web_exe_entrypoint.py")
    entrypoint_match = re.search(r'PORT", (\d+)\)', web_exe_entrypoint)
    assert entrypoint_match is not None
    assert entrypoint_match.group(1) == "5000"

    pyinstaller_guide = _read_text("docs/setup/PYINSTALLER_WINDOWS.md")
    assert "Python 3.12 설치 권장" in pyinstaller_guide
    assert "3.13은 experimental source-only" in pyinstaller_guide
    assert "../reference/support-policy.md" in pyinstaller_guide
    assert "compatibility default 포트 `5000`" in _read_text(
        "docs/setup/PYINSTALLER_WINDOWS.md"
    )
    assert "compatibility default port `5000`" in _read_text(
        "docs/reference/support-policy.md"
    )


def test_installation_docs_do_not_claim_unshipped_release_channels() -> None:
    installation = _read_text("docs/setup/INSTALLATION.md")

    assert "PyPI 패키지 (정식 릴리즈 채널 아님)" in installation
    assert "Docker 이미지 (정식 릴리즈 artifact 아님)" in installation
    assert "Dockerfile`이 canonical container packaging target" in installation
