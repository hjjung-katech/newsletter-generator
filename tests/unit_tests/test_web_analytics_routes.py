from __future__ import annotations

import sys
from pathlib import Path

import pytest
from flask import Flask

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from db_state import ensure_database_schema, record_analytics_event  # noqa: E402
from routes_analytics import register_analytics_routes  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def _build_app(database_path: str) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_analytics_routes(app, database_path)
    return app


def test_analytics_route_returns_summary_and_recent_events(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))
    record_analytics_event(
        str(db_path),
        "generation.completed",
        job_id="job-1",
        status="success",
        duration_seconds=3.25,
        cost_usd=0.75,
        payload={"source": "unit-test"},
    )
    record_analytics_event(
        str(db_path),
        "email.sent",
        job_id="job-1",
        status="sent",
        payload={"recipient": "ops@example.com"},
    )
    record_analytics_event(
        str(db_path),
        "schedule.execute.completed",
        schedule_id="schedule-1",
        job_id="job-1",
        status="success",
        payload={"source": "schedule_runner"},
    )

    app = _build_app(str(db_path))
    with app.test_client() as client:
        response = client.get("/api/analytics?window_days=14&recent_limit=10")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert payload["window_days"] == 14
    assert payload["summary"]["generation"]["completed"] == 1
    assert payload["summary"]["email"]["sent"] == 1
    assert payload["summary"]["schedule"]["completed"] == 1
    assert len(payload["recent_events"]) == 3


def test_analytics_route_clamps_invalid_window_and_limit(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    app = _build_app(str(db_path))
    with app.test_client() as client:
        response = client.get("/api/analytics?window_days=0&recent_limit=999")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert payload["window_days"] == 1
    assert payload["recent_events"] == []
