"""Route registration for outbox dedupe statistics.

Exposes a drill-down view of how often the outbox dedupe layer filtered out
duplicate sends, by time window and recipient.

The raw counter already exists inside ``/api/analytics`` (``summary.email.deduplicated``),
but this endpoint gives operators a direct, filterable view for incident review.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue

try:
    from ops_logging import log_exception, log_info
except ImportError:
    from web.ops_logging import log_exception, log_info  # pragma: no cover


logger = logging.getLogger("web.routes_ops_dedupe_stats")


_DEFAULT_WINDOW_DAYS = 7
_MAX_WINDOW_DAYS = 90
_DEFAULT_TOP_N = 10
_MAX_TOP_N = 50


def _clamp_int(raw: int | None, default: int, maximum: int) -> int:
    if raw is None:
        return default
    return max(1, min(int(raw), maximum))


def _window_start_iso(window_days: int) -> str:
    since = datetime.now(timezone.utc) - timedelta(days=window_days)
    return since.isoformat().replace("+00:00", "Z")


def _extract_recipient(payload_json: str | None) -> str | None:
    if not payload_json:
        return None
    try:
        payload = json.loads(payload_json)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    recipient = payload.get("recipient")
    return recipient if isinstance(recipient, str) and recipient.strip() else None


def compute_dedupe_stats(
    database_path: str,
    *,
    window_days: int = _DEFAULT_WINDOW_DAYS,
    top_recipients: int = _DEFAULT_TOP_N,
) -> dict[str, Any]:
    """Return a structured breakdown of dedupe events inside the window."""
    window_days = _clamp_int(window_days, _DEFAULT_WINDOW_DAYS, _MAX_WINDOW_DAYS)
    top_recipients = _clamp_int(top_recipients, _DEFAULT_TOP_N, _MAX_TOP_N)

    since_iso = _window_start_iso(window_days)

    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                SUM(CASE WHEN event_type = 'email.sent' THEN 1 ELSE 0 END),
                SUM(CASE WHEN event_type = 'email.deduplicated' THEN 1 ELSE 0 END),
                SUM(CASE WHEN event_type = 'email.failed' THEN 1 ELSE 0 END)
            FROM analytics_events
            WHERE created_at >= ?
            """,
            (since_iso,),
        )
        totals_row = cursor.fetchone() or (0, 0, 0)

        cursor.execute(
            """
            SELECT id, job_id, payload, created_at
            FROM analytics_events
            WHERE event_type = 'email.deduplicated' AND created_at >= ?
            ORDER BY created_at DESC
            """,
            (since_iso,),
        )
        dedupe_rows = cursor.fetchall()
    finally:
        conn.close()

    sent_count = int(totals_row[0] or 0)
    deduped_count = int(totals_row[1] or 0)
    failed_count = int(totals_row[2] or 0)
    attempt_base = sent_count + deduped_count
    dedupe_rate = (
        round((deduped_count / attempt_base) * 100, 1) if attempt_base else None
    )

    recipient_counter: dict[str, int] = {}
    job_counter: dict[str, int] = {}
    recent_events: list[dict[str, Any]] = []

    for row in dedupe_rows:
        event_id = row[0]
        job_id = str(row[1]) if row[1] is not None else None
        recipient = _extract_recipient(row[2])
        created_at = row[3]

        if recipient is not None:
            recipient_counter[recipient] = recipient_counter.get(recipient, 0) + 1
        if job_id is not None:
            job_counter[job_id] = job_counter.get(job_id, 0) + 1

        if len(recent_events) < top_recipients:
            recent_events.append(
                {
                    "id": event_id,
                    "job_id": job_id,
                    "recipient": recipient,
                    "created_at": created_at,
                }
            )

    top_recipient_list: list[dict[str, Any]] = [
        {"recipient": recipient, "count": count}
        for recipient, count in sorted(
            recipient_counter.items(), key=lambda pair: pair[1], reverse=True
        )[:top_recipients]
    ]

    top_job_list: list[dict[str, Any]] = [
        {"job_id": job_id, "count": count}
        for job_id, count in sorted(
            job_counter.items(), key=lambda pair: pair[1], reverse=True
        )[:top_recipients]
    ]

    return {
        "window_days": window_days,
        "since": since_iso,
        "totals": {
            "sent": sent_count,
            "deduplicated": deduped_count,
            "failed": failed_count,
            "dedupe_rate_percent": dedupe_rate,
        },
        "top_recipients": top_recipient_list,
        "top_jobs": top_job_list,
        "recent_events": recent_events,
    }


def register_dedupe_stats_routes(app: Flask, database_path: str) -> None:
    """Register the outbox dedupe statistics route on the given Flask app."""

    @app.route("/api/ops/dedupe-stats", methods=["GET"])  # type: ignore[untyped-decorator]
    def ops_dedupe_stats() -> ResponseReturnValue:
        """Return aggregated outbox dedupe statistics for the given window."""
        try:
            window_days = request.args.get("window_days", type=int)
            top = request.args.get("top", type=int)
            payload = compute_dedupe_stats(
                database_path,
                window_days=window_days or _DEFAULT_WINDOW_DAYS,
                top_recipients=top or _DEFAULT_TOP_N,
            )
            log_info(
                logger,
                "ops.dedupe_stats.listed",
                window_days=payload["window_days"],
                deduplicated=payload["totals"]["deduplicated"],
            )
            return jsonify(payload)
        except Exception as exc:
            log_exception(logger, "ops.dedupe_stats.list_failed", exc)
            return (
                jsonify({"error": f"Dedupe stats lookup failed: {exc}"}),
                500,
            )
