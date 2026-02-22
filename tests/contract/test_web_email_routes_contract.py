"""Contract tests that pin email/html web route behavior before refactor."""

import json
import sqlite3
import sys
import uuid

import pytest

from web.app import DATABASE_PATH, app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def _insert_history_row(job_id: str, status: str, result: dict, params: dict) -> None:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO history (id, params, result, status) VALUES (?, ?, ?, ?)",
        (
            job_id,
            json.dumps(params),
            json.dumps(result),
            status,
        ),
    )
    conn.commit()
    conn.close()


def _delete_history_row(job_id: str) -> None:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()


def test_newsletter_html_returns_not_found_for_missing_job(client):
    response = client.get("/api/newsletter-html/non-existent-contract-job")

    assert response.status_code == 404
    assert "뉴스레터를 찾을 수 없습니다" in response.get_data(as_text=True)


def test_newsletter_html_returns_pending_message_for_unfinished_job(client):
    job_id = f"contract-pending-{uuid.uuid4()}"
    _insert_history_row(
        job_id=job_id,
        status="pending",
        result={},
        params={"keywords": "AI"},
    )

    try:
        response = client.get(f"/api/newsletter-html/{job_id}")
        assert response.status_code == 400
        assert "완료되지 않았습니다" in response.get_data(as_text=True)
    finally:
        _delete_history_row(job_id)


def test_newsletter_html_returns_rendered_content_for_completed_job(client):
    job_id = f"contract-completed-{uuid.uuid4()}"
    expected_html = "<html><body><h1>contract-html</h1></body></html>"
    _insert_history_row(
        job_id=job_id,
        status="completed",
        result={"html_content": expected_html},
        params={"keywords": "AI"},
    )

    try:
        response = client.get(f"/api/newsletter-html/{job_id}")
        assert response.status_code == 200
        assert response.headers["Content-Type"].startswith("text/html")
        assert "contract-html" in response.get_data(as_text=True)
    finally:
        _delete_history_row(job_id)


def test_send_email_requires_job_id_and_email(client):
    response = client.post(
        "/api/send-email",
        json={"job_id": "missing-email"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "job_id와 email이 필요합니다"}


def test_send_email_returns_not_found_for_missing_job(client):
    response = client.post(
        "/api/send-email",
        json={"job_id": "missing-job", "email": "contract@example.com"},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "작업을 찾을 수 없습니다"}


def test_send_email_sends_completed_newsletter(client, monkeypatch):
    try:
        import mail as mail_module
    except ImportError:
        from web import mail as mail_module

    sent: dict[str, str] = {}

    def _fake_send_email(*, to: str, subject: str, html: str) -> None:
        sent["to"] = to
        sent["subject"] = subject
        sent["html"] = html

    monkeypatch.setitem(sys.modules, "mail", mail_module)
    monkeypatch.setattr(mail_module, "send_email", _fake_send_email)

    job_id = f"contract-send-{uuid.uuid4()}"
    expected_html = "<html><body><h1>contract-send</h1></body></html>"
    _insert_history_row(
        job_id=job_id,
        status="completed",
        result={"html_content": expected_html},
        params={"keywords": ["AI", "ML"]},
    )

    try:
        response = client.post(
            "/api/send-email",
            json={"job_id": job_id, "email": "contract@example.com"},
        )
        payload = response.get_json()

        assert response.status_code == 200
        assert payload == {
            "success": True,
            "message": "이메일이 성공적으로 발송되었습니다",
        }
        assert sent["to"] == "contract@example.com"
        assert sent["subject"] == "Newsletter: AI, ML"
        assert sent["html"] == expected_html
    finally:
        _delete_history_row(job_id)
