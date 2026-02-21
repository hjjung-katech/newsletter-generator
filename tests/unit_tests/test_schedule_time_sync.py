#!/usr/bin/env python3
"""Unit tests for schedule time-window and sync behavior."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from web.schedule_runner import ScheduleRunner


@pytest.fixture
def temp_db_path():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE schedules (
            id TEXT PRIMARY KEY,
            params JSON NOT NULL,
            rrule TEXT NOT NULL,
            next_run TEXT NOT NULL,
            created_at TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            is_test INTEGER DEFAULT 0,
            expires_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()

    yield db_path

    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def runner(temp_db_path):
    schedule_runner = ScheduleRunner(db_path=temp_db_path, redis_url=None)
    schedule_runner.redis_conn = None
    schedule_runner.queue = None
    return schedule_runner


def _insert_schedule(
    db_path: str,
    schedule_id: str,
    next_run: datetime,
    *,
    is_test: int,
    enabled: int = 1,
) -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO schedules (id, params, rrule, next_run, created_at, enabled, is_test, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            schedule_id,
            json.dumps({"keywords": ["ai"], "send_email": False}),
            "FREQ=DAILY;BYHOUR=9;BYMINUTE=0",
            next_run.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            enabled,
            is_test,
            (datetime.now(timezone.utc) + timedelta(hours=1)).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
        ),
    )

    conn.commit()
    conn.close()


@pytest.mark.unit
def test_parse_iso_datetime_handles_z_suffix(runner):
    parsed = runner._parse_iso_datetime("2026-02-20T09:00:00.000000Z")
    assert parsed.tzinfo == timezone.utc
    assert parsed.hour == 9


@pytest.mark.unit
def test_test_schedule_window_boundary_is_inclusive(temp_db_path, runner):
    now = datetime.now(timezone.utc)
    _insert_schedule(
        temp_db_path,
        "test-window-boundary",
        now - timedelta(minutes=9, seconds=50),
        is_test=1,
    )

    pending = runner.get_pending_schedules()

    pending_ids = [item["id"] for item in pending]
    assert "test-window-boundary" in pending_ids


@pytest.mark.unit
def test_regular_schedule_window_boundary_is_inclusive(temp_db_path, runner):
    now = datetime.now(timezone.utc)
    _insert_schedule(
        temp_db_path,
        "regular-window-boundary",
        now - timedelta(minutes=29, seconds=50),
        is_test=0,
    )

    pending = runner.get_pending_schedules()

    pending_ids = [item["id"] for item in pending]
    assert "regular-window-boundary" in pending_ids


@pytest.mark.unit
def test_expired_schedule_updates_next_run(temp_db_path, runner):
    now = datetime.now(timezone.utc)
    old_next_run = now - timedelta(hours=2)

    _insert_schedule(
        temp_db_path,
        "expired-regular",
        old_next_run,
        is_test=0,
    )

    pending = runner.get_pending_schedules()

    # Expired schedule should not be in immediate queue.
    assert all(item["id"] != "expired-regular" for item in pending)

    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT next_run FROM schedules WHERE id = ?", ("expired-regular",))
    updated_next_run = cursor.fetchone()[0]
    conn.close()

    updated_dt = datetime.fromisoformat(updated_next_run.replace("Z", "+00:00"))
    assert updated_dt > now
