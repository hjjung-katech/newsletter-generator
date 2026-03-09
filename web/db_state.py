"""Shared DB schema, idempotency, and state-transition helpers for web runtime."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from typing import Any, Dict, Optional, cast

try:
    import db_core as _db_core
except ImportError:
    from web import db_core as _db_core  # pragma: no cover

try:
    import db_history as _db_history
except ImportError:
    from web import db_history as _db_history  # pragma: no cover

try:
    import db_archive as _db_archive
except ImportError:
    from web import db_archive as _db_archive  # pragma: no cover

try:
    import db_analytics as _db_analytics
except ImportError:
    from web import db_analytics as _db_analytics  # pragma: no cover

APPROVAL_STATUS_NOT_REQUESTED = _db_history.APPROVAL_STATUS_NOT_REQUESTED
APPROVAL_STATUS_PENDING = _db_history.APPROVAL_STATUS_PENDING
APPROVAL_STATUS_APPROVED = _db_history.APPROVAL_STATUS_APPROVED
APPROVAL_STATUS_REJECTED = _db_history.APPROVAL_STATUS_REJECTED

DELIVERY_STATUS_DRAFT = _db_history.DELIVERY_STATUS_DRAFT
DELIVERY_STATUS_PENDING_APPROVAL = _db_history.DELIVERY_STATUS_PENDING_APPROVAL
DELIVERY_STATUS_APPROVED = _db_history.DELIVERY_STATUS_APPROVED
DELIVERY_STATUS_SENT = _db_history.DELIVERY_STATUS_SENT
DELIVERY_STATUS_SEND_FAILED = _db_history.DELIVERY_STATUS_SEND_FAILED

SOURCE_POLICY_ALLOW = "allow"
SOURCE_POLICY_BLOCK = "block"


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


build_idempotency_key = _db_history.build_idempotency_key
build_schedule_idempotency_key = _db_history.build_schedule_idempotency_key
derive_job_id = _db_history.derive_job_id
derive_history_review_state = _db_history.derive_history_review_state
create_or_get_history_job = _db_history.create_or_get_history_job
ensure_history_row = _db_history.ensure_history_row
update_history_status = _db_history.update_history_status
get_history_row_by_idempotency_key = _db_history.get_history_row_by_idempotency_key
get_history_row = _db_history.get_history_row
update_history_review_state = _db_history.update_history_review_state
sync_archive_entry_from_history = _db_archive.sync_archive_entry_from_history
sync_archive_entries_from_history = _db_archive.sync_archive_entries_from_history
get_archive_entry = _db_archive.get_archive_entry
search_archive_entries = _db_archive.search_archive_entries
record_analytics_event = _db_analytics.record_analytics_event
list_analytics_events = _db_analytics.list_analytics_events
get_analytics_dashboard_data = _db_analytics.get_analytics_dashboard_data


def _connect(db_path: str) -> sqlite3.Connection:
    return cast(sqlite3.Connection, _db_core.connect_db(db_path))


def ensure_database_schema(db_path: str) -> None:
    """Preserve the legacy db_state schema API while delegating to db_core."""
    _db_core.ensure_database_schema(db_path)


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


def list_generation_presets(db_path: str) -> list[Dict[str, Any]]:
    """Return generation presets ordered with defaults first."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, description, params, is_default, created_at, updated_at
            FROM generation_presets
            ORDER BY is_default DESC, updated_at DESC, created_at DESC
            """
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "params": json.loads(row[3]) if row[3] else {},
                "is_default": bool(row[4]),
                "created_at": row[5],
                "updated_at": row[6],
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_generation_preset(db_path: str, preset_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single generation preset."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, description, params, is_default, created_at, updated_at
            FROM generation_presets
            WHERE id = ?
            """,
            (preset_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "params": json.loads(row[3]) if row[3] else {},
            "is_default": bool(row[4]),
            "created_at": row[5],
            "updated_at": row[6],
        }
    finally:
        conn.close()


