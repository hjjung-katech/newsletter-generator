"""Shared DB schema, idempotency, and state-transition helpers for web runtime."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, cast

try:
    from archive import build_archive_entry
except ImportError:
    from web.archive import build_archive_entry  # pragma: no cover

try:
    import db_core as _db_core
except ImportError:
    from web import db_core as _db_core  # pragma: no cover

try:
    import db_history as _db_history
except ImportError:
    from web import db_history as _db_history  # pragma: no cover

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


def _parse_history_json(raw_value: str | None) -> Dict[str, Any]:
    """Best-effort JSON decoding for stored history payloads."""
    if not raw_value:
        return {}
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _serialize_event_timestamp(value: str | datetime | None) -> str:
    """Serialize analytics timestamps in UTC ISO format."""
    if value is None:
        timestamp = datetime.now(timezone.utc)
    elif isinstance(value, str):
        return value
    elif value.tzinfo is None:
        timestamp = value.replace(tzinfo=timezone.utc)
    else:
        timestamp = value.astimezone(timezone.utc)

    return timestamp.isoformat().replace("+00:00", "Z")


def sync_archive_entry_from_history(
    db_path: str, job_id: str
) -> Optional[Dict[str, Any]]:
    """Create or refresh a normalized archive entry from a completed history row."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, params, result, created_at, status
            FROM history
            WHERE id = ?
            """,
            (job_id,),
        )
        row = cursor.fetchone()
        if not row or row[4] != "completed":
            return None

        entry = build_archive_entry(
            job_id=row[0],
            created_at=row[3],
            params=_parse_history_json(row[1]),
            result=_parse_history_json(row[2]),
        )
        if entry is None:
            return None

        cursor.execute(
            """
            INSERT INTO archive_entries (
                job_id,
                title,
                snippet,
                source_kind,
                source_value,
                keywords,
                metadata,
                search_text,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                title = excluded.title,
                snippet = excluded.snippet,
                source_kind = excluded.source_kind,
                source_value = excluded.source_value,
                keywords = excluded.keywords,
                metadata = excluded.metadata,
                search_text = excluded.search_text,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at
            """,
            (
                entry["job_id"],
                entry["title"],
                entry["snippet"],
                entry["source_kind"],
                entry["source_value"],
                canonical_json({"items": entry["keywords"]}),
                canonical_json(entry["metadata"]),
                entry["search_text"],
                entry["created_at"],
                _serialize_event_timestamp(datetime.now(timezone.utc)),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return get_archive_entry(db_path, job_id)


def sync_archive_entries_from_history(db_path: str, *, limit: int = 100) -> int:
    """Backfill recent completed history rows into archive storage."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id
            FROM history
            WHERE status = 'completed'
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (max(1, int(limit)),),
        )
        job_ids = [str(row[0]) for row in cursor.fetchall()]
    finally:
        conn.close()

    synced = 0
    for job_id in job_ids:
        if sync_archive_entry_from_history(db_path, job_id):
            synced += 1
    return synced


def _decode_archive_row(row: tuple[Any, ...]) -> Dict[str, Any]:
    keywords_payload = _parse_history_json(row[5])
    metadata = _parse_history_json(row[6])
    return {
        "job_id": row[0],
        "title": row[1],
        "snippet": row[2],
        "source_kind": row[3],
        "source_value": row[4],
        "keywords": keywords_payload.get("items", []),
        "metadata": metadata,
        "created_at": row[8],
        "updated_at": row[9],
    }


def get_archive_entry(db_path: str, job_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a normalized archive entry with archived history payloads."""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                a.job_id,
                a.title,
                a.snippet,
                a.source_kind,
                a.source_value,
                a.keywords,
                a.metadata,
                a.search_text,
                a.created_at,
                a.updated_at,
                h.params,
                h.result,
                h.status
            FROM archive_entries AS a
            LEFT JOIN history AS h ON h.id = a.job_id
            WHERE a.job_id = ?
            """,
            (job_id,),
        )
        row = cursor.fetchone()
    finally:
        conn.close()

    if row is None:
        synced = sync_archive_entry_from_history(db_path, job_id)
        if synced is None:
            return None
        return get_archive_entry(db_path, job_id)

    archive_entry = _decode_archive_row(row[:10])
    archive_entry["params"] = _parse_history_json(row[10])
    archive_entry["result"] = _parse_history_json(row[11])
    archive_entry["status"] = row[12]
    return archive_entry


def search_archive_entries(
    db_path: str,
    *,
    query: str | None = None,
    limit: int = 20,
) -> list[Dict[str, Any]]:
    """Search archive entries by source, title, and archived newsletter content."""
    normalized_limit = max(1, int(limit))
    sync_archive_entries_from_history(db_path, limit=max(50, normalized_limit * 5))

    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                job_id,
                title,
                snippet,
                source_kind,
                source_value,
                keywords,
                metadata,
                search_text,
                created_at,
                updated_at
            FROM archive_entries
            ORDER BY created_at DESC, job_id DESC
            LIMIT ?
            """,
            (max(50, normalized_limit * 5),),
        )
        rows = cursor.fetchall()
        entries = [_decode_archive_row(row) for row in rows]
        normalized_query = (query or "").strip().lower()
        if not normalized_query:
            return entries[:normalized_limit]

        terms = [term for term in re.split(r"\s+", normalized_query) if term]
        filtered_entries = [
            entry
            for entry, row in zip(entries, rows)
            if all(term in str(row[7]).lower() for term in terms)
        ]
        return filtered_entries[:normalized_limit]
    finally:
        conn.close()


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
                None if payload is None else canonical_json(payload),
                _serialize_event_timestamp(occurred_at),
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
