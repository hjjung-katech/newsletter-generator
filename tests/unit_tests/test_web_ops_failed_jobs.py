"""Unit tests for the failed-jobs operational visibility routes."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import pytest
from flask import Flask

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from db_state import ensure_database_schema  # noqa: E402
from routes_ops_failed_jobs import register_failed_jobs_routes  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def _build_app(database_path: str) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_failed_jobs_routes(app, database_path)
    return app


def _insert_history_row(
    database_path: str,
    *,
    job_id: str,
    status: str,
    delivery_status: str = "draft",
    result: dict[str, object] | None = None,
    params: dict[str, object] | None = None,
) -> None:
    import sqlite3

    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO history (id, params, result, status, delivery_status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                job_id,
                json.dumps(params or {}),
                json.dumps(result or {}),
                status,
                delivery_status,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _insert_outbox_row(
    database_path: str,
    *,
    send_key: str,
    job_id: str,
    recipient: str,
    status: str,
    last_error: str | None = None,
    attempt_count: int = 1,
) -> None:
    import sqlite3

    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO email_outbox (
                send_key, job_id, recipient, subject_hash,
                status, attempt_count, last_error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                send_key,
                job_id,
                recipient,
                "dummy_subject_hash",
                status,
                attempt_count,
                last_error,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def test_failed_jobs_returns_history_and_outbox(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    _insert_history_row(
        str(db_path),
        job_id="job-failed",
        status="failed",
        result={"error": "LLM provider outage", "error_type": "RuntimeError"},
        params={"keywords": ["AI"], "domain": "tech"},
    )
    _insert_history_row(
        str(db_path),
        job_id="job-send-failed",
        status="completed",
        delivery_status="send_failed",
        result={"error": "SMTP refused"},
    )
    _insert_history_row(
        str(db_path),
        job_id="job-ok",
        status="completed",
    )
    _insert_outbox_row(
        str(db_path),
        send_key="sk-failed",
        job_id="job-failed",
        recipient="ops@example.com",
        status="failed",
        last_error="SMTP refused",
    )
    _insert_outbox_row(
        str(db_path),
        send_key="sk-ok",
        job_id="job-ok",
        recipient="ops@example.com",
        status="sent",
    )

    app = _build_app(str(db_path))
    with app.test_client() as client:
        response = client.get("/api/ops/failed-jobs")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None

    history_ids = {row["job_id"] for row in payload["history"]}
    assert "job-failed" in history_ids
    assert "job-send-failed" in history_ids
    assert "job-ok" not in history_ids

    outbox_keys = {row["send_key"] for row in payload["outbox"]}
    assert "sk-failed" in outbox_keys
    assert "sk-ok" not in outbox_keys

    summary = payload["summary"]
    assert summary["failed_history_count"] == 2
    assert summary["failed_outbox_count"] == 1
    assert summary["sent_outbox_count"] == 1


def test_failed_jobs_limit_is_clamped(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    for index in range(5):
        _insert_history_row(
            str(db_path),
            job_id=f"job-{index}",
            status="failed",
            result={"error": f"error-{index}"},
        )

    app = _build_app(str(db_path))
    with app.test_client() as client:
        response = client.get("/api/ops/failed-jobs?limit=2")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert payload["limit"] == 2
    assert len(payload["history"]) == 2


def test_failed_jobs_retry_resets_outbox_to_pending(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    _insert_outbox_row(
        str(db_path),
        send_key="sk-retry",
        job_id="job-retry",
        recipient="ops@example.com",
        status="failed",
        last_error="temporary",
    )

    app = _build_app(str(db_path))
    with app.test_client() as client:
        response = client.post("/api/ops/failed-jobs/outbox/sk-retry/retry")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert payload["status"] == "pending"

    import sqlite3

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status, last_error FROM email_outbox WHERE send_key = ?",
            ("sk-retry",),
        )
        row = cursor.fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row[0] == "pending"
    assert row[1] is None


def test_failed_jobs_retry_404_when_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    app = _build_app(str(db_path))
    with app.test_client() as client:
        response = client.post(
            f"/api/ops/failed-jobs/outbox/{uuid.uuid4().hex}/retry"
        )

    assert response.status_code == 404


def test_failed_jobs_retry_409_when_not_failed(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    _insert_outbox_row(
        str(db_path),
        send_key="sk-already-sent",
        job_id="job-sent",
        recipient="ops@example.com",
        status="sent",
    )

    app = _build_app(str(db_path))
    with app.test_client() as client:
        response = client.post(
            "/api/ops/failed-jobs/outbox/sk-already-sent/retry"
        )

    assert response.status_code == 409
