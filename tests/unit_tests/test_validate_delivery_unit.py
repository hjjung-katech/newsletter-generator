"""Unit tests for delivery unit validator helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ci"))

import validate_delivery_unit as delivery_validator  # noqa: E402


def test_extract_field_value_supports_plain_and_bulleted_lines() -> None:
    pr_body = """
## Delivery Unit
RR: #123
- Delivery Unit ID: DU-20260316-doc-governance
Merge Boundary: squash
Rollback Boundary: revert
"""

    assert delivery_validator._extract_field_value(pr_body, "RR") == "#123"
    assert (
        delivery_validator._extract_field_value(pr_body, "Delivery Unit ID")
        == "DU-20260316-doc-governance"
    )


def test_looks_like_placeholder_detects_angle_bracket_tokens() -> None:
    assert delivery_validator._looks_like_placeholder("#<n>")
    assert delivery_validator._looks_like_placeholder("DU-YYYYMMDD-<topic>")
    assert not delivery_validator._looks_like_placeholder("#123")
    assert not delivery_validator._looks_like_placeholder("DU-20260316-governance")


def test_validate_delivery_unit_fields_accepts_filled_template() -> None:
    pr_body = """
## Delivery Unit
RR: #42
Delivery Unit ID: DU-20260316-delivery-governance
Merge Boundary: squash merge
Rollback Boundary: revert-merge-sha
"""

    (
        errors,
        rr_number,
        delivery_unit,
    ) = delivery_validator._validate_delivery_unit_fields(pr_body)

    assert errors == []
    assert rr_number == 42
    assert delivery_unit == "DU-20260316-delivery-governance"


def test_validate_delivery_unit_fields_rejects_placeholders_and_empty_values() -> None:
    pr_body = """
## Delivery Unit
RR: #<n>
Delivery Unit ID:
Merge Boundary: <merge-boundary>
Rollback Boundary:
"""

    (
        errors,
        rr_number,
        delivery_unit,
    ) = delivery_validator._validate_delivery_unit_fields(pr_body)

    assert rr_number is None
    assert delivery_unit is None
    assert (
        "Placeholder `RR: #<n>` must be replaced in `## Delivery Unit` section."
        in errors
    )
    assert (
        "Missing non-empty `Delivery Unit ID:` in `## Delivery Unit` section." in errors
    )
    assert (
        "Placeholder `Merge Boundary:` value must be replaced in "
        "`## Delivery Unit` section." in errors
    )
    assert (
        "Missing non-empty `Rollback Boundary:` in `## Delivery Unit` section."
        in errors
    )


def test_validate_delivery_unit_fields_rejects_fields_outside_delivery_unit_section() -> (
    None
):
    pr_body = """
RR: #123
Delivery Unit ID: DU-20260319-delivery-validator-hardening
Merge Boundary: squash
Rollback Boundary: revert

## Delivery Unit
(fields must not be accepted from outside this section)
"""

    (
        errors,
        rr_number,
        delivery_unit,
    ) = delivery_validator._validate_delivery_unit_fields(pr_body)

    assert rr_number is None
    assert delivery_unit is None
    assert "Missing `RR: #<number>` in `## Delivery Unit` section." in errors
    assert (
        "Missing non-empty `Delivery Unit ID:` in `## Delivery Unit` section." in errors
    )
    assert (
        "Missing non-empty `Merge Boundary:` in `## Delivery Unit` section." in errors
    )
    assert (
        "Missing non-empty `Rollback Boundary:` in `## Delivery Unit` section."
        in errors
    )


def test_validate_rr_issue_requires_review_request_label() -> None:
    issue = {"labels": []}

    errors = delivery_validator._validate_rr_issue(issue, 381)

    assert errors == ["Referenced RR #381 must have the `review-request` label."]


def test_validate_rr_issue_accepts_review_request_issue() -> None:
    issue = {"labels": [{"name": "review-request"}]}

    errors = delivery_validator._validate_rr_issue(issue, 381)

    assert errors == []
