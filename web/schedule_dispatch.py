"""Scheduler enqueue and telemetry helpers for the canonical web runtime."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional

from rq import Queue

try:
    from db_state import (
        build_schedule_idempotency_key,
        derive_job_id,
        ensure_history_row,
        is_feature_enabled,
    )
except ImportError:
    from web.db_state import (  # pragma: no cover
        build_schedule_idempotency_key,
        derive_job_id,
        ensure_history_row,
        is_feature_enabled,
    )

try:
    from analytics import record_schedule_event
except ImportError:
    from web.analytics import record_schedule_event  # pragma: no cover

try:
    from ops_logging import log_exception, log_info
except ImportError:
    from web.ops_logging import log_exception, log_info  # pragma: no cover

ScheduleTask = Callable[..., Optional[dict[str, Any]]]


@dataclass(frozen=True)
class ScheduleExecutionContext:
    db_path: str
    schedule_id: str
    params: dict[str, Any]
    schedule_job_id: str
    idempotency_key: str
    send_email: bool


def _record_event(
    db_path: str,
    *,
    event_type: str,
    schedule_id: str,
    source: str = "schedule_runner",
    status: str,
    job_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    record_schedule_event(
        db_path,
        event_type=event_type,
        schedule_id=schedule_id,
        job_id=job_id,
        source=source,
        status=status,
        payload=payload,
    )


def record_preupdate_failure(
    db_path: str,
    schedule_id: str,
) -> None:
    _record_event(
        db_path,
        event_type="schedule.execute.failed",
        schedule_id=schedule_id,
        status="failed",
        payload={"reason": "next_run_update_failed"},
    )


def record_no_more_occurrences(
    db_path: str,
    schedule_id: str,
) -> None:
    _record_event(
        db_path,
        event_type="schedule.execute.disabled",
        schedule_id=schedule_id,
        status="disabled",
        payload={"reason": "no_more_occurrences"},
    )


def build_execution_context(
    db_path: str,
    schedule_id: str,
    params: dict[str, Any],
    intended_run_at: datetime,
    *,
    logger: logging.Logger,
) -> ScheduleExecutionContext:
    idempotency_enabled = is_feature_enabled("WEB_IDEMPOTENCY_ENABLED", default=True)
    if idempotency_enabled:
        idempotency_key = build_schedule_idempotency_key(
            schedule_id=schedule_id,
            intended_run_at=intended_run_at,
        )
    else:
        idempotency_key = f"schedule:{schedule_id}:{uuid.uuid4()}"

    job_suffix = derive_job_id(idempotency_key, prefix="sched").split("_", 1)[1]
    schedule_job_id = f"schedule_{schedule_id}_{job_suffix}"
    ensure_history_row(
        db_path=db_path,
        job_id=schedule_job_id,
        params=params,
        status="pending",
        idempotency_key=idempotency_key,
    )
    _record_event(
        db_path,
        event_type="schedule.execute.started",
        schedule_id=schedule_id,
        job_id=schedule_job_id,
        status="processing",
        payload={"idempotency_key": idempotency_key},
    )
    log_info(
        logger,
        "schedule.execute.started",
        schedule_id=schedule_id,
        keywords=params.get("keywords"),
        email=params.get("email"),
    )
    return ScheduleExecutionContext(
        db_path=db_path,
        schedule_id=schedule_id,
        params=params,
        schedule_job_id=schedule_job_id,
        idempotency_key=idempotency_key,
        send_email=bool(params.get("send_email", False)),
    )


def enqueue_schedule_job(
    queue: Queue | None,
    task_fn: ScheduleTask,
    context: ScheduleExecutionContext,
    *,
    logger: logging.Logger,
) -> bool:
    if queue is None:
        return False

    try:
        job = queue.enqueue(
            task_fn,
            context.params,
            context.schedule_job_id,
            context.send_email,
            context.idempotency_key,
            context.db_path,
            job_id=context.schedule_job_id,
            job_timeout="10m",
            result_ttl=86400,
        )
        queue_job_id = getattr(job, "id", context.schedule_job_id)
        log_info(
            logger,
            "schedule.execute.enqueued",
            schedule_id=context.schedule_id,
            job_id=queue_job_id,
        )
        _record_event(
            context.db_path,
            event_type="schedule.execute.enqueued",
            schedule_id=context.schedule_id,
            job_id=context.schedule_job_id,
            status="queued",
            payload={"queue_job_id": queue_job_id},
        )
        return True
    except Exception as redis_error:
        log_exception(
            logger,
            "schedule.execute.redis_failed",
            redis_error,
            schedule_id=context.schedule_id,
        )
        log_info(
            logger,
            "schedule.execute.fallback_sync",
            schedule_id=context.schedule_id,
        )
        _record_event(
            context.db_path,
            event_type="schedule.execute.redis_failed",
            schedule_id=context.schedule_id,
            job_id=context.schedule_job_id,
            status="fallback_sync",
            payload={"error": str(redis_error)},
        )
        return False


def run_sync_fallback(
    task_fn: ScheduleTask,
    context: ScheduleExecutionContext,
    *,
    logger: logging.Logger,
) -> Optional[dict[str, Any]]:
    log_info(logger, "schedule.execute.sync_started", schedule_id=context.schedule_id)
    result = task_fn(
        context.params,
        context.schedule_job_id,
        context.send_email,
        context.idempotency_key,
        context.db_path,
    )
    result_status = result.get("status", "unknown") if result else "unknown"
    log_info(
        logger,
        "schedule.execute.sync_completed",
        schedule_id=context.schedule_id,
        status=result_status,
    )
    _record_event(
        context.db_path,
        event_type="schedule.execute.completed",
        schedule_id=context.schedule_id,
        job_id=context.schedule_job_id,
        status=result_status,
    )
    return result


def record_execution_failure(
    db_path: str,
    schedule_id: str,
    error: Exception,
    *,
    job_id: str | None = None,
) -> None:
    _record_event(
        db_path,
        event_type="schedule.execute.failed",
        schedule_id=schedule_id,
        job_id=job_id,
        status="failed",
        payload={"error": str(error)},
    )
