from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT_DIR = Path(__file__).resolve().parents[2]
WEB_DIR = ROOT_DIR / "web"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

import routes_approval  # noqa: E402
from db_state import ensure_database_schema, get_history_row  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def _build_approval_app(database_path: str) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    routes_approval.register_approval_routes(app, database_path)
    return app


def _insert_history_row(
    db_path: str,
    *,
    job_id: str,
    approval_status: str,
    delivery_status: str,
    params: dict | None = None,
    result: dict | None = None,
) -> None:
    ensure_database_schema(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO history (
                id,
                params,
                result,
                status,
                approval_status,
                delivery_status
            )
            VALUES (?, ?, ?, 'completed', ?, ?)
            """,
            (
                job_id,
                json.dumps(params or {"keywords": ["AI"], "email": "test@example.com"}),
                json.dumps(result or {"html_content": "<html><body>ok</body></html>"}),
                approval_status,
                delivery_status,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def test_approval_inbox_returns_pending_items_only(tmp_path: Path) -> None:
    database_path = str(tmp_path / "storage.db")
    app = _build_approval_app(database_path)
    _insert_history_row(
        database_path,
        job_id="pending-job",
        approval_status="pending",
        delivery_status="pending_approval",
    )
    _insert_history_row(
        database_path,
        job_id="approved-job",
        approval_status="approved",
        delivery_status="approved",
    )

    with app.test_client() as client:
        response = client.get("/api/approvals")

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, list)
    assert [item["id"] for item in payload] == ["pending-job"]
    assert payload[0]["execution_visibility"]["status_category"] == "completed"
    assert payload[0]["approval_visibility"] == {
        "raw_approval_status": "pending",
        "approval_state": "pending",
        "approval_label": "승인 대기",
        "approval_message": "검토 후 승인 또는 반려할 수 있습니다.",
        "primary_timestamp": payload[0]["created_at"],
        "timestamp_label": "요청 시각",
        "can_resolve": True,
        "can_approve": True,
        "can_reject": True,
    }


def test_approval_inbox_all_filter_includes_resolved_visibility(tmp_path: Path) -> None:
    database_path = str(tmp_path / "storage.db")
    app = _build_approval_app(database_path)
    _insert_history_row(
        database_path,
        job_id="pending-job",
        approval_status="pending",
        delivery_status="pending_approval",
    )
    _insert_history_row(
        database_path,
        job_id="approved-job",
        approval_status="approved",
        delivery_status="approved",
    )

    with app.test_client() as client:
        response = client.get("/api/approvals?approval_status=all")

    assert response.status_code == 200
    payload = response.get_json()
    assert [item["id"] for item in payload] == ["pending-job", "approved-job"]
    approved_item = payload[1]
    assert approved_item["approval_visibility"]["approval_state"] == "approved"
    assert approved_item["approval_visibility"]["can_approve"] is False
    assert approved_item["approval_visibility"]["can_reject"] is False


def test_approve_route_marks_job_as_approved(tmp_path: Path) -> None:
    database_path = str(tmp_path / "storage.db")
    app = _build_approval_app(database_path)
    _insert_history_row(
        database_path,
        job_id="approve-me",
        approval_status="pending",
        delivery_status="pending_approval",
    )

    with app.test_client() as client:
        response = client.post(
            "/api/approvals/approve-me/approve",
            json={"note": "Looks good"},
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["approval_status"] == "approved"
    assert payload["delivery_status"] == "approved"
    assert payload["approved_at"]
    assert payload["approval_note"] == "Looks good"
    assert payload["approval_visibility"]["approval_state"] == "approved"
    assert payload["approval_visibility"]["can_approve"] is False
    assert (
        payload["execution_visibility"]["status_message"] == "생성은 완료되었고 발송 준비가 끝났습니다."
    )

    row = get_history_row(database_path, "approve-me")
    assert row is not None
    assert row["approval_status"] == "approved"
    assert row["delivery_status"] == "approved"
    assert row["approval_note"] == "Looks good"


def test_reject_route_marks_job_as_rejected_and_draft(tmp_path: Path) -> None:
    database_path = str(tmp_path / "storage.db")
    app = _build_approval_app(database_path)
    _insert_history_row(
        database_path,
        job_id="reject-me",
        approval_status="pending",
        delivery_status="pending_approval",
    )

    with app.test_client() as client:
        response = client.post(
            "/api/approvals/reject-me/reject",
            json={"note": "Need edits"},
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["approval_status"] == "rejected"
    assert payload["delivery_status"] == "draft"
    assert payload["rejected_at"]
    assert payload["approval_note"] == "Need edits"
    assert payload["approval_visibility"]["approval_state"] == "rejected"
    assert payload["approval_visibility"]["can_reject"] is False
    assert (
        payload["execution_visibility"]["status_message"]
        == "생성은 완료되었지만 반려되어 draft 상태로 유지됩니다."
    )

    row = get_history_row(database_path, "reject-me")
    assert row is not None
    assert row["approval_status"] == "rejected"
    assert row["delivery_status"] == "draft"
    assert row["approval_note"] == "Need edits"
