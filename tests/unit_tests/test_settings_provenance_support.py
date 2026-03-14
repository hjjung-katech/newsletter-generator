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
