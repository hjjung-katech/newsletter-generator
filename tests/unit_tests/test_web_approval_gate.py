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

import routes_send_email  # noqa: E402
import tasks  # noqa: E402
from db_state import ensure_database_schema, get_history_row  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def _build_send_email_app(database_path: str) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    routes_send_email.register_send_email_route(app, database_path)
    return app


def _insert_history_row(
    db_path: str,
    *,
    job_id: str,
    params: dict,
    result: dict,
    status: str = "completed",
    approval_status: str = "not_requested",
    delivery_status: str = "draft",
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
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                json.dumps(params),
                json.dumps(result),
                status,
                approval_status,
                delivery_status,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def test_generate_task_marks_email_job_pending_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = str(tmp_path / "storage.db")
    ensure_database_schema(database_path)

    monkeypatch.setattr(
        tasks,
        "generate_newsletter",
        lambda request: {
            "status": "success",
            "html_content": "<html><body>approval</body></html>",
            "title": "Approval Newsletter",
            "generation_stats": {},
            "input_params": {"keywords": request.keywords},
        },
    )

    send_calls: list[dict[str, str]] = []

    def _fake_send_email_with_outbox(**kwargs: str) -> dict[str, str]:
        send_calls.append(kwargs)
        return {"send_key": "unexpected-send", "skipped": False}

    monkeypatch.setattr(tasks, "send_email_with_outbox", _fake_send_email_with_outbox)

    result = tasks.generate_newsletter_task(
        {
            "keywords": ["AI", "robotics"],
            "email": "approval@example.com",
            "require_approval": True,
        },
        job_id="approval-job",
        send_email=True,
        idempotency_key="generate:approval-job",
        database_path=database_path,
    )

    assert send_calls == []
    assert result["approval_required"] is True
    assert result["approval_status"] == "pending"
    assert result["delivery_status"] == "pending_approval"
    assert result["email_sent"] is False

    history_row = get_history_row(database_path, "approval-job")
    assert history_row is not None
    assert history_row["status"] == "completed"
    assert history_row["approval_status"] == "pending"
    assert history_row["delivery_status"] == "pending_approval"


def test_send_email_route_rejects_pending_approval_job(tmp_path: Path) -> None:
    database_path = str(tmp_path / "storage.db")
    app = _build_send_email_app(database_path)
    job_id = "pending-approval-job"
    _insert_history_row(
        database_path,
        job_id=job_id,
        params={"keywords": ["AI"], "email": "approval@example.com"},
        result={"html_content": "<html><body>approval</body></html>"},
        approval_status="pending",
        delivery_status="pending_approval",
    )

    with app.test_client() as client:
        response = client.post(
            "/api/send-email",
            json={"job_id": job_id, "email": "approval@example.com"},
        )

    assert response.status_code == 409
    assert response.get_json() == {"error": "승인 대기 중인 작업입니다"}


def test_send_email_route_marks_approved_job_as_sent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = str(tmp_path / "storage.db")
    app = _build_send_email_app(database_path)
    job_id = "approved-job"

    _insert_history_row(
        database_path,
        job_id=job_id,
        params={"keywords": ["AI"], "email": "approved@example.com"},
        result={
            "html_content": "<html><body>approved</body></html>",
            "title": "Approved",
        },
        approval_status="approved",
        delivery_status="approved",
    )

    monkeypatch.setattr(
        routes_send_email,
        "send_email_with_outbox",
        lambda **kwargs: {"send_key": "approved-send-key", "skipped": False},
    )
    monkeypatch.setattr(
        routes_send_email,
        "get_newsletter_subject",
        lambda result, params: "Approved Subject",
    )

    with app.test_client() as client:
        response = client.post(
            "/api/send-email",
            json={"job_id": job_id, "email": "approved@example.com"},
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["deduplicated"] is False

    history_row = get_history_row(database_path, job_id)
    assert history_row is not None
    assert history_row["delivery_status"] == "sent"
