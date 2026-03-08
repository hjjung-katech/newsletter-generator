from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from flask import Flask

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

import routes_send_email  # noqa: E402
from db_state import ensure_database_schema, list_analytics_events  # noqa: E402
from schedule_runner import ScheduleRunner  # noqa: E402
from tasks import generate_newsletter_task  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def _build_send_email_app(database_path: str) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    routes_send_email.register_send_email_route(app, database_path)
    return app


def test_generate_newsletter_task_records_generation_and_email_events(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    with patch("tasks.generate_newsletter") as generate_mock:
        generate_mock.return_value = {
            "status": "success",
            "html_content": "<html><head><title>Analytics</title></head><body>ok</body></html>",
            "title": "Analytics",
            "generation_stats": {
                "total_time": 4.5,
                "cost_summary": {"total_cost_usd": 1.75},
            },
            "input_params": {"keywords": ["AI"]},
            "error": None,
        }
        with patch("tasks.send_email_with_outbox") as send_mock:
            send_mock.return_value = {"send_key": "send-1", "skipped": False}

            result = generate_newsletter_task(
                {"keywords": ["AI"], "email": "ops@example.com"},
                "job-analytics",
                send_email=True,
                database_path=str(db_path),
            )

    assert result["status"] == "success"
    events = list_analytics_events(str(db_path), limit=10)
    event_types = {event["event_type"] for event in events}
    assert "generation.started" in event_types
    assert "generation.completed" in event_types
    assert "email.sent" in event_types

    completed = next(
        event for event in events if event["event_type"] == "generation.completed"
    )
    assert completed["duration_seconds"] == pytest.approx(4.5)
    assert completed["cost_usd"] == pytest.approx(1.75)


def test_send_email_route_records_deduplicated_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO history (id, params, result, status, approval_status, delivery_status)
        VALUES (?, ?, ?, 'completed', 'approved', 'approved')
        """,
        (
            "job-send-route",
            json.dumps({"email": "ops@example.com"}),
            json.dumps({"html_content": "<html>ok</html>", "title": "Route Analytics"}),
        ),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(
        routes_send_email,
        "send_email_with_outbox",
        lambda **_: {"send_key": "send-dup", "skipped": True},
    )

    app = _build_send_email_app(str(db_path))
    with app.test_client() as client:
        response = client.post(
            "/api/send-email",
            data=json.dumps({"job_id": "job-send-route", "email": "ops@example.com"}),
            content_type="application/json",
        )

    assert response.status_code == 200
    events = list_analytics_events(str(db_path), limit=10)
    deduplicated = next(
        event for event in events if event["event_type"] == "email.deduplicated"
    )
    assert deduplicated["job_id"] == "job-send-route"
    assert deduplicated["deduplicated"] is True


def test_schedule_runner_records_execution_events(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    schedule_id = "schedule-analytics"
    next_run = datetime.now(timezone.utc).replace(microsecond=0)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO schedules (id, params, rrule, next_run, enabled)
        VALUES (?, ?, ?, ?, 1)
        """,
        (
            schedule_id,
            json.dumps({"keywords": ["AI"], "send_email": False}),
            "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
            next_run.isoformat().replace("+00:00", "Z"),
        ),
    )
    conn.commit()
    conn.close()

    runner = ScheduleRunner(db_path=str(db_path), redis_url="redis://localhost:6379/0")
    runner.redis_conn = None
    runner.queue = None

    with patch("schedule_runner.generate_newsletter_task") as generate_mock:
        generate_mock.return_value = {
            "status": "success",
            "html_content": "<html><body>ok</body></html>",
            "title": "Scheduled Analytics",
            "generation_stats": {},
            "input_params": {},
            "error": None,
            "sent": False,
            "email_sent": False,
        }
        success = runner.execute_schedule(
            {
                "id": schedule_id,
                "params": {"keywords": ["AI"], "send_email": False},
                "rrule": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
                "next_run": next_run,
                "created_at": next_run,
                "is_test": False,
            }
        )

    assert success is True
    events = list_analytics_events(
        str(db_path),
        limit=10,
        event_type_prefix="schedule.execute",
    )
    event_types = {event["event_type"] for event in events}
    assert "schedule.execute.started" in event_types
    assert "schedule.execute.completed" in event_types
