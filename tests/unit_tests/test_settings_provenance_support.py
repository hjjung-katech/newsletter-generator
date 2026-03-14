from __future__ import annotations

import sys
from pathlib import Path

import pytest

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

import settings_provenance_support  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def test_build_effective_settings_provenance_marks_overridden_linked_context() -> None:
    provenance = settings_provenance_support.build_effective_settings_provenance(
        preset={"name": "Morning Brief", "is_default": True},
        preset_visibility={
            "availability_state": "available",
            "preset_type_label": "키워드 프리셋",
        },
        source_policy_visibility={
            "link_state": "matched",
            "status_label": "활성 정책 연결",
            "message": "활성 소스 정책 1개와 연결됩니다.",
        },
        personalization_visibility={
            "personalization_state": "overridden",
            "status_label": "오버라이드 적용",
            "source_policy_link_state": "matched",
            "source_policy_message": "활성 소스 정책 1개와 연결됩니다.",
        },
        latest_related_execution={
            "job_id": "job-1",
            "created_at": "2026-03-14T10:00:00Z",
            "execution_visibility": {
                "status_category": "completed",
                "status_label": "완료",
                "status_message": "최근 실행이 완료되었습니다.",
                "primary_timestamp": "2026-03-14T10:00:00Z",
            },
        },
    )

    assert provenance["effective_state"] == "overridden"
    assert provenance["status_label"] == "오버라이드된 설정 조합"
    assert provenance["default_mode_state"] == "overridden"
    assert provenance["linkage_state"] == "linked"
    assert provenance["has_recent_execution"] is True
    assert provenance["preset_name"] == "Morning Brief"
    assert provenance["summary_tokens"][0] == "프리셋: Morning Brief (기본)"
    assert provenance["diagnostics"] == {
        "primary_reason_code": None,
        "reason_codes": [],
        "summary": "",
        "details": [],
        "field_summary": "",
        "field_explanations": [],
    }


def test_build_effective_settings_provenance_marks_detached_context_without_recent_execution() -> (
    None
):
    provenance = settings_provenance_support.build_effective_settings_provenance(
        source_policy_visibility={
            "visibility_state": "detached",
            "status_label": "연결 없음",
            "status_message": "활성 정책이지만 연결된 프리셋이나 최근 적용 이력이 없습니다.",
            "linked_preset_count": 0,
        },
        personalization_visibility={
            "personalization_state": "default",
            "status_label": "기본 개인화",
            "source_policy_link_state": "detached",
            "source_policy_message": "활성 정책이지만 연결된 프리셋이나 최근 적용 이력이 없습니다.",
        },
    )

    assert provenance["effective_state"] == "detached"
    assert provenance["status_label"] == "부분 분리된 설정"
    assert provenance["has_recent_execution"] is False
    assert provenance["source_policy_state"] == "detached"
    assert provenance["default_mode_state"] == "default"
    assert (
        provenance["diagnostics"]["primary_reason_code"]
        == "source_policy_detached_from_presets"
    )
    assert provenance["diagnostics"]["reason_codes"] == [
        "source_policy_detached_from_presets",
        "personalization_default_only",
    ]
    assert "detached" in provenance["diagnostics"]["summary"]
    assert "프리셋 연결 축" in provenance["diagnostics"]["field_summary"]
    assert (
        provenance["diagnostics"]["field_explanations"][0]["axis"] == "preset_linkage"
    )
    assert (
        provenance["diagnostics"]["field_explanations"][0]["current_label"]
        == "연결된 preset 0개"
    )


def test_build_effective_settings_provenance_marks_recent_execution_mismatch() -> None:
    provenance = settings_provenance_support.build_effective_settings_provenance(
        source_policy_visibility={
            "visibility_state": "applied",
            "status_label": "최근 반영",
            "status_message": "최근 실행에서 이 정책이 실제로 반영되었습니다.",
            "linked_preset_count": 0,
        },
        preset_linkage_visibility={
            "link_state": "none",
            "message": "직접 연결된 도메인 프리셋이 없습니다.",
            "linked_preset_count": 0,
            "linked_default_preset_count": 0,
        },
        personalization_visibility={
            "personalization_state": "default",
            "status_label": "기본 개인화",
        },
        latest_related_execution={
            "job_id": "job-2",
            "created_at": "2026-03-14T10:30:00Z",
            "execution_visibility": {
                "status_category": "completed",
                "status_label": "완료",
                "status_message": "최근 실행이 완료되었습니다.",
                "primary_timestamp": "2026-03-14T10:30:00Z",
            },
        },
    )

    assert provenance["effective_state"] == "effective"
    assert (
        provenance["diagnostics"]["primary_reason_code"]
        == "recent_execution_not_reflected_by_current_settings"
    )
    assert provenance["diagnostics"]["reason_codes"][0] == (
        "recent_execution_not_reflected_by_current_settings"
    )
    assert "최근 관련 실행은 있지만" in provenance["diagnostics"]["summary"]
    assert (
        provenance["diagnostics"]["field_explanations"][0]["axis"] == "recent_execution"
    )
    assert (
        provenance["diagnostics"]["field_explanations"][0]["field"]
        == "settings_alignment"
    )
