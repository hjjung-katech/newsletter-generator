"""History and idempotency store helpers for the web runtime."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, cast

try:
    import db_core as _db_core
except ImportError:
    from web import db_core as _db_core  # pragma: no cover

APPROVAL_STATUS_NOT_REQUESTED = "not_requested"
APPROVAL_STATUS_PENDING = "pending"
APPROVAL_STATUS_APPROVED = "approved"
APPROVAL_STATUS_REJECTED = "rejected"

DELIVERY_STATUS_DRAFT = "draft"
DELIVERY_STATUS_PENDING_APPROVAL = "pending_approval"
DELIVERY_STATUS_APPROVED = "approved"
DELIVERY_STATUS_SENT = "sent"
DELIVERY_STATUS_SEND_FAILED = "send_failed"

_UNSET = object()


def _connect(db_path: str) -> sqlite3.Connection:
    return cast(sqlite3.Connection, _db_core.connect_db(db_path))


def _canonical_json(payload: Dict[str, Any] | None) -> str:
    return json.dumps(
        payload or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def build_idempotency_key(
    payload: Dict[str, Any] | None,
    provided_key: str | None = None,
    namespace: str = "generate",
) -> str:
    """Build an idempotency key using client key first, otherwise canonical hash."""
    if provided_key and str(provided_key).strip():
        return str(provided_key).strip()

    digest = hashlib.sha256(
        f"{namespace}:{_canonical_json(payload)}".encode("utf-8")
    ).hexdigest()
    return f"{namespace}:{digest}"


def build_schedule_idempotency_key(schedule_id: str, intended_run_at: datetime) -> str:
    """Derive deterministic schedule idempotency key from schedule and intended run."""
    intended_utc = intended_run_at.astimezone(timezone.utc).isoformat()
    return build_idempotency_key(
        {"schedule_id": schedule_id, "intended_run_at": intended_utc},
        namespace="schedule",
    )


def derive_job_id(idempotency_key: str, prefix: str = "job") -> str:
    """Build stable job ID from idempotency key."""
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


def derive_history_review_state(
    params: Dict[str, Any] | None,
) -> tuple[str, str]:
    """Derive initial approval and delivery state from request params."""
    payload = params or {}
    has_email = bool(str(payload.get("email", "") or "").strip())
    requires_approval = bool(payload.get("require_approval")) and has_email

    if requires_approval:
        return APPROVAL_STATUS_PENDING, DELIVERY_STATUS_PENDING_APPROVAL

    return APPROVAL_STATUS_NOT_REQUESTED, DELIVERY_STATUS_DRAFT


def create_or_get_history_job(
    db_path: str,
    job_id: str,
    params: Dict[str, Any],
    idempotency_key: str | None,
    status: str = "pending",
) -> Tuple[str, bool, str]:
    """Insert a new history row or return existing one by idempotency key."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        approval_status, delivery_status = derive_history_review_state(params)
        if idempotency_key:
            cursor.execute(
                "SELECT id, status FROM history WHERE idempotency_key = ?",
                (idempotency_key,),
            )
            existing = cursor.fetchone()
            if existing:
                return existing[0], True, existing[1]

        cursor.execute(
            """
            INSERT OR IGNORE INTO history (
                id,
                params,
                status,
                idempotency_key,
                approval_status,
                delivery_status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                _canonical_json(params),
                status,
                idempotency_key,
                approval_status,
                delivery_status,
            ),
        )
        conn.commit()
        return job_id, False, status
    finally:
        conn.close()


def ensure_history_row(
    db_path: str,
    job_id: str,
    params: Dict[str, Any] | None = None,
    status: str = "pending",
    idempotency_key: str | None = None,
) -> None:
    """Ensure history row exists for a job."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        approval_status, delivery_status = derive_history_review_state(params)
        cursor.execute(
            """
            INSERT OR IGNORE INTO history (
                id,
                params,
                status,
                idempotency_key,
                approval_status,
                delivery_status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                _canonical_json(params),
                status,
                idempotency_key,
                approval_status,
                delivery_status,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def update_history_status(
    db_path: str,
    job_id: str,
    status: str,
    result: Dict[str, Any] | None = None,
    params: Dict[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> None:
    """Update history status/result in one consistent path."""
    ensure_history_row(
        db_path=db_path,
        job_id=job_id,
        params=params,
        status="pending",
        idempotency_key=idempotency_key,
    )

    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        if result is None:
            cursor.execute(
                "UPDATE history SET status = ? WHERE id = ?",
                (status, job_id),
            )
        else:
            cursor.execute(
                "UPDATE history SET status = ?, result = ? WHERE id = ?",
                (status, _canonical_json(result), job_id),
            )
        conn.commit()
    finally:
        conn.close()


def get_history_row_by_idempotency_key(
    db_path: str, idempotency_key: str
) -> Optional[Dict[str, Any]]:
    """Fetch a history row by idempotency key."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, status, result, params, approval_status, delivery_status
            FROM history
            WHERE idempotency_key = ?
            """,
            (idempotency_key,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "status": row[1],
            "result": row[2],
            "params": row[3],
            "approval_status": row[4],
            "delivery_status": row[5],
        }
    finally:
        conn.close()


def get_history_row(db_path: str, job_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a history row by job id."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id,
                status,
                result,
                params,
                idempotency_key,
                approval_status,
                delivery_status,
                approved_at,
                rejected_at,
                approval_note
            FROM history
            WHERE id = ?
            """,
            (job_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "status": row[1],
            "result": row[2],
            "params": row[3],
            "idempotency_key": row[4],
            "approval_status": row[5],
            "delivery_status": row[6],
            "approved_at": row[7],
            "rejected_at": row[8],
            "approval_note": row[9],
        }
    finally:
        conn.close()


def update_history_review_state(
    db_path: str,
    job_id: str,
    *,
    approval_status: str | None = None,
    delivery_status: str | None = None,
    approved_at: str | None | object = _UNSET,
    rejected_at: str | None | object = _UNSET,
    approval_note: str | None | object = _UNSET,
) -> None:
    """Update approval and delivery metadata for a history row."""
    if (
        approval_status is None
        and delivery_status is None
        and approved_at is _UNSET
        and rejected_at is _UNSET
        and approval_note is _UNSET
    ):
        return

    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE history
            SET
                approval_status = COALESCE(?, approval_status),
                delivery_status = COALESCE(?, delivery_status),
                approved_at = CASE WHEN ? THEN ? ELSE approved_at END,
                rejected_at = CASE WHEN ? THEN ? ELSE rejected_at END,
                approval_note = CASE WHEN ? THEN ? ELSE approval_note END
            WHERE id = ?
            """,
            (
                approval_status,
                delivery_status,
                approved_at is not _UNSET,
                None if approved_at is _UNSET else approved_at,
                rejected_at is not _UNSET,
                None if rejected_at is _UNSET else rejected_at,
                approval_note is not _UNSET,
                None if approval_note is _UNSET else approval_note,
                job_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()
