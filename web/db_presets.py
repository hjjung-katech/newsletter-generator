"""Generation preset persistence helpers for the canonical web runtime."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, Optional, cast

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


def _decode_generation_preset(row: tuple[Any, ...]) -> Dict[str, Any]:
    return {
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "params": json.loads(row[3]) if row[3] else {},
        "is_default": bool(row[4]),
        "created_at": row[5],
        "updated_at": row[6],
    }


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
        return [_decode_generation_preset(row) for row in rows]
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
        return _decode_generation_preset(row)
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
                _canonical_json(params),
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
                _canonical_json(params),
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
