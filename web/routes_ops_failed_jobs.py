"""Operational routes for inspecting failed background jobs and outbox state.

This module adds production-safe visibility endpoints on top of the existing
history / email_outbox tables so operators can see what has failed and why
without opening the database directly. The endpoints are protected via the
standard ``/api/ops`` prefix (see ``web.access_control``).
"""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any, cast

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue

try:
    from db_state import DELIVERY_STATUS_SEND_FAILED
except ImportError:
    from web.db_state import DELIVERY_STATUS_SEND_FAILED  # pragma: no cover

try:
    from ops_logging import log_exception, log_info
except ImportError:
    from web.ops_logging import log_exception, log_info  # pragma: no cover


logger = logging.getLogger("web.routes_ops_failed_jobs")


_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


def _connect(database_path: str) -> sqlite3.Connection:
    return sqlite3.connect(database_path)


def _clamp_limit(raw: int | None) -> int:
    if raw is None:
        return _DEFAULT_LIMIT
    return max(1, min(int(raw), _MAX_LIMIT))


def _parse_json(payload: str | None) -> dict[str, Any] | None:
    if not payload:
        return None
    try:
        parsed = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if isinstance(parsed, dict):
        return cast(dict[str, Any], parsed)
    return None


def _error_summary(result_payload: dict[str, Any] | None) -> str | None:
    if not result_payload:
        return None
    error = result_payload.get("error")
    if isinstance(error, str) and error.strip():
        return error.strip()[:500]
    error_type = result_payload.get("error_type")
    if isinstance(error_type, str) and error_type.strip():
        return error_type.strip()
    return None


def _fetch_failed_history(database_path: str, limit: int) -> list[dict[str, Any]]:
    conn = _connect(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id,
                params,
                result,
                status,
                created_at,
                approval_status,
                delivery_status
            FROM history
            WHERE status = 'failed'
               OR delivery_status = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (DELIVERY_STATUS_SEND_FAILED, limit),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    results: list[dict[str, Any]] = []
    for row in rows:
        params = _parse_json(row[1]) or {}
        result_payload = _parse_json(row[2]) or {}
        results.append(
            {
                "job_id": row[0],
                "status": row[3],
                "created_at": row[4],
                "approval_status": row[5],
                "delivery_status": row[6],
                "keywords": params.get("keywords"),
                "domain": params.get("domain"),
                "error": _error_summary(result_payload),
                "attempts": result_payload.get("attempts"),
            }
        )
    return results


def _fetch_failed_outbox(database_path: str, limit: int) -> list[dict[str, Any]]:
    conn = _connect(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                send_key,
                job_id,
                recipient,
                status,
                attempt_count,
                last_error,
                provider_message_id,
                created_at,
                updated_at
            FROM email_outbox
            WHERE status = 'failed'
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    return [
        {
            "send_key": row[0],
            "job_id": row[1],
            "recipient": row[2],
            "status": row[3],
            "attempt_count": row[4],
            "last_error": (row[5] or "")[:500] if row[5] else None,
            "provider_message_id": row[6],
            "created_at": row[7],
            "updated_at": row[8],
        }
        for row in rows
    ]


def _count_outbox_by_status(database_path: str) -> dict[str, int]:
    conn = _connect(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT status, COUNT(*) FROM email_outbox GROUP BY status")
        rows = cursor.fetchall()
    finally:
        conn.close()
    return {str(row[0]): int(row[1]) for row in rows}


def _reset_outbox_record_for_retry(database_path: str, send_key: str) -> str:
    """Mark an outbox record as pending so the next send attempt will go through.

    Returns one of: ``"retry_queued"``, ``"not_found"``, ``"not_failed"``.
    """
    conn = _connect(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status FROM email_outbox WHERE send_key = ?", (send_key,)
        )
        existing = cursor.fetchone()
        if existing is None:
            return "not_found"
        if str(existing[0]) != "failed":
            return "not_failed"
        cursor.execute(
            """
            UPDATE email_outbox
            SET status = 'pending',
                last_error = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE send_key = ?
            """,
            (send_key,),
        )
        conn.commit()
        return "retry_queued"
    finally:
        conn.close()


def register_failed_jobs_routes(app: Flask, database_path: str) -> None:
    """Register failed-jobs visibility routes on the given Flask app."""

    @app.route("/api/ops/failed-jobs", methods=["GET"])  # type: ignore[untyped-decorator]
    def ops_failed_jobs() -> ResponseReturnValue:
        """Return recent failed generation jobs and failed outbox entries."""
        try:
            limit = _clamp_limit(request.args.get("limit", type=int))
            history = _fetch_failed_history(database_path, limit)
            outbox = _fetch_failed_outbox(database_path, limit)
            outbox_totals = _count_outbox_by_status(database_path)

            payload = {
                "limit": limit,
                "history": history,
                "outbox": outbox,
                "summary": {
                    "failed_history_count": len(history),
                    "failed_outbox_count": outbox_totals.get("failed", 0),
                    "pending_outbox_count": outbox_totals.get("pending", 0),
                    "sent_outbox_count": outbox_totals.get("sent", 0),
                },
            }
            log_info(
                logger,
                "ops.failed_jobs.listed",
                history=len(history),
                outbox=len(outbox),
                limit=limit,
            )
            return jsonify(payload)
        except Exception as exc:
            log_exception(logger, "ops.failed_jobs.list_failed", exc)
            return (
                jsonify({"error": f"Failed jobs listing failed: {exc}"}),
                500,
            )

    @app.route(
        "/api/ops/failed-jobs/outbox/<send_key>/retry",
        methods=["POST"],
    )  # type: ignore[untyped-decorator]
    def ops_retry_outbox(send_key: str) -> ResponseReturnValue:
        """Reset a failed outbox record so the next send attempt will retry."""
        try:
            outcome = _reset_outbox_record_for_retry(database_path, send_key)
        except Exception as exc:
            log_exception(
                logger,
                "ops.failed_jobs.retry_failed",
                exc,
                send_key=send_key,
            )
            return (
                jsonify({"error": f"Outbox retry failed: {exc}"}),
                500,
            )

        if outcome == "not_found":
            return jsonify({"error": "outbox record not found"}), 404
        if outcome == "not_failed":
            return (
                jsonify({"error": "outbox record is not in failed state"}),
                409,
            )

        log_info(
            logger,
            "ops.failed_jobs.retry_queued",
            send_key=send_key,
        )
        return jsonify(
            {
                "send_key": send_key,
                "status": "pending",
                "message": "outbox record reset for retry",
            }
        )
