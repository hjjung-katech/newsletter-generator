"""
This file protects the generation route contract.
Do not add feature tests here —
ops-safety regression only.
"""

import json
import sqlite3
import uuid

import pytest

import web.routes_generation as _routes_generation
from web.app import DATABASE_PATH, app

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]

_GENERATE_RESPONSE_KEYS = {"job_id", "deduplicated", "idempotency_key", "status"}
_SCHEDULE_RUN_RESPONSE_KEYS = {"job_id", "status"}


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def _delete_history_row(job_id: str) -> None:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()


def _insert_schedule_row(schedule_id: str, params: dict) -> None:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO schedules
            (id, params, rrule, next_run, created_at, enabled)
        VALUES (?, ?, ?, ?, ?, 1)
        """,
        (
            schedule_id,
            json.dumps(params),
            "FREQ=DAILY;BYHOUR=9;BYMINUTE=0",
            "2099-01-01T09:00:00Z",
            "2026-01-01T08:00:00Z",
        ),
    )
    conn.commit()
    conn.close()


def _delete_schedule_row(schedule_id: str) -> None:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()


def test_generate_first_call_returns_202_accepted(client):
    payload = {
        "keywords": f"contract-generate-first-{uuid.uuid4()}",
        "template_style": "compact",
        "period": 14,
    }

    response = client.post(
        "/api/generate",
        data=json.dumps(payload),
        content_type="application/json",
    )
    result = response.get_json()

    try:
        assert response.status_code == 202
        assert _GENERATE_RESPONSE_KEYS <= set(result)
        assert result["deduplicated"] is False
    finally:
        if result and result.get("job_id"):
            _delete_history_row(result["job_id"])


def test_generate_duplicate_key_returns_202_with_dedup_flag(client):
    unique_key = f"contract-dedup-{uuid.uuid4()}"
    payload = {
        "keywords": "AI, machine learning",
        "template_style": "compact",
        "period": 14,
    }
    headers = {"Idempotency-Key": unique_key}

    first = client.post(
        "/api/generate",
        data=json.dumps(payload),
        content_type="application/json",
        headers=headers,
    )
    second = client.post(
        "/api/generate",
        data=json.dumps(payload),
        content_type="application/json",
        headers=headers,
    )

    first_result = first.get_json()
    second_result = second.get_json()

    try:
        assert first.status_code == 202
        assert second.status_code == 202
        assert _GENERATE_RESPONSE_KEYS <= set(first_result)
        assert _GENERATE_RESPONSE_KEYS <= set(second_result)
        assert first_result["deduplicated"] is False
        assert second_result["deduplicated"] is True
        assert first_result["job_id"] == second_result["job_id"]
    finally:
        if first_result and first_result.get("job_id"):
            _delete_history_row(first_result["job_id"])


def test_generate_missing_required_field_returns_400(client):
    payload = {"template_style": "compact", "period": 14}

    response = client.post(
        "/api/generate",
        data=json.dumps(payload),
        content_type="application/json",
    )
    result = response.get_json()

    assert response.status_code == 400
    assert "error" in result


def test_schedule_run_now_returns_accepted(client, monkeypatch):
    schedule_id = f"contract-sched-{uuid.uuid4()}"
    params = {"keywords": "AI", "template_style": "compact", "period": 14}
    _insert_schedule_row(schedule_id, params)

    monkeypatch.setattr(
        _routes_generation,
        "generate_newsletter_task",
        lambda *args, **kwargs: {"status": "success", "html_content": "<p>ok</p>"},
    )

    try:
        response = client.post(f"/api/schedule/{schedule_id}/run")
        result = response.get_json()

        assert response.status_code == 200
        assert _SCHEDULE_RUN_RESPONSE_KEYS <= set(result)
    finally:
        _delete_schedule_row(schedule_id)
