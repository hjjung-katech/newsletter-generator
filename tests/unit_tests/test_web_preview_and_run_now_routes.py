from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
from flask import Flask

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

import routes_generation  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def _build_generation_app(database_path: str) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    routes_generation.register_generation_routes(
        app=app,
        database_path=database_path,
        newsletter_cli=object(),
        in_memory_tasks={},
        task_queue=None,
        redis_conn=None,
    )
    return app


def test_generate_route_accepts_preview_only_field(tmp_path: Path) -> None:
    app = _build_generation_app(str(tmp_path / "storage.db"))

    with app.test_client() as client:
        response = client.post(
            "/api/generate",
            data=json.dumps(
                {
                    "keywords": ["AI", "robotics"],
                    "preview_only": True,
                }
            ),
            content_type="application/json",
        )

    assert response.status_code == 202
    payload = response.get_json()
    assert payload is not None
    assert payload["status"] == "processing"
    assert payload["deduplicated"] is False


def test_schedule_run_now_executes_scheduled_job(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = str(tmp_path / "storage.db")
    app = _build_generation_app(database_path)

    observed: dict[str, Any] = {}

    def fake_generate_newsletter_task(
        data: dict[str, Any],
        job_id: str,
        send_email: bool = False,
        idempotency_key: str | None = None,
        database_path: str | None = None,
    ) -> dict[str, Any]:
        observed["data"] = data
        observed["job_id"] = job_id
        observed["send_email"] = send_email
        observed["idempotency_key"] = idempotency_key
        observed["database_path"] = database_path
        return {
            "status": "success",
            "html_content": "<html><body>ok</body></html>",
            "title": "Scheduled Newsletter",
            "generation_stats": {},
            "input_params": data,
            "error": None,
            "sent": False,
            "email_sent": False,
        }

    monkeypatch.setattr(
        routes_generation, "generate_newsletter_task", fake_generate_newsletter_task
    )

    with app.test_client() as client:
        create_response = client.post(
            "/api/schedule",
            data=json.dumps(
                {
                    "keywords": ["AI", "robotics"],
                    "email": "test@example.com",
                    "rrule": "FREQ=WEEKLY;BYDAY=MO,WE;BYHOUR=9;BYMINUTE=0",
                }
            ),
            content_type="application/json",
        )
        created_payload = create_response.get_json()
        assert create_response.status_code == 201
        assert created_payload is not None

        schedule_id = created_payload["schedule_id"]
        run_response = client.post(f"/api/schedule/{schedule_id}/run")

    assert run_response.status_code == 200
    run_payload = run_response.get_json()
    assert run_payload is not None
    assert run_payload["status"] == "completed"
    assert run_payload["job_id"].startswith(f"schedule_{schedule_id}_")
    assert run_payload["result"]["title"] == "Scheduled Newsletter"
    assert observed["send_email"] is True
    assert observed["database_path"] == database_path
    assert observed["data"]["email"] == "test@example.com"
