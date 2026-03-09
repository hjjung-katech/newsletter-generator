"""Archive storage helpers for the canonical web runtime."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional, cast

try:
    from archive import build_archive_entry
except ImportError:
    from web.archive import build_archive_entry  # pragma: no cover

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


def _parse_history_json(raw_value: str | None) -> Dict[str, Any]:
    if not raw_value:
        return {}
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


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
                _canonical_json({"items": entry["keywords"]}),
                _canonical_json(entry["metadata"]),
                entry["search_text"],
                entry["created_at"],
                _serialize_timestamp(datetime.now(timezone.utc)),
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
