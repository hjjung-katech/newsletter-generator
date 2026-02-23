"""Shared DB schema, idempotency, and state-transition helpers for web runtime."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple


def is_feature_enabled(env_var: str, default: bool = True) -> bool:
    """Read a boolean feature flag from environment variables."""
    raw = os.getenv(env_var)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def canonical_json(payload: Dict[str, Any] | None) -> str:
    """Serialize payload into a deterministic JSON string."""
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
        f"{namespace}:{canonical_json(payload)}".encode("utf-8")
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


def _ensure_column(
    cursor: sqlite3.Cursor, table_name: str, column_name: str, column_def: str
) -> None:
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if column_name not in existing_columns:
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
        )


def _ensure_database_schema(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id TEXT PRIMARY KEY,
            params JSON NOT NULL,
            result JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
        """
    )
    _ensure_column(cursor, "history", "params", "JSON")
    _ensure_column(cursor, "history", "result", "JSON")
    _ensure_column(cursor, "history", "status", "TEXT DEFAULT 'pending'")
    _ensure_column(
        cursor, "history", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    )
    _ensure_column(cursor, "history", "idempotency_key", "TEXT")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schedules (
            id TEXT PRIMARY KEY,
            params JSON NOT NULL,
            rrule TEXT NOT NULL,
            next_run TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            enabled INTEGER DEFAULT 1
        )
        """
    )
    _ensure_column(cursor, "schedules", "is_test", "INTEGER DEFAULT 0")
    _ensure_column(cursor, "schedules", "expires_at", "TEXT")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS email_outbox (
            send_key TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            recipient TEXT NOT NULL,
            subject_hash TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            attempt_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            provider_message_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_history_created_at ON history(created_at)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_status ON history(status)")
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_history_idempotency_key ON history(idempotency_key) WHERE idempotency_key IS NOT NULL"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_schedules_next_run ON schedules(next_run)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_schedules_enabled ON schedules(enabled)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_email_outbox_status ON email_outbox(status)"
    )

    conn.commit()


def ensure_database_schema(db_path: str) -> None:
    """Run additive DB migrations and ensure runtime schema is complete."""
    conn = sqlite3.connect(db_path)
    try:
        _ensure_database_schema(conn)
    finally:
        conn.close()


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    _ensure_database_schema(conn)
    return conn


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
            INSERT OR IGNORE INTO history (id, params, status, idempotency_key)
            VALUES (?, ?, ?, ?)
            """,
            (job_id, canonical_json(params), status, idempotency_key),
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
        cursor.execute(
            """
            INSERT OR IGNORE INTO history (id, params, status, idempotency_key)
            VALUES (?, ?, ?, ?)
            """,
            (job_id, canonical_json(params), status, idempotency_key),
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
                (status, canonical_json(result), job_id),
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
            "SELECT id, status, result, params FROM history WHERE idempotency_key = ?",
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
        }
    finally:
        conn.close()


def get_history_row(db_path: str, job_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a history row by job id."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, status, result, params, idempotency_key FROM history WHERE id = ?",
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
        }
    finally:
        conn.close()


def hash_subject(subject: str) -> str:
    """Hash email subject for stable outbox keys."""
    return hashlib.sha256(subject.encode("utf-8")).hexdigest()


def get_or_create_outbox_record(
    db_path: str,
    send_key: str,
    job_id: str,
    recipient: str,
    subject_hash: str,
) -> str:
    """Get outbox status or create pending record."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status FROM email_outbox WHERE send_key = ?", (send_key,)
        )
        existing = cursor.fetchone()
        if existing:
            return str(existing[0])

        cursor.execute(
            """
            INSERT INTO email_outbox (send_key, job_id, recipient, subject_hash, status)
            VALUES (?, ?, ?, ?, 'pending')
            """,
            (send_key, job_id, recipient, subject_hash),
        )
        conn.commit()
        return "pending"
    finally:
        conn.close()


def mark_outbox_sent(
    db_path: str, send_key: str, provider_message_id: str | None = None
) -> None:
    """Mark outbox record as sent."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE email_outbox
            SET status = 'sent',
                attempt_count = attempt_count + 1,
                last_error = NULL,
                provider_message_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE send_key = ?
            """,
            (provider_message_id, send_key),
        )
        conn.commit()
    finally:
        conn.close()


def mark_outbox_failed(db_path: str, send_key: str, error_message: str) -> None:
    """Mark outbox record as failed with error message."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE email_outbox
            SET status = 'failed',
                attempt_count = attempt_count + 1,
                last_error = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE send_key = ?
            """,
            (error_message, send_key),
        )
        conn.commit()
    finally:
        conn.close()
