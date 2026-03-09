"""SQLite schema and connection helpers for the web runtime."""

from __future__ import annotations

import sqlite3

_APPROVAL_STATUS_NOT_REQUESTED = "not_requested"
_DELIVERY_STATUS_DRAFT = "draft"


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
    _ensure_column(
        cursor,
        "history",
        "approval_status",
        f"TEXT DEFAULT '{_APPROVAL_STATUS_NOT_REQUESTED}'",
    )
    _ensure_column(
        cursor,
        "history",
        "delivery_status",
        f"TEXT DEFAULT '{_DELIVERY_STATUS_DRAFT}'",
    )
    _ensure_column(cursor, "history", "approved_at", "TEXT")
    _ensure_column(cursor, "history", "rejected_at", "TEXT")
    _ensure_column(cursor, "history", "approval_note", "TEXT")

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
        """
        CREATE TABLE IF NOT EXISTS generation_presets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            params JSON NOT NULL,
            is_default INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS source_policies (
            id TEXT PRIMARY KEY,
            pattern TEXT NOT NULL,
            policy_type TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(pattern, policy_type)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_events (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            job_id TEXT,
            schedule_id TEXT,
            status TEXT,
            deduplicated INTEGER NOT NULL DEFAULT 0,
            duration_seconds REAL,
            cost_usd REAL,
            payload JSON,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS archive_entries (
            job_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            snippet TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            source_value TEXT,
            keywords JSON NOT NULL,
            metadata JSON,
            search_text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
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
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_generation_presets_default ON generation_presets(is_default)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_generation_presets_updated_at ON generation_presets(updated_at)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_source_policies_type_active ON source_policies(policy_type, is_active)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_analytics_events_type_created ON analytics_events(event_type, created_at DESC)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_analytics_events_job_id ON analytics_events(job_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_analytics_events_schedule_id ON analytics_events(schedule_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_analytics_events_created_at ON analytics_events(created_at DESC)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_archive_entries_created_at ON archive_entries(created_at DESC)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_archive_entries_source_kind ON archive_entries(source_kind, created_at DESC)"
    )

    conn.commit()


def ensure_database_schema(db_path: str) -> None:
    """Run additive DB migrations and ensure runtime schema is complete."""
    conn = sqlite3.connect(db_path)
    try:
        _ensure_database_schema(conn)
    finally:
        conn.close()


def connect_db(db_path: str) -> sqlite3.Connection:
    """Return a connection after ensuring the additive runtime schema."""
    conn = sqlite3.connect(db_path)
    _ensure_database_schema(conn)
    return conn
