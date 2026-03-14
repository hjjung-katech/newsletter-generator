from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest
from flask import Flask

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

import routes_presets  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def _build_preset_app(database_path: str) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    routes_presets.register_preset_routes(app, database_path)
    return app


def _insert_history_row(
    *,
    database_path: str,
    job_id: str,
    params: dict,
    result: dict,
    created_at: str,
    status: str = "completed",
    approval_status: str = "not_requested",
    delivery_status: str = "draft",
) -> None:
    conn = sqlite3.connect(database_path)
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
                json.dumps(params),
                json.dumps(result),
                created_at,
                status,
                approval_status,
                delivery_status,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _insert_source_policy(
    *,
    database_path: str,
    policy_id: str,
    pattern: str,
    policy_type: str = "allow",
    is_active: bool = True,
) -> None:
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO source_policies (id, pattern, policy_type, is_active)
            VALUES (?, ?, ?, ?)
            """,
            (policy_id, pattern, policy_type, int(is_active)),
        )
        conn.commit()
    finally:
        conn.close()


def test_preset_routes_create_and_list(tmp_path: Path) -> None:
    app = _build_preset_app(str(tmp_path / "storage.db"))

    payload = {
        "name": "Weekly AI Digest",
        "description": "Compact weekly summary",
        "is_default": True,
        "params": {
            "keywords": ["AI", "robotics"],
            "template_style": "compact",
            "email_compatible": True,
            "period": 7,
            "email": "test@example.com",
            "rrule": "FREQ=WEEKLY;BYDAY=MO,WE;BYHOUR=9;BYMINUTE=0",
        },
    }

    with app.test_client() as client:
        create_response = client.post(
            "/api/presets",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert create_response.status_code == 201
        created = create_response.get_json()
        assert created is not None
        assert created["name"] == "Weekly AI Digest"
        assert created["is_default"] is True
        assert created["params"]["keywords"] == ["AI", "robotics"]
        assert created["params"]["rrule"].startswith("FREQ=WEEKLY")
        assert created["preset_visibility"]["availability_state"] == "available"
        assert created["preset_visibility"]["preset_type"] == "scheduled"
        assert created["latest_related_execution"] is None
        assert created["source_policy_visibility"]["link_state"] == "unavailable"
        assert (
            created["personalization_visibility"]["personalization_state"]
            == "overridden"
        )
        assert (
            created["effective_settings_provenance"]["effective_state"] == "overridden"
        )
        assert (
            created["effective_settings_provenance"]["default_mode_state"]
            == "overridden"
        )
        assert created["personalization_visibility"]["override_labels"] == [
            "이메일 호환 모드",
            "기간",
        ]

        list_response = client.get("/api/presets")
        assert list_response.status_code == 200
        presets = list_response.get_json()

    assert isinstance(presets, list)
    assert presets[0]["id"] == created["id"]
    assert presets[0]["is_default"] is True
    assert presets[0]["preset_visibility"]["recent_usage_state"] == "empty"


def test_update_route_promotes_single_default_preset(tmp_path: Path) -> None:
    app = _build_preset_app(str(tmp_path / "storage.db"))

    first_payload = {
        "name": "Daily AI",
        "is_default": True,
        "params": {
            "keywords": ["AI"],
            "template_style": "compact",
            "email_compatible": False,
            "period": 1,
        },
    }
    second_payload = {
        "name": "Domain Watch",
        "is_default": False,
        "params": {
            "domain": "semiconductor",
            "template_style": "detailed",
            "email_compatible": True,
            "period": 14,
        },
    }

    with app.test_client() as client:
        first_response = client.post(
            "/api/presets",
            data=json.dumps(first_payload),
            content_type="application/json",
        )
        second_response = client.post(
            "/api/presets",
            data=json.dumps(second_payload),
            content_type="application/json",
        )

        first = first_response.get_json()
        second = second_response.get_json()
        assert first_response.status_code == 201
        assert second_response.status_code == 201

        update_response = client.put(
            f"/api/presets/{second['id']}",
            data=json.dumps(
                {
                    "name": "Domain Watch",
                    "description": "Promoted preset",
                    "is_default": True,
                    "params": {
                        "domain": "semiconductor",
                        "template_style": "modern",
                        "email_compatible": True,
                        "period": 30,
                    },
                }
            ),
            content_type="application/json",
        )
        assert update_response.status_code == 200

        list_response = client.get("/api/presets")
        presets = list_response.get_json()

    assert isinstance(presets, list)
    preset_by_id = {preset["id"]: preset for preset in presets}
    assert preset_by_id[first["id"]]["is_default"] is False
    assert preset_by_id[second["id"]]["is_default"] is True
    assert preset_by_id[second["id"]]["params"]["template_style"] == "modern"
    assert preset_by_id[second["id"]]["params"]["period"] == 30


def test_delete_route_removes_preset(tmp_path: Path) -> None:
    app = _build_preset_app(str(tmp_path / "storage.db"))

    with app.test_client() as client:
        create_response = client.post(
            "/api/presets",
            data=json.dumps(
                {
                    "name": "Delete Me",
                    "params": {
                        "keywords": ["ai"],
                        "template_style": "compact",
                        "email_compatible": False,
                        "period": 7,
                    },
                }
            ),
            content_type="application/json",
        )
        preset = create_response.get_json()
        assert create_response.status_code == 201

        delete_response = client.delete(f"/api/presets/{preset['id']}")
        assert delete_response.status_code == 200
        assert delete_response.get_json() == {
            "success": True,
            "deleted_id": preset["id"],
        }

        list_response = client.get("/api/presets")
        assert list_response.status_code == 200
        assert list_response.get_json() == []


def test_list_route_adds_recent_execution_and_source_policy_visibility(
    tmp_path: Path,
) -> None:
    db_path = str(tmp_path / "storage.db")
    app = _build_preset_app(db_path)

    payload = {
        "name": "Domain Watch",
        "description": "Monitor Reuters domain",
        "is_default": False,
        "params": {
            "domain": "https://www.reuters.com",
            "template_style": "modern",
            "email_compatible": True,
            "period": 14,
            "email": "ops@example.com",
        },
    }

    with app.test_client() as client:
        create_response = client.post(
            "/api/presets",
            data=json.dumps(payload),
            content_type="application/json",
        )
        created = create_response.get_json()
        assert create_response.status_code == 201
        assert created is not None

    _insert_history_row(
        database_path=db_path,
        job_id="job-preset-1",
        params={
            "domain": "reuters.com",
            "template_style": "modern",
            "email_compatible": True,
            "period": 14,
            "email": "ops@example.com",
        },
        result={"title": "Reuters daily digest"},
        created_at="2026-03-13T08:00:00Z",
    )
    _insert_source_policy(
        database_path=db_path,
        policy_id="policy-1",
        pattern="reuters.com",
        policy_type="allow",
    )

    with app.test_client() as client:
        list_response = client.get("/api/presets")
        assert list_response.status_code == 200
        presets = list_response.get_json()

    assert isinstance(presets, list)
    preset = presets[0]
    assert preset["latest_related_execution"]["job_id"] == "job-preset-1"
    assert (
        preset["latest_related_execution"]["execution_visibility"]["status_category"]
        == "completed"
    )
    assert preset["source_policy_visibility"]["link_state"] == "matched"
    assert preset["source_policy_visibility"]["match_count"] == 1
    assert preset["preset_visibility"]["has_recent_related_execution"] is True
    assert preset["preset_visibility"]["has_source_policy_link"] is True
    assert preset["personalization_visibility"]["has_recent_related_execution"] is True
    assert preset["personalization_visibility"]["source_policy_link_state"] == "matched"
    assert preset["effective_settings_provenance"]["effective_state"] == "overridden"
    assert preset["effective_settings_provenance"]["linkage_state"] == "linked"
    assert preset["effective_settings_provenance"]["has_recent_execution"] is True
