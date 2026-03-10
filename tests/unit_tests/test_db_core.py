from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from db_core import connect_db, ensure_database_schema  # noqa: E402


def _table_columns(db_path: Path, table_name: str) -> set[str]:
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return {row[1] for row in cursor.fetchall()}
    finally:
        conn.close()


def test_ensure_database_schema_creates_runtime_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"

    ensure_database_schema(str(db_path))

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
    finally:
        conn.close()

    assert {
        "history",
        "schedules",
        "email_outbox",
        "generation_presets",
        "source_policies",
        "analytics_events",
        "archive_entries",
    }.issubset(tables)


def test_ensure_database_schema_creates_missing_parent_directories(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / ".local" / "state" / "web" / "storage.db"

    ensure_database_schema(str(db_path))

    assert db_path.parent.is_dir()
    assert db_path.is_file()


def test_connect_db_applies_additive_history_and_schedule_columns(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE history (
                id TEXT PRIMARY KEY,
                params JSON NOT NULL,
                result JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE schedules (
                id TEXT PRIMARY KEY,
                params JSON NOT NULL,
                rrule TEXT NOT NULL,
                next_run TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                enabled INTEGER DEFAULT 1
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    conn = connect_db(str(db_path))
    conn.close()

    assert {
        "idempotency_key",
        "approval_status",
        "delivery_status",
        "approved_at",
        "rejected_at",
        "approval_note",
    }.issubset(_table_columns(db_path, "history"))
    assert {"is_test", "expires_at"}.issubset(_table_columns(db_path, "schedules"))
