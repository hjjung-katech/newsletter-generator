"""Bounded pre-dispatch and pre-side-effect helpers for generation routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class TaskDispatchCall:
    args: tuple[dict[str, Any], str, bool, str | None, str]
    queue_kwargs: dict[str, Any]


@dataclass(frozen=True)
class GenerationDispatchAction:
    via: str
    response_status: str
    task_call: TaskDispatchCall | None
    processing_task: dict[str, Any] | None
    thread_kwargs: dict[str, Any] | None


@dataclass(frozen=True)
class ScheduleRunDispatchAction:
    mode: str
    task_call: TaskDispatchCall


@dataclass(frozen=True)
class RouteSideEffectAction:
    schedule_id: str
    job_id: str | None
    event_type: str
    source: str
    status: str | None
    payload: dict[str, Any] | None

    def as_record_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "event_type": self.event_type,
            "schedule_id": self.schedule_id,
            "source": self.source,
            "status": self.status,
        }
        if self.job_id is not None:
            kwargs["job_id"] = self.job_id
        if self.payload is not None:
            kwargs["payload"] = self.payload
        return kwargs


@dataclass(frozen=True)
class SyncEmailAction:
    to: str
    subject: str
    html: str


def build_task_dispatch_call(
    *,
    payload: dict[str, Any],
    job_id: str,
    send_email: bool,
    idempotency_key: str | None,
    database_path: str,
    queue_job_id: str | None = None,
    job_timeout: str | None = None,
) -> TaskDispatchCall:
    queue_kwargs: dict[str, Any] = {}
    if queue_job_id is not None:
        queue_kwargs["job_id"] = queue_job_id
    if job_timeout is not None:
        queue_kwargs["job_timeout"] = job_timeout
    return TaskDispatchCall(
        args=(payload, job_id, send_email, idempotency_key, database_path),
        queue_kwargs=queue_kwargs,
    )


def build_generation_dispatch_action(
    *,
    dispatch_via: str,
    response_status: str,
    should_start_in_memory_thread: bool,
    payload: dict[str, Any],
    job_id: str,
    send_email: bool,
    task_idempotency_key: str | None,
    response_idempotency_key: str,
    database_path: str,
    started_at: str,
    build_processing_task_fn: Callable[..., dict[str, Any]],
) -> GenerationDispatchAction:
    if dispatch_via == "redis":
        return GenerationDispatchAction(
            via=dispatch_via,
            response_status=response_status,
            task_call=build_task_dispatch_call(
                payload=payload,
                job_id=job_id,
                send_email=send_email,
                idempotency_key=task_idempotency_key,
                database_path=database_path,
                queue_job_id=job_id,
            ),
            processing_task=None,
            thread_kwargs=None,
        )

    thread_kwargs = None
    if should_start_in_memory_thread:
        thread_kwargs = {
            "job_id": job_id,
            "data": payload,
            "send_email": send_email,
            "idempotency_key": task_idempotency_key,
        }

    return GenerationDispatchAction(
        via=dispatch_via,
        response_status=response_status,
        task_call=None,
        processing_task=build_processing_task_fn(
            started_at=started_at,
            idempotency_key=response_idempotency_key,
        ),
        thread_kwargs=thread_kwargs,
    )


def build_schedule_run_dispatch_action(
    *,
    params: dict[str, Any],
    immediate_job_id: str,
    effective_idempotency_key: str | None,
    database_path: str,
    has_async_runtime: bool,
) -> ScheduleRunDispatchAction:
    return ScheduleRunDispatchAction(
        mode="queued" if has_async_runtime else "immediate",
        task_call=build_task_dispatch_call(
            payload=params,
            job_id=immediate_job_id,
            send_email=bool(params.get("send_email", False)),
            idempotency_key=effective_idempotency_key,
            database_path=database_path,
            queue_job_id=immediate_job_id,
            job_timeout="10m" if has_async_runtime else None,
        ),
    )


def build_route_side_effect_action(
    *,
    schedule_id: str,
    job_id: str | None = None,
    event_type: str,
    source: str,
    status: str | None,
    payload: Mapping[str, Any] | None = None,
) -> RouteSideEffectAction:
    return RouteSideEffectAction(
        schedule_id=schedule_id,
        job_id=job_id,
        event_type=event_type,
        source=source,
        status=status,
        payload=dict(payload) if payload is not None else None,
    )


def build_sync_email_action(
    *,
    email: str,
    preview_only: bool,
    result: Mapping[str, Any],
    keywords: Any,
    domain: Any,
    subject_builder: Callable[..., str],
) -> SyncEmailAction | None:
    html = result.get("content")
    if not email or not html or preview_only:
        return None

    subject = subject_builder(
        result_title=result.get("title"),
        keywords=keywords,
        domain=domain,
    )
    return SyncEmailAction(to=email, subject=subject, html=html)
