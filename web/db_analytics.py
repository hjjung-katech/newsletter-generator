"""Analytics event persistence helpers for the canonical web runtime."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, cast

try:
    import db_core as _db_core
except ImportError:
    from web import db_core as _db_core  # pragma: no cover


def _connect(db_path: str) -> sqlite3.Connection:
    return cast(sqlite3.Connection, _db_core.connect_db(db_path))


def _canonical_json(payload: Dict[str, Any] | None) -> str:
    return json.dumps(
        payload or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _serialize_timestamp(value: str | datetime | None) -> str:
    if value is None:
        timestamp = datetime.now(timezone.utc)
    elif isinstance(value, str):
        return value
    elif value.tzinfo is None:
        timestamp = value.replace(tzinfo=timezone.utc)
    else:
        timestamp = value.astimezone(timezone.utc)

    return timestamp.isoformat().replace("+00:00", "Z")


def record_analytics_event(
    db_path: str,
    event_type: str,
    *,
    job_id: str | None = None,
    schedule_id: str | None = None,
    status: str | None = None,
    deduplicated: bool = False,
    duration_seconds: float | None = None,
    cost_usd: float | None = None,
    payload: Dict[str, Any] | None = None,
    occurred_at: str | datetime | None = None,
) -> str:
    """Persist a structured analytics event for later aggregation."""
    event_id = f"evt_{uuid.uuid4().hex}"
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO analytics_events (
                id,
                event_type,
                job_id,
                schedule_id,
                status,
                deduplicated,
                duration_seconds,
                cost_usd,
                payload,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                event_type,
                job_id,
                schedule_id,
                status,
                int(deduplicated),
                duration_seconds,
                cost_usd,
                None if payload is None else _canonical_json(payload),
                _serialize_timestamp(occurred_at),
            ),
        )
        conn.commit()
        return event_id
    finally:
        conn.close()


def list_analytics_events(
    db_path: str,
    *,
    limit: int = 100,
    event_type_prefix: str | None = None,
    created_since: str | None = None,
) -> list[Dict[str, Any]]:
    """Return recent analytics events for tests and dashboard routes."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        if event_type_prefix and created_since:
            cursor.execute(
                """
                SELECT
                    id,
                    event_type,
                    job_id,
                    schedule_id,
                    status,
                    deduplicated,
                    duration_seconds,
                    cost_usd,
                    payload,
                    created_at
                FROM analytics_events
                WHERE event_type LIKE ? AND created_at >= ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (f"{event_type_prefix}%", created_since, limit),
            )
        elif event_type_prefix:
            cursor.execute(
                """
                SELECT
                    id,
                    event_type,
                    job_id,
                    schedule_id,
                    status,
                    deduplicated,
                    duration_seconds,
                    cost_usd,
                    payload,
                    created_at
                FROM analytics_events
                WHERE event_type LIKE ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (f"{event_type_prefix}%", limit),
            )
        elif created_since:
            cursor.execute(
                """
                SELECT
                    id,
                    event_type,
                    job_id,
                    schedule_id,
                    status,
                    deduplicated,
                    duration_seconds,
                    cost_usd,
                    payload,
                    created_at
                FROM analytics_events
                WHERE created_at >= ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (created_since, limit),
            )
        else:
            cursor.execute(
                """
                SELECT
                    id,
                    event_type,
                    job_id,
                    schedule_id,
                    status,
                    deduplicated,
                    duration_seconds,
                    cost_usd,
                    payload,
                    created_at
                FROM analytics_events
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            )
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "event_type": row[1],
                "job_id": row[2],
                "schedule_id": row[3],
                "status": row[4],
                "deduplicated": bool(row[5]),
                "duration_seconds": row[6],
                "cost_usd": row[7],
                "payload": json.loads(row[8]) if row[8] else None,
                "created_at": row[9],
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_analytics_dashboard_data(
    db_path: str,
    *,
    window_days: int = 7,
    recent_limit: int = 25,
) -> Dict[str, Any]:
    """Return aggregated analytics metrics and recent events for the dashboard."""
    since = (
        (datetime.now(timezone.utc) - timedelta(days=max(1, int(window_days))))
        .isoformat()
        .replace("+00:00", "Z")
    )
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                SUM(CASE WHEN event_type = 'generation.started' THEN 1 ELSE 0 END),
                SUM(CASE WHEN event_type = 'generation.completed' THEN 1 ELSE 0 END),
                SUM(CASE WHEN event_type = 'generation.failed' THEN 1 ELSE 0 END),
                AVG(CASE WHEN event_type = 'generation.completed' THEN duration_seconds END),
                SUM(CASE WHEN event_type = 'generation.completed' THEN COALESCE(cost_usd, 0) ELSE 0 END)
            FROM analytics_events
            WHERE created_at >= ?
            """,
            (since,),
        )
        generation_row = cursor.fetchone() or (0, 0, 0, None, 0.0)

        cursor.execute(
            """
            SELECT
                SUM(CASE WHEN event_type = 'email.sent' THEN 1 ELSE 0 END),
                SUM(CASE WHEN event_type = 'email.deduplicated' THEN 1 ELSE 0 END),
                SUM(CASE WHEN event_type = 'email.failed' THEN 1 ELSE 0 END)
            FROM analytics_events
            WHERE created_at >= ?
            """,
            (since,),
        )
        email_row = cursor.fetchone() or (0, 0, 0)

        cursor.execute(
            """
            SELECT
                SUM(CASE WHEN event_type = 'schedule.created' THEN 1 ELSE 0 END),
                SUM(CASE WHEN event_type IN ('schedule.execute.enqueued', 'schedule.run_now.queued') THEN 1 ELSE 0 END),
                SUM(CASE WHEN event_type IN ('schedule.execute.completed', 'schedule.run_now.completed') THEN 1 ELSE 0 END),
                SUM(CASE WHEN event_type IN ('schedule.execute.failed', 'schedule.run_now.failed') THEN 1 ELSE 0 END)
            FROM analytics_events
            WHERE created_at >= ?
            """,
            (since,),
        )
        schedule_row = cursor.fetchone() or (0, 0, 0, 0)
    finally:
        conn.close()

    generation_started = int(generation_row[0] or 0)
    generation_completed = int(generation_row[1] or 0)
    generation_failed = int(generation_row[2] or 0)
    success_base = generation_completed + generation_failed
    success_rate = (
        round((generation_completed / success_base) * 100, 1) if success_base else None
    )

    return {
        "window_days": max(1, int(window_days)),
        "summary": {
            "generation": {
                "started": generation_started,
                "completed": generation_completed,
                "failed": generation_failed,
                "success_rate": success_rate,
                "average_duration_seconds": (
                    round(float(generation_row[3]), 2)
                    if generation_row[3] is not None
                    else None
                ),
                "total_cost_usd": round(float(generation_row[4] or 0.0), 4),
            },
            "email": {
                "sent": int(email_row[0] or 0),
                "deduplicated": int(email_row[1] or 0),
                "failed": int(email_row[2] or 0),
            },
            "schedule": {
                "created": int(schedule_row[0] or 0),
                "queued": int(schedule_row[1] or 0),
                "completed": int(schedule_row[2] or 0),
                "failed": int(schedule_row[3] or 0),
            },
        },
        "recent_events": list_analytics_events(
            db_path,
            limit=max(1, int(recent_limit)),
            created_since=since,
        ),
    }
