from __future__ import annotations

import json
import sys
from pathlib import Path

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


def test_schedule_routes_create_and_list(tmp_path: Path) -> None:
    app = _build_generation_app(str(tmp_path / "storage.db"))

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

        assert create_response.status_code == 201
        created_payload = create_response.get_json()
        assert created_payload is not None
        schedule_id = created_payload["schedule_id"]

        list_response = client.get("/api/schedules")
        assert list_response.status_code == 200
        schedules = list_response.get_json()

    assert isinstance(schedules, list)
    assert any(schedule["id"] == schedule_id for schedule in schedules)
