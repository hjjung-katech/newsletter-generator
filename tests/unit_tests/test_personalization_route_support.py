from __future__ import annotations

import sys
from pathlib import Path

import pytest

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

import personalization_route_support  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def test_build_personalization_visibility_marks_default_params() -> None:
    visibility = personalization_route_support.build_personalization_visibility(
        {
            "keywords": ["AI"],
            "template_style": "compact",
            "email_compatible": False,
            "period": 14,
        }
    )

    assert visibility == {
        "personalization_state": "default",
        "status_label": "기본 개인화",
        "status_message": "현재 개인화 설정은 기본값으로 유지됩니다.",
        "effective_template_style": "compact",
        "effective_period": 14,
        "email_compatible": False,
        "email_mode_label": "기본 모드",
        "override_count": 0,
        "override_labels": [],
        "has_archive_context": False,
        "archive_reference_count": 0,
        "source_policy_override_count": 0,
        "source_policy_link_state": "unknown",
        "source_policy_message": "",
        "has_recent_related_execution": False,
        "recent_usage_state": "empty",
        "recent_usage_label": "연관 실행 없음",
        "recent_usage_timestamp": None,
    }


def test_build_personalization_visibility_marks_overrides_and_linkage() -> None:
    visibility = personalization_route_support.build_personalization_visibility(
        {
            "domain": "reuters.com",
            "template_style": "modern",
            "email_compatible": True,
            "period": 7,
            "archive_reference_ids": ["job-1"],
            "source_allowlist": ["reuters.com"],
        },
        source_policy_visibility={
            "link_state": "matched",
            "message": "활성 소스 정책 1개와 연결됩니다.",
        },
        latest_related_execution={
            "job_id": "job-1",
            "created_at": "2026-03-14T03:00:00Z",
        },
    )

    assert visibility["personalization_state"] == "overridden"
    assert visibility["status_label"] == "오버라이드 적용"
    assert visibility["override_count"] == 5
    assert visibility["override_labels"] == [
        "템플릿 스타일",
        "이메일 호환 모드",
        "기간",
        "아카이브 컨텍스트",
        "소스 정책 오버라이드",
    ]
    assert visibility["archive_reference_count"] == 1
    assert visibility["source_policy_override_count"] == 1
    assert visibility["source_policy_link_state"] == "matched"
    assert visibility["source_policy_message"] == "활성 소스 정책 1개와 연결됩니다."
    assert visibility["has_recent_related_execution"] is True
    assert visibility["recent_usage_timestamp"] == "2026-03-14T03:00:00Z"
