"""Contract tests that pin email/html web route behavior before refactor."""

import json
import sqlite3
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
