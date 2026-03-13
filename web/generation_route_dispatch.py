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


_SCHEDULE_STATUS_LABELS = {
    "queued": "대기 중",
    "running": "실행 중",
    "completed": "완료",
    "failed": "실패",
    "empty": "실행 이력 없음",
    "unknown": "상태 미상",
}


def _derive_schedule_status(event_type: str, status: Any) -> str:
    normalized_status = str(status or "").strip().lower()
    if normalized_status in {"queued", "pending", "requested"}:
        return "queued"
    if normalized_status in {"processing", "running", "started"}:
        return "running"
    if normalized_status in {"completed", "finished", "success"}:
        return "completed"
    if normalized_status in {"failed", "error", "redis_failed"}:
        return "failed"

    if (
        event_type.endswith(".requested")
        or event_type.endswith(".queued")
        or event_type.endswith(".enqueued")
    ):
        return "queued"
    if event_type.endswith(".started"):
        return "running"
    if event_type.endswith(".completed"):
        return "completed"
    if event_type.endswith(".failed") or event_type.endswith(".redis_failed"):
        return "failed"
    return "unknown"


def _build_schedule_status_message(
    *,
    event_type: str,
    status_category: str,
    payload: Mapping[str, Any],
) -> str:
    if status_category == "empty":
        return "아직 실행 이력이 없습니다."
    if event_type.endswith(".requested"):
        return "즉시 실행 요청이 접수되었습니다."
    if event_type.endswith(".queued") or event_type.endswith(".enqueued"):
        return "실행이 대기열에 등록되었습니다."
    if event_type.endswith(".started") or status_category == "running":
        return "실행이 진행 중입니다."
    if event_type.endswith(".completed") or status_category == "completed":
        return "최근 예약 실행이 완료되었습니다."
    if (
        event_type.endswith(".failed")
        or event_type.endswith(".redis_failed")
        or status_category == "failed"
    ):
        return str(payload.get("error") or "최근 예약 실행이 실패했습니다.")
    return "현재 예약 실행 상태를 확인할 수 없습니다."


def build_schedule_execution_summary(
    latest_event: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not latest_event:
        return {
            "event_type": None,
            "job_id": None,
            "status_category": "empty",
            "status_label": _SCHEDULE_STATUS_LABELS["empty"],
            "status_message": "아직 실행 이력이 없습니다.",
            "primary_timestamp": None,
            "result_status": None,
        }

    event_type = str(latest_event.get("event_type") or "")
    payload = latest_event.get("payload")
    payload_mapping = payload if isinstance(payload, Mapping) else {}
    status_category = _derive_schedule_status(event_type, latest_event.get("status"))
    return {
        "event_type": event_type or None,
        "job_id": latest_event.get("job_id"),
        "status_category": status_category,
        "status_label": _SCHEDULE_STATUS_LABELS.get(
            status_category, _SCHEDULE_STATUS_LABELS["unknown"]
        ),
        "status_message": _build_schedule_status_message(
            event_type=event_type,
            status_category=status_category,
            payload=payload_mapping,
        ),
        "primary_timestamp": latest_event.get("created_at"),
        "result_status": payload_mapping.get("result_status"),
    }


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
    latest_execution: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    schedule_id, params, rrule, next_run, created_at, enabled = row
    return {
        "id": schedule_id,
        "params": parse_params(params),
        "rrule": rrule,
        "next_run": serialize_timestamp(next_run),
        "created_at": serialize_timestamp(created_at),
        "enabled": bool(enabled),
        "latest_execution": build_schedule_execution_summary(latest_execution),
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
