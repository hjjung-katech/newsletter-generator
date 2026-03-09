"""Source policy persistence helpers for the canonical web runtime."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, Optional, cast

try:
    import db_core as _db_core
except ImportError:
    from web import db_core as _db_core  # pragma: no cover

SOURCE_POLICY_ALLOW = "allow"
SOURCE_POLICY_BLOCK = "block"


def _connect(db_path: str) -> sqlite3.Connection:
    return cast(sqlite3.Connection, _db_core.connect_db(db_path))


def _decode_source_policy(row: tuple[Any, ...]) -> Dict[str, Any]:
    return {
        "id": row[0],
        "pattern": row[1],
        "policy_type": row[2],
        "is_active": bool(row[3]),
        "created_at": row[4],
        "updated_at": row[5],
    }


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
        return [_decode_source_policy(row) for row in rows]
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
        return _decode_source_policy(row)
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
