"""Unit tests for the schedule drift detector module and ops route."""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from flask import Flask

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from db_state import ensure_database_schema  # noqa: E402
from routes_ops_schedule_drift import register_schedule_drift_routes  # noqa: E402
from schedule_drift import (  # noqa: E402
    DriftedSchedule,
    DriftReport,
    detect_schedule_drift,
    resolve_drift_threshold_seconds,
)

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def _insert_schedule(
    database_path: str,
    *,
    schedule_id: str,
    next_run: str,
    enabled: int = 1,
    rrule: str = "FREQ=DAILY;BYHOUR=8",
    params: dict[str, object] | None = None,
) -> None:
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO schedules (id, params, rrule, next_run, enabled)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                schedule_id,
                json.dumps(params or {}),
                rrule,
                next_run,
                enabled,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def test_resolve_drift_threshold_defaults_and_overrides() -> None:
    assert resolve_drift_threshold_seconds() == 15 * 60
    assert resolve_drift_threshold_seconds(explicit=30) == 30
    assert resolve_drift_threshold_seconds(explicit=-5) == 1
    assert (
        resolve_drift_threshold_seconds(
            environ={"SCHEDULE_DRIFT_THRESHOLD_SECONDS": "120"},
        )
        == 120
    )
    assert (
        resolve_drift_threshold_seconds(
            environ={"SCHEDULE_DRIFT_THRESHOLD_SECONDS": "not-a-number"},
        )
        == 15 * 60
    )


def test_drift_report_status_levels() -> None:
    # Healthy when nothing drifted
    report = DriftReport(
        checked_at="2026-01-01T00:00:00Z",
        threshold_seconds=60,
        active_schedule_count=1,
        drifted=[],
    )
    assert report.status == "healthy"

    degraded = DriftReport(
        checked_at="2026-01-01T00:00:00Z",
        threshold_seconds=60,
        active_schedule_count=1,
        drifted=[
            DriftedSchedule(
                schedule_id="sched-1",
                next_run="2026-01-01T00:00:00Z",
                drift_seconds=120.0,
                rrule="FREQ=DAILY",
                enabled=True,
            )
        ],
    )
    assert degraded.status == "degraded"

    errored = DriftReport(
        checked_at="2026-01-01T00:00:00Z",
        threshold_seconds=60,
        active_schedule_count=1,
        drifted=[
            DriftedSchedule(
                schedule_id="sched-1",
                next_run="2026-01-01T00:00:00Z",
                drift_seconds=60 * 4 + 1,
                rrule="FREQ=DAILY",
                enabled=True,
            )
        ],
    )
    assert errored.status == "error"


def test_detect_schedule_drift_reports_drifted_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    now = datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc)

    _insert_schedule(
        str(db_path),
        schedule_id="sched-ok",
        next_run=_iso(now + timedelta(minutes=30)),
    )
    _insert_schedule(
        str(db_path),
        schedule_id="sched-drifted",
        next_run=_iso(now - timedelta(hours=1)),
    )
    _insert_schedule(
        str(db_path),
        schedule_id="sched-way-drifted",
        next_run=_iso(now - timedelta(hours=4)),
    )
    _insert_schedule(
        str(db_path),
        schedule_id="sched-disabled",
        next_run=_iso(now - timedelta(days=1)),
        enabled=0,
    )

    report = detect_schedule_drift(
        str(db_path),
        now=now,
        threshold_seconds=15 * 60,
    )
    payload = report.to_dict()

    assert payload["active_schedule_count"] == 3  # disabled excluded
    assert payload["drifted_count"] == 2
    assert payload["threshold_seconds"] == 15 * 60

    drift_ids = [row["schedule_id"] for row in payload["drifted"]]
    # Worst drift should appear first (sorted descending)
    assert drift_ids[0] == "sched-way-drifted"
    assert "sched-drifted" in drift_ids
    assert "sched-ok" not in drift_ids
    assert "sched-disabled" not in drift_ids

    # With a 15-minute threshold, 4h drift is 16x the threshold -> "error"
    assert payload["status"] == "error"


def test_detect_schedule_drift_healthy_when_nothing_late(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    now = datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc)
    _insert_schedule(
        str(db_path),
        schedule_id="sched-future",
        next_run=_iso(now + timedelta(minutes=5)),
    )

    report = detect_schedule_drift(
        str(db_path),
        now=now,
        threshold_seconds=60,
    )
    payload = report.to_dict()

    assert payload["status"] == "healthy"
    assert payload["drifted_count"] == 0
    assert payload["active_schedule_count"] == 1


def test_detect_schedule_drift_ignores_unparseable_next_run(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    now = datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc)
    _insert_schedule(
        str(db_path),
        schedule_id="sched-garbage",
        next_run="not-a-timestamp",
    )

    report = detect_schedule_drift(
        str(db_path),
        now=now,
        threshold_seconds=60,
    )
    payload = report.to_dict()

    assert payload["status"] == "healthy"
    assert payload["drifted_count"] == 0
    # Active count still reflects the row existing in the table
    assert payload["active_schedule_count"] == 1


def _build_app(database_path: str) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_schedule_drift_routes(app, database_path)
    return app


def test_ops_schedule_drift_endpoint_returns_payload(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    past = datetime.now(timezone.utc) - timedelta(hours=2)
    _insert_schedule(
        str(db_path),
        schedule_id="sched-late",
        next_run=_iso(past),
    )

    app = _build_app(str(db_path))
    with app.test_client() as client:
        response = client.get("/api/ops/schedule-drift")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert payload["drifted_count"] == 1
    assert payload["active_schedule_count"] == 1
    assert payload["status"] in {"degraded", "error"}
    assert payload["drifted"][0]["schedule_id"] == "sched-late"


def test_ops_schedule_drift_endpoint_respects_threshold_query(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    _insert_schedule(
        str(db_path),
        schedule_id="sched-small-lag",
        next_run=_iso(past),
    )

    app = _build_app(str(db_path))
    with app.test_client() as client:
        # Large threshold -> should not consider the row drifted
        response = client.get("/api/ops/schedule-drift?threshold_seconds=3600")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert payload["threshold_seconds"] == 3600
    assert payload["drifted_count"] == 0
    assert payload["status"] == "healthy"
