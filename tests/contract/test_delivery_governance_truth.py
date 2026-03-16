"""Contract tests for delivery gate and RR lifecycle documentation truth."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_agents_declares_delivery_gate_and_authority_boundaries() -> None:
    agents = _read_text("AGENTS.md")

    required_entries = [
        "## Mandatory Delivery Gate",
        "[DELIVERY_CHECK]",
        "local-change-only",
        "Branch` is required when repo-tracked edits are made inside a git repository",
        "RR Reference: #<n>",
        "Delivery Unit ID",
        "changed files",
        "Silence is not permission to skip workflow.",
        "AGENTS.md` is authoritative for start-of-task behavior, handoff minimum, and the distinction between handoff and close-out.",
    ]

    for entry in required_entries:
        assert entry in agents


def test_ci_cd_guide_tracks_delivery_lifecycle_truth() -> None:
    ci_guide = _read_text("docs/dev/CI_CD_GUIDE.md")

    required_entries = [
        "## Delivery Lifecycle Authorities",
        "## Delivery Start Gate",
        "## Delivery Handoff and Close-out",
        "## Machine-checked PR Body Literals",
        "## Delivery Unit",
        "RR: #<n>",
        "Delivery Unit ID: <id>",
        "Merge Boundary:",
        "Rollback Boundary:",
        "RR Reference: #<n>",
        "PR metadata is the system-of-record for the actual current base branch.",
        "n/a` is allowed only for fields not required by the declared Stage.",
        "Template placeholders must be replaced before `pr-open` or `merged`.",
    ]

    for entry in required_entries:
        assert entry in ci_guide


def test_rr_and_pr_templates_expose_delivery_unit_slots() -> None:
    rr_template = _read_text(".github/ISSUE_TEMPLATE/review-request.yml")
    base_pr_template = _read_text(".github/pull_request_template.md")
    repo_hygiene_template = _read_text(".github/PULL_REQUEST_TEMPLATE/repo_hygiene.md")
    release_integration_template = _read_text(
        ".github/PULL_REQUEST_TEMPLATE/release_integration.md"
    )
    playbook = _read_text("docs/dev/AGENT_SKILL_REQUEST_PLAYBOOK.md")

    assert "label: Planned Base Branch" in rr_template

    for template in (
        base_pr_template,
        repo_hygiene_template,
        release_integration_template,
    ):
        assert "## Delivery Unit" in template
        assert "RR: #<n>" in template
        assert "Delivery Unit ID:" in template
        assert "Merge Boundary:" in template
        assert "Rollback Boundary:" in template

    for entry in (
        "Delivery mode: rr-branch-commit-pr",
        "RR Reference: #<n>",
        "Base branch: <base-branch>",
        "First output must begin with [DELIVERY_CHECK]",
    ):
        assert entry in playbook
