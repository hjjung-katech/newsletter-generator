"""Unit tests for the outbox dedupe statistics route."""

from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from flask import Flask

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from db_state import ensure_database_schema  # noqa: E402
from routes_ops_dedupe_stats import (  # noqa: E402
    compute_dedupe_stats,
    register_dedupe_stats_routes,
)

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def _insert_analytics_event(
    database_path: str,
    *,
    event_type: str,
    job_id: str | None = None,
    payload: dict[str, object] | None = None,
    created_at: str | None = None,
    deduplicated: int = 0,
) -> None:
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO analytics_events (
                id, event_type, job_id, schedule_id, status,
                deduplicated, duration_seconds, cost_usd, payload, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid.uuid4().hex,
                event_type,
                job_id,
                None,
                None,
                deduplicated,
                None,
                None,
                json.dumps(payload or {}),
                created_at
                or datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _build_app(database_path: str) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_dedupe_stats_routes(app, database_path)
    return app


def test_compute_dedupe_stats_aggregates_events(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    _insert_analytics_event(
        str(db_path),
        event_type="email.sent",
        job_id="job-alpha",
        payload={"recipient": "ops@example.com"},
    )
    _insert_analytics_event(
        str(db_path),
        event_type="email.sent",
        job_id="job-alpha",
        payload={"recipient": "ops@example.com"},
    )
    _insert_analytics_event(
        str(db_path),
        event_type="email.deduplicated",
        job_id="job-alpha",
        payload={"recipient": "ops@example.com"},
        deduplicated=1,
    )
    _insert_analytics_event(
        str(db_path),
        event_type="email.deduplicated",
        job_id="job-alpha",
        payload={"recipient": "ops@example.com"},
        deduplicated=1,
    )
    _insert_analytics_event(
        str(db_path),
        event_type="email.deduplicated",
        job_id="job-beta",
        payload={"recipient": "reports@example.com"},
        deduplicated=1,
    )
    _insert_analytics_event(
        str(db_path),
        event_type="email.failed",
        job_id="job-gamma",
        payload={"recipient": "failing@example.com"},
    )

    result = compute_dedupe_stats(str(db_path))

    totals = result["totals"]
    assert totals["sent"] == 2
    assert totals["deduplicated"] == 3
    assert totals["failed"] == 1
    # Attempts = 2 sent + 3 deduped = 5. 3/5 = 60%.
    assert totals["dedupe_rate_percent"] == 60.0

    recipients = {row["recipient"]: row["count"] for row in result["top_recipients"]}
    assert recipients.get("ops@example.com") == 2
    assert recipients.get("reports@example.com") == 1

    jobs = {row["job_id"]: row["count"] for row in result["top_jobs"]}
    assert jobs.get("job-alpha") == 2
    assert jobs.get("job-beta") == 1


def test_compute_dedupe_stats_empty_state(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    result = compute_dedupe_stats(str(db_path))

    assert result["totals"]["sent"] == 0
    assert result["totals"]["deduplicated"] == 0
    assert result["totals"]["failed"] == 0
    assert result["totals"]["dedupe_rate_percent"] is None
    assert result["top_recipients"] == []
    assert result["top_jobs"] == []
    assert result["recent_events"] == []


def test_compute_dedupe_stats_ignores_events_outside_window(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    old_ts = (
        datetime.now(timezone.utc) - timedelta(days=30)
    ).isoformat().replace("+00:00", "Z")

    _insert_analytics_event(
        str(db_path),
        event_type="email.deduplicated",
        job_id="job-old",
        payload={"recipient": "old@example.com"},
        deduplicated=1,
        created_at=old_ts,
    )
    _insert_analytics_event(
        str(db_path),
        event_type="email.deduplicated",
        job_id="job-new",
        payload={"recipient": "new@example.com"},
        deduplicated=1,
    )

    result = compute_dedupe_stats(str(db_path), window_days=1)

    assert result["window_days"] == 1
    assert result["totals"]["deduplicated"] == 1
    recipients = {row["recipient"] for row in result["top_recipients"]}
    assert "new@example.com" in recipients
    assert "old@example.com" not in recipients


def test_compute_dedupe_stats_handles_malformed_payload(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    # Row with non-dict payload string
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO analytics_events (
                id, event_type, job_id, payload, created_at, deduplicated
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                uuid.uuid4().hex,
                "email.deduplicated",
                "job-broken",
                "not-json",
                datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                1,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    result = compute_dedupe_stats(str(db_path))

    # Event is still counted in totals even if payload is unusable
    assert result["totals"]["deduplicated"] == 1
    # Job-level aggregation still works
    assert any(row["job_id"] == "job-broken" for row in result["top_jobs"])
    # No recipient extracted -> top_recipients stays empty
    assert result["top_recipients"] == []


def test_ops_dedupe_stats_route_returns_payload(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    _insert_analytics_event(
        str(db_path),
        event_type="email.sent",
        job_id="job-a",
        payload={"recipient": "a@example.com"},
    )
    _insert_analytics_event(
        str(db_path),
        event_type="email.deduplicated",
        job_id="job-a",
        payload={"recipient": "a@example.com"},
        deduplicated=1,
    )

    app = _build_app(str(db_path))
    with app.test_client() as client:
        response = client.get("/api/ops/dedupe-stats?window_days=7&top=5")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert payload["window_days"] == 7
    assert payload["totals"]["sent"] == 1
    assert payload["totals"]["deduplicated"] == 1
    assert payload["totals"]["dedupe_rate_percent"] == 50.0
    assert payload["top_recipients"][0]["recipient"] == "a@example.com"


def test_ops_dedupe_stats_clamps_query_arguments(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    app = _build_app(str(db_path))
    with app.test_client() as client:
        response = client.get(
            "/api/ops/dedupe-stats?window_days=9999&top=9999"
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    # Window is clamped to max 90 days
    assert payload["window_days"] == 90
