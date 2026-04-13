"""Schedule drift detection for operational visibility.

A schedule is considered "drifted" when its ``next_run`` is older than now by
more than a configurable threshold. This typically means the scheduler was
down, stuck, or overloaded and has not advanced the schedule row yet.

This module is a pure data/helper layer. It is consumed by:
- ``web.routes_health`` to surface a top-level drift indicator on /health
- ``web.routes_ops_schedule_drift`` to expose a drill-down endpoint

It never mutates rows — diagnosis only. Rescheduling is done by
``web.schedule_scan``.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

_DEFAULT_DRIFT_THRESHOLD_SECONDS = 15 * 60  # 15 minutes
_DRIFT_ENV_VAR = "SCHEDULE_DRIFT_THRESHOLD_SECONDS"


@dataclass
class DriftedSchedule:
    """A single drifted schedule row."""

    schedule_id: str
    next_run: str
    drift_seconds: float
    rrule: str
    enabled: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "next_run": self.next_run,
            "drift_seconds": round(self.drift_seconds, 1),
            "drift_minutes": round(self.drift_seconds / 60, 1),
            "rrule": self.rrule,
            "enabled": self.enabled,
        }


@dataclass
class DriftReport:
    """Aggregated drift detection result."""

    checked_at: str
    threshold_seconds: int
    active_schedule_count: int
    drifted: list[DriftedSchedule] = field(default_factory=list)

    @property
    def status(self) -> str:
        if not self.drifted:
            return "healthy"
        worst = max(item.drift_seconds for item in self.drifted)
        if worst >= self.threshold_seconds * 4:
            return "error"
        return "degraded"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checked_at": self.checked_at,
            "threshold_seconds": self.threshold_seconds,
            "active_schedule_count": self.active_schedule_count,
            "drifted_count": len(self.drifted),
            "drifted": [item.to_dict() for item in self.drifted],
        }


def resolve_drift_threshold_seconds(
    explicit: int | None = None,
    environ: dict[str, str] | os._Environ[str] | None = None,
) -> int:
    """Resolve the drift threshold from an explicit value or env var."""
    if explicit is not None:
        return max(1, int(explicit))

    env = environ if environ is not None else os.environ
    raw = env.get(_DRIFT_ENV_VAR)
    if raw is None:
        return _DEFAULT_DRIFT_THRESHOLD_SECONDS
    try:
        parsed = int(str(raw).strip())
    except (TypeError, ValueError):
        return _DEFAULT_DRIFT_THRESHOLD_SECONDS
    return max(1, parsed)


def _parse_next_run(value: str) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def detect_schedule_drift(
    database_path: str,
    *,
    now: datetime | None = None,
    threshold_seconds: int | None = None,
) -> DriftReport:
    """Return a drift report for currently-enabled schedules."""
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    resolved_threshold = resolve_drift_threshold_seconds(threshold_seconds)
    threshold_delta = timedelta(seconds=resolved_threshold)

    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, next_run, rrule, enabled
            FROM schedules
            WHERE enabled = 1
            """
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    drifted: list[DriftedSchedule] = []
    for row in rows:
        schedule_id = str(row[0])
        next_run_raw = str(row[1]) if row[1] is not None else ""
        rrule = str(row[2]) if row[2] is not None else ""
        enabled_flag = bool(int(row[3])) if row[3] is not None else False

        parsed = _parse_next_run(next_run_raw)
        if parsed is None:
            continue

        drift = current_time - parsed
        if drift > threshold_delta:
            drifted.append(
                DriftedSchedule(
                    schedule_id=schedule_id,
                    next_run=next_run_raw,
                    drift_seconds=drift.total_seconds(),
                    rrule=rrule,
                    enabled=enabled_flag,
                )
            )

    drifted.sort(key=lambda item: item.drift_seconds, reverse=True)

    return DriftReport(
        checked_at=current_time.isoformat().replace("+00:00", "Z"),
        threshold_seconds=resolved_threshold,
        active_schedule_count=len(rows),
        drifted=drifted,
    )