def create_generation_preset(
    db_path: str,
    preset_id: str,
    name: str,
    description: str | None,
    params: Dict[str, Any],
    *,
    is_default: bool = False,
) -> Dict[str, Any]:
    """Create a generation preset and return the stored row."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        if is_default:
            cursor.execute("UPDATE generation_presets SET is_default = 0")

        cursor.execute(
            """
            INSERT INTO generation_presets (id, name, description, params, is_default)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                preset_id,
                name,
                description,
                canonical_json(params),
                int(is_default),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return get_generation_preset(db_path, preset_id) or {}


def update_generation_preset(
    db_path: str,
    preset_id: str,
    name: str,
    description: str | None,
    params: Dict[str, Any],
    *,
    is_default: bool = False,
) -> Optional[Dict[str, Any]]:
    """Update a generation preset and return the stored row."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM generation_presets WHERE id = ?",
            (preset_id,),
        )
        if not cursor.fetchone():
            return None

        if is_default:
            cursor.execute(
                "UPDATE generation_presets SET is_default = 0 WHERE id != ?",
                (preset_id,),
            )

        cursor.execute(
            """
            UPDATE generation_presets
            SET name = ?,
                description = ?,
                params = ?,
                is_default = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                name,
                description,
                canonical_json(params),
                int(is_default),
                preset_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return get_generation_preset(db_path, preset_id)


def delete_generation_preset(db_path: str, preset_id: str) -> bool:
    """Delete a generation preset."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM generation_presets WHERE id = ?", (preset_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def list_source_policies(db_path: str) -> list[Dict[str, Any]]:
    """Return source policy rows ordered by type and recency."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, pattern, policy_type, is_active, created_at, updated_at
            FROM source_policies
            ORDER BY policy_type ASC, updated_at DESC, created_at DESC
            """
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "pattern": row[1],
                "policy_type": row[2],
                "is_active": bool(row[3]),
                "created_at": row[4],
                "updated_at": row[5],
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_source_policy(db_path: str, policy_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single source policy row."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, pattern, policy_type, is_active, created_at, updated_at
            FROM source_policies
            WHERE id = ?
            """,
            (policy_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "pattern": row[1],
            "policy_type": row[2],
            "is_active": bool(row[3]),
            "created_at": row[4],
            "updated_at": row[5],
        }
    finally:
        conn.close()


def create_source_policy(
    db_path: str,
    policy_id: str,
    pattern: str,
    policy_type: str,
    *,
    is_active: bool = True,
) -> Dict[str, Any]:
    """Create a source policy row and return it."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO source_policies (id, pattern, policy_type, is_active)
            VALUES (?, ?, ?, ?)
            """,
            (policy_id, pattern, policy_type, int(is_active)),
        )
        conn.commit()
    finally:
        conn.close()

    return get_source_policy(db_path, policy_id) or {}


def update_source_policy(
    db_path: str,
    policy_id: str,
    pattern: str,
    policy_type: str,
    *,
    is_active: bool = True,
) -> Optional[Dict[str, Any]]:
    """Update an existing source policy row."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM source_policies WHERE id = ?", (policy_id,))
        if not cursor.fetchone():
            return None

        cursor.execute(
            """
            UPDATE source_policies
            SET pattern = ?,
                policy_type = ?,
                is_active = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (pattern, policy_type, int(is_active), policy_id),
        )
        conn.commit()
    finally:
        conn.close()

    return get_source_policy(db_path, policy_id)


def delete_source_policy(db_path: str, policy_id: str) -> bool:
    """Delete a source policy row."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM source_policies WHERE id = ?", (policy_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_active_source_policies(db_path: str) -> Dict[str, list[str]]:
    """Return active source policy patterns grouped by allow/block type."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT pattern, policy_type
            FROM source_policies
            WHERE is_active = 1
            ORDER BY policy_type ASC, updated_at DESC
            """
        )
        allowlist: list[str] = []
        blocklist: list[str] = []
        for pattern, policy_type in cursor.fetchall():
            if policy_type == SOURCE_POLICY_ALLOW:
                allowlist.append(str(pattern))
            elif policy_type == SOURCE_POLICY_BLOCK:
                blocklist.append(str(pattern))
        return {"allowlist": allowlist, "blocklist": blocklist}
    finally:
        conn.close()
