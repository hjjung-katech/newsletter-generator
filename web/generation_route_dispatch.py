"""Bounded dispatch and schedule response helpers for generation routes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class GenerationJobResolution:
    job_id: str
    deduplicated: bool
    stored_status: str
    idempotency_key: str
    effective_idempotency_key: str | None


@dataclass(frozen=True)
class GenerationDispatchPlan:
    via: str
    response_status: str
    should_start_in_memory_thread: bool


@dataclass(frozen=True)
class ScheduleRunResolution:
    schedule_id: str
    params: dict[str, Any]
    immediate_job_id: str
    idempotency_key: str
    effective_idempotency_key: str | None


def build_generation_dispatch_plan(
    *, has_task_queue: bool, is_testing: bool
) -> GenerationDispatchPlan:
    if has_task_queue:
        return GenerationDispatchPlan(
            via="redis",
            response_status="queued",
            should_start_in_memory_thread=False,
        )
    return GenerationDispatchPlan(
        via="in_memory",
        response_status="processing",
        should_start_in_memory_thread=not is_testing,
    )


def build_generation_job_response(
    *,
    resolution: GenerationJobResolution,
    status: str,
    deduplicated: bool,
) -> dict[str, Any]:
    return {
        "job_id": resolution.job_id,
        "status": status,
        "deduplicated": deduplicated,
        "idempotency_key": resolution.idempotency_key,
    }


def build_in_memory_processing_task(
    *, started_at: str, idempotency_key: str
) -> dict[str, Any]:
    return {
        "status": "processing",
        "started_at": started_at,
        "idempotency_key": idempotency_key,
    }


def build_in_memory_completed_task(
    *, result: Mapping[str, Any], updated_at: str
) -> dict[str, Any]:
    return {
        "status": "completed",
        "result": dict(result),
        "updated_at": updated_at,
    }


def build_in_memory_failed_task(*, error: str, updated_at: str) -> dict[str, Any]:
    return {
        "status": "failed",
        "error": error,
        "updated_at": updated_at,
    }


def build_schedule_entry(
    row: tuple[Any, ...],
    *,
    parse_params: Callable[[str | None], Any],
    serialize_timestamp: Callable[[str | None], str | None],
) -> dict[str, Any]:
    schedule_id, params, rrule, next_run, created_at, enabled = row
    return {
        "id": schedule_id,
        "params": parse_params(params),
        "rrule": rrule,
        "next_run": serialize_timestamp(next_run),
        "created_at": serialize_timestamp(created_at),
        "enabled": bool(enabled),
    }


def build_schedule_created_event_payload(
    *,
    params: Mapping[str, Any],
    rrule: str,
    is_test: bool,
    expires_at: str | None,
) -> dict[str, Any]:
    return {
        "rrule": rrule,
        "email": params["email"],
        "is_test": is_test,
        "require_approval": bool(params.get("require_approval", False)),
        "expires_at": expires_at,
    }


def build_schedule_created_response(
    *, schedule_id: str, next_run: str
) -> dict[str, Any]:
    return {
        "status": "scheduled",
        "schedule_id": schedule_id,
        "next_run": next_run,
    }


def build_schedule_run_resolution(
    schedule_id: str,
    params: dict[str, Any],
    *,
    intended_run_at: datetime,
    idempotency_enabled: bool,
    schedule_idempotency_key_builder: Callable[..., str],
    derive_job_id_fn: Callable[..., str],
    to_iso_utc_fn: Callable[[datetime], str],
) -> ScheduleRunResolution:
    idempotency_key = schedule_idempotency_key_builder(
        schedule_id=schedule_id,
        intended_run_at=intended_run_at,
    )
    if not idempotency_enabled:
        idempotency_key = f"schedule:{schedule_id}:{to_iso_utc_fn(intended_run_at)}"
    job_suffix = derive_job_id_fn(idempotency_key, prefix="sched").split("_", 1)[1]
    immediate_job_id = f"schedule_{schedule_id}_{job_suffix}"
    return ScheduleRunResolution(
        schedule_id=schedule_id,
        params=params,
        immediate_job_id=immediate_job_id,
        idempotency_key=idempotency_key,
        effective_idempotency_key=idempotency_key if idempotency_enabled else None,
    )


def build_schedule_run_requested_payload(idempotency_key: str) -> dict[str, Any]:
    return {"idempotency_key": idempotency_key}


def build_schedule_run_event_payload(
    *, queue_job_id: str | None = None
) -> dict[str, Any]:
    if queue_job_id is None:
        return {}
    return {"queue_job_id": queue_job_id}


def build_schedule_run_failed_payload(error: str) -> dict[str, Any]:
    return {"error": error}


def build_schedule_run_response(
    *,
    resolution: ScheduleRunResolution,
    status: str,
    result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    response: dict[str, Any] = {
        "status": status,
        "job_id": resolution.immediate_job_id,
        "idempotency_key": resolution.idempotency_key,
    }
    if result is None:
        response["message"] = "Newsletter generation started"
    else:
        response["result"] = dict(result)
    return response
