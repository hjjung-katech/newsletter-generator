from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

import source_policy_route_support  # noqa: E402
from db_state import (  # noqa: E402
    create_generation_preset,
    create_source_policy,
    ensure_database_schema,
    list_source_policies,
)

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def _insert_history_row(
    *,
    db_path: str,
    job_id: str,
    input_params: dict,
    created_at: str,
    status: str = "completed",
) -> None:
    ensure_database_schema(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO history (
                id,
                params,
                result,
                created_at,
                status,
                approval_status,
                delivery_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                json.dumps({"domain": "reuters.com"}),
                json.dumps(
                    {
                        "title": "Reuters Digest",
                        "input_params": input_params,
                    }
                ),
                created_at,
                status,
                "not_requested",
                "draft",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def test_enrich_source_policy_entry_marks_active_policy_as_detached_without_links(
    tmp_path: Path,
) -> None:
    db_path = str(tmp_path / "storage.db")
    ensure_database_schema(db_path)
    create_source_policy(
        db_path,
        "policy_allow",
        "reuters.com",
        "allow",
        is_active=True,
    )

    policy = list_source_policies(db_path)[0]
    enriched = source_policy_route_support.enrich_source_policy_entry(db_path, policy)

    assert enriched["latest_related_execution"] is None
    assert enriched["preset_linkage_visibility"] == {
        "link_state": "none",
        "message": "직접 연결된 도메인 프리셋이 없습니다.",
        "linked_preset_count": 0,
        "linked_default_preset_count": 0,
    }
    assert enriched["source_policy_visibility"]["visibility_state"] == "detached"
    assert enriched["source_policy_visibility"]["status_label"] == "연결 없음"
    assert enriched["source_policy_visibility"]["recent_usage_state"] == "empty"
    assert enriched["effective_settings_provenance"]["effective_state"] == "detached"
    assert enriched["effective_settings_provenance"]["linkage_state"] == "detached"
    assert (
        enriched["effective_settings_provenance"]["diagnostics"]["primary_reason_code"]
        == "source_policy_detached_from_presets"
    )


def test_enrich_source_policy_entry_adds_preset_and_execution_visibility(
    tmp_path: Path,
) -> None:
    db_path = str(tmp_path / "storage.db")
    ensure_database_schema(db_path)
    create_source_policy(
        db_path,
        "policy_allow",
        "https://www.reuters.com",
        "allow",
        is_active=True,
    )
    create_generation_preset(
        db_path,
        "preset_reuters",
        "Reuters Watch",
        "Monitor Reuters",
        {
            "domain": "reuters.com",
            "template_style": "compact",
            "email_compatible": True,
            "period": 14,
        },
        is_default=True,
    )
    _insert_history_row(
        db_path=db_path,
        job_id="job-source-policy",
        input_params={
            "source_allowlist": ["reuters.com"],
            "source_blocklist": [],
        },
        created_at="2026-03-13T09:00:00Z",
    )

    policy = list_source_policies(db_path)[0]
    enriched = source_policy_route_support.enrich_source_policy_entry(db_path, policy)

    assert enriched["linked_presets"] == [
        {
            "id": "preset_reuters",
            "name": "Reuters Watch",
            "is_default": True,
            "domain": "reuters.com",
        }
    ]
    assert enriched["preset_linkage_visibility"] == {
        "link_state": "matched",
        "message": "연결된 도메인 프리셋 1개, 기본 프리셋 1개",
        "linked_preset_count": 1,
        "linked_default_preset_count": 1,
    }
    assert enriched["latest_related_execution"]["job_id"] == "job-source-policy"
    assert enriched["latest_related_execution"]["title"] == "Reuters Digest"
    assert (
        enriched["latest_related_execution"]["execution_visibility"]["status_category"]
        == "completed"
    )
    assert enriched["source_policy_visibility"]["visibility_state"] == "applied"
    assert enriched["source_policy_visibility"]["linked_preset_count"] == 1
    assert enriched["source_policy_visibility"]["linked_default_preset_count"] == 1
    assert enriched["source_policy_visibility"]["recent_usage_state"] == "recent"
    assert enriched["effective_settings_provenance"]["effective_state"] == "effective"
    assert enriched["effective_settings_provenance"]["linked_preset_count"] == 1
    assert enriched["effective_settings_provenance"]["has_recent_execution"] is True
    assert (
        enriched["effective_settings_provenance"]["diagnostics"]["primary_reason_code"]
        is None
    )
