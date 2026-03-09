from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from db_analytics import (  # noqa: E402
    get_analytics_dashboard_data,
    list_analytics_events,
    record_analytics_event,
)
from db_state import ensure_database_schema  # noqa: E402


def test_get_analytics_dashboard_data_summarizes_recent_events(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    record_analytics_event(
        str(db_path),
        "generation.completed",
        job_id="job-1",
        status="success",
        duration_seconds=4.25,
        cost_usd=1.5,
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
        job_id="job-1",
        schedule_id="schedule-1",
        status="success",
        payload={"source": "schedule_runner"},
    )

    payload = get_analytics_dashboard_data(str(db_path), window_days=7, recent_limit=10)

    assert payload["summary"]["generation"]["completed"] == 1
    assert payload["summary"]["generation"]["average_duration_seconds"] == 4.25
    assert payload["summary"]["generation"]["total_cost_usd"] == 1.5
    assert payload["summary"]["email"]["sent"] == 1
    assert payload["summary"]["schedule"]["completed"] == 1
    assert len(payload["recent_events"]) == 3


def test_list_analytics_events_filters_prefix_and_since(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))
    old_timestamp = datetime.now(timezone.utc) - timedelta(days=10)
    recent_timestamp = datetime.now(timezone.utc) - timedelta(hours=1)

    record_analytics_event(
        str(db_path),
        "generation.completed",
        job_id="job-old",
        occurred_at=old_timestamp,
    )
    record_analytics_event(
        str(db_path),
        "generation.failed",
        job_id="job-new",
        occurred_at=recent_timestamp,
    )
    record_analytics_event(
        str(db_path),
        "email.sent",
        job_id="job-email",
        occurred_at=recent_timestamp,
    )

    events = list_analytics_events(
        str(db_path),
        limit=10,
        event_type_prefix="generation.",
        created_since=(datetime.now(timezone.utc) - timedelta(days=1))
        .isoformat()
        .replace("+00:00", "Z"),
    )

    assert [event["event_type"] for event in events] == ["generation.failed"]
