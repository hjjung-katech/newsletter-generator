"""Scheduler scan and reschedule helpers for the canonical web runtime."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional, cast

from dateutil.rrule import rrulestr  # type: ignore[import-untyped]

try:
    from web.time_utils import to_iso_utc  # PyInstaller
except ImportError:
    from time_utils import to_iso_utc  # Development

try:
    from ops_logging import log_debug, log_error, log_exception, log_info
except ImportError:
    from web.ops_logging import (  # pragma: no cover
        log_debug,
        log_error,
        log_exception,
        log_info,
    )

logger = logging.getLogger(__name__)

# Keep a stable datetime parser even when callers patch their module-level `datetime`.
REAL_DATETIME = datetime

ScheduleParser = Callable[[str], datetime]
NextRunCalculator = Callable[[str, datetime | None], Optional[datetime]]


def parse_iso_datetime(iso_string: str) -> datetime:
    """Parse ISO datetime strings and normalize `Z` to UTC."""
    if iso_string.endswith("Z"):
        return REAL_DATETIME.fromisoformat(iso_string[:-1]).replace(tzinfo=timezone.utc)
    return REAL_DATETIME.fromisoformat(iso_string)


def calculate_next_run(
    rrule_str: str, after: datetime | None = None
) -> Optional[datetime]:
    """Calculate the next run time from an RRULE."""
    try:
        if after is None:
            after = REAL_DATETIME.now(timezone.utc)

        after_naive = after.replace(tzinfo=None) if after.tzinfo is not None else after
        rrule = rrulestr(rrule_str, dtstart=after_naive)
        next_occurrence_naive = rrule.after(after_naive)

        if next_occurrence_naive is None:
            return None

        return cast(datetime, next_occurrence_naive).replace(tzinfo=timezone.utc)
    except Exception as exc:
        log_exception(
            logger,
            "schedule.next_run.calculate_failed",
            exc,
            rrule=rrule_str,
        )
        return None


def update_schedule_next_run(
    db_path: str, schedule_id: str, next_run: datetime
) -> bool:
    """Persist the next run timestamp for a schedule."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE schedules
            SET next_run = ?
            WHERE id = ?
            """,
            (to_iso_utc(next_run), schedule_id),
        )
        conn.commit()
        conn.close()
        log_info(
            logger,
            "schedule.next_run.updated",
            schedule_id=schedule_id,
            next_run=next_run,
        )
        return True
    except Exception as exc:
        log_exception(
            logger,
            "schedule.next_run.update_failed",
            exc,
            schedule_id=schedule_id,
        )
        return False


def disable_schedule(db_path: str, schedule_id: str) -> bool:
    """Disable a schedule that should no longer execute."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE schedules
            SET enabled = 0
            WHERE id = ?
            """,
            (schedule_id,),
        )
        conn.commit()
        conn.close()
        log_info(logger, "schedule.disabled", schedule_id=schedule_id)
        return True
    except Exception as exc:
        log_exception(logger, "schedule.disable_failed", exc, schedule_id=schedule_id)
        return False


def get_pending_schedules(
    db_path: str,
    *,
    now: datetime,
    parse_datetime: ScheduleParser = parse_iso_datetime,
    calculate_next_run_fn: NextRunCalculator = calculate_next_run,
) -> list[dict[str, Any]]:
    """Return schedules that are ready for execution, ordered by due time."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        log_debug(
            logger,
            "schedule.scan.started",
            db_path=db_path,
            db_exists=os.path.exists(db_path),
            now=now,
        )

        now_iso = to_iso_utc(now)

        cursor.execute(
            "UPDATE schedules SET enabled = 0 WHERE is_test = 1 AND expires_at IS NOT NULL AND expires_at <= ?",
            (now_iso,),
        )
        expired_count = cursor.rowcount
        if expired_count > 0:
            log_info(
                logger,
                "schedule.expired_tests.disabled",
                count=expired_count,
            )

        cursor.execute(
            "SELECT id, params, rrule, next_run, created_at, is_test FROM schedules WHERE enabled = 1"
        )
        all_schedules = cursor.fetchall()
        log_debug(
            logger, "schedule.scan.loaded_active", active_count=len(all_schedules)
        )

        ready_for_execution: list[tuple[Any, ...]] = []
        updated_count = 0
        regular_window = timedelta(minutes=30)
        test_window = timedelta(minutes=10)

        for schedule in all_schedules:
            (
                schedule_id,
                params,
                rrule_str,
                next_run_str,
                created_at,
                is_test,
            ) = schedule

            try:
                next_run = parse_datetime(str(next_run_str))
                time_diff = now - next_run
                execution_window = test_window if is_test else regular_window

                log_debug(
                    logger,
                    "schedule.scan.evaluating",
                    schedule_id=schedule_id,
                    next_run=next_run_str,
                    time_diff_seconds=round(time_diff.total_seconds(), 1),
                    window_seconds=execution_window.total_seconds(),
                )

                if timedelta(0) <= time_diff <= execution_window:
                    log_debug(
                        logger,
                        "schedule.scan.ready",
                        schedule_id=schedule_id,
                        window_minutes=round(execution_window.total_seconds() / 60, 1),
                    )
                    ready_for_execution.append(schedule)
                elif time_diff > execution_window:
                    log_info(
                        logger,
                        "schedule.scan.expired",
                        schedule_id=schedule_id,
                        missed_window_minutes=round(time_diff.total_seconds() / 60, 1),
                    )

                    next_run_calculated = calculate_next_run_fn(str(rrule_str), now)
                    if next_run_calculated:
                        cursor.execute(
                            "UPDATE schedules SET next_run = ? WHERE id = ?",
                            (to_iso_utc(next_run_calculated), schedule_id),
                        )
                        updated_count += 1
                        log_info(
                            logger,
                            "schedule.scan.expired_rescheduled",
                            schedule_id=schedule_id,
                            previous_next_run=next_run_str,
                            next_run=to_iso_utc(next_run_calculated),
                        )
                    else:
                        cursor.execute(
                            "UPDATE schedules SET enabled = 0 WHERE id = ?",
                            (schedule_id,),
                        )
                        log_info(
                            logger,
                            "schedule.scan.disabled_no_more_occurrences",
                            schedule_id=schedule_id,
                        )
                else:
                    log_debug(
                        logger,
                        "schedule.scan.future",
                        schedule_id=schedule_id,
                        run_in_minutes=round(abs(time_diff.total_seconds()) / 60, 1),
                    )
            except Exception as parse_error:
                log_exception(
                    logger,
                    "schedule.scan.parse_failed",
                    parse_error,
                    schedule_id=schedule_id,
                )

        if expired_count > 0 or updated_count > 0:
            conn.commit()
        if updated_count > 0:
            log_info(
                logger,
                "schedule.scan.expired_updates_committed",
                updated_count=updated_count,
            )

        log_debug(
            logger,
            "schedule.scan.ready_summary",
            ready_count=len(ready_for_execution),
        )

        ready_for_execution.sort(
            key=lambda schedule_data: parse_datetime(schedule_data[3])
        )

        schedules: list[dict[str, Any]] = []
        for schedule_data in ready_for_execution:
            (
                schedule_id,
                params,
                rrule_str,
                next_run_str,
                created_at,
                is_test,
            ) = schedule_data
            is_test_bool = bool(is_test)

            log_debug(
                logger,
                "schedule.queue.ready_entry",
                schedule_id=schedule_id,
                schedule_type="test" if is_test_bool else "regular",
                next_run=next_run_str,
            )

            schedules.append(
                {
                    "id": schedule_id,
                    "params": json.loads(params),
                    "rrule": rrule_str,
                    "next_run": parse_datetime(str(next_run_str)),
                    "created_at": parse_datetime(str(created_at)),
                    "is_test": is_test_bool,
                }
            )

        conn.close()
        return schedules
    except Exception as exc:
        log_exception(logger, "schedule.scan.failed", exc, db_path=db_path)
        return []
