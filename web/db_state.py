"""Shared DB schema, idempotency, and state-transition helpers for web runtime."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from typing import Any, Dict, cast

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

try:
    import db_presets as _db_presets
except ImportError:
    from web import db_presets as _db_presets  # pragma: no cover

try:
    import db_source_policies as _db_source_policies
except ImportError:
    from web import db_source_policies as _db_source_policies  # pragma: no cover

APPROVAL_STATUS_NOT_REQUESTED = _db_history.APPROVAL_STATUS_NOT_REQUESTED
APPROVAL_STATUS_PENDING = _db_history.APPROVAL_STATUS_PENDING
APPROVAL_STATUS_APPROVED = _db_history.APPROVAL_STATUS_APPROVED
APPROVAL_STATUS_REJECTED = _db_history.APPROVAL_STATUS_REJECTED

DELIVERY_STATUS_DRAFT = _db_history.DELIVERY_STATUS_DRAFT
DELIVERY_STATUS_PENDING_APPROVAL = _db_history.DELIVERY_STATUS_PENDING_APPROVAL
DELIVERY_STATUS_APPROVED = _db_history.DELIVERY_STATUS_APPROVED
DELIVERY_STATUS_SENT = _db_history.DELIVERY_STATUS_SENT
DELIVERY_STATUS_SEND_FAILED = _db_history.DELIVERY_STATUS_SEND_FAILED

SOURCE_POLICY_ALLOW = _db_source_policies.SOURCE_POLICY_ALLOW
SOURCE_POLICY_BLOCK = _db_source_policies.SOURCE_POLICY_BLOCK


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
list_generation_presets = _db_presets.list_generation_presets
get_generation_preset = _db_presets.get_generation_preset
create_generation_preset = _db_presets.create_generation_preset
update_generation_preset = _db_presets.update_generation_preset
delete_generation_preset = _db_presets.delete_generation_preset
list_source_policies = _db_source_policies.list_source_policies
get_source_policy = _db_source_policies.get_source_policy
create_source_policy = _db_source_policies.create_source_policy
update_source_policy = _db_source_policies.update_source_policy
delete_source_policy = _db_source_policies.delete_source_policy
get_active_source_policies = _db_source_policies.get_active_source_policies


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
