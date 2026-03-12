from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from flask import Flask

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

import generation_route_actions  # noqa: E402
import generation_route_dispatch  # noqa: E402
import routes_generation  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def _build_generation_app(
    database_path: str,
    *,
    task_queue: Any = None,
    redis_conn: Any = None,
) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    routes_generation.register_generation_routes(
        app=app,
        database_path=database_path,
        newsletter_cli=object(),
        in_memory_tasks={},
        task_queue=task_queue,
        redis_conn=redis_conn,
    )
    return app


def test_build_generation_dispatch_action_preserves_queue_and_thread_contract() -> None:
    queued = generation_route_actions.build_generation_dispatch_action(
        dispatch_via="redis",
        response_status="queued",
        should_start_in_memory_thread=False,
        payload={"keywords": ["AI"]},
        job_id="job_123",
        send_email=True,
        task_idempotency_key="generate:key",
        response_idempotency_key="generate:key",
        database_path="/tmp/newsletter.db",
        started_at="2026-03-12T00:00:00Z",
        build_processing_task_fn=lambda **_kwargs: {},
    )
    in_memory = generation_route_actions.build_generation_dispatch_action(
        dispatch_via="in_memory",
        response_status="processing",
        should_start_in_memory_thread=True,
        payload={"keywords": ["AI"]},
        job_id="job_456",
        send_email=False,
        task_idempotency_key=None,
        response_idempotency_key="generate:fallback",
        database_path="/tmp/newsletter.db",
        started_at="2026-03-12T00:00:00Z",
        build_processing_task_fn=lambda **kwargs: dict(kwargs),
    )

    assert queued.task_call is not None
    assert queued.task_call.args == (
        {"keywords": ["AI"]},
        "job_123",
        True,
        "generate:key",
        "/tmp/newsletter.db",
    )
    assert queued.task_call.queue_kwargs == {"job_id": "job_123"}
    assert queued.processing_task is None
    assert queued.thread_kwargs is None

    assert in_memory.task_call is None
    assert in_memory.processing_task == {
        "started_at": "2026-03-12T00:00:00Z",
        "idempotency_key": "generate:fallback",
    }
    assert in_memory.thread_kwargs == {
        "job_id": "job_456",
        "data": {"keywords": ["AI"]},
        "send_email": False,
        "idempotency_key": None,
    }


def test_build_schedule_dispatch_and_side_effect_helpers_preserve_contract() -> None:
    queued = generation_route_actions.build_schedule_run_dispatch_action(
        params={"keywords": ["AI"], "send_email": True},
        immediate_job_id="schedule_sched_1_run",
        effective_idempotency_key="schedule:key",
        database_path="/tmp/newsletter.db",
        has_async_runtime=True,
    )
    completed = generation_route_actions.build_schedule_run_dispatch_action(
        params={"keywords": ["AI"], "send_email": False},
        immediate_job_id="schedule_sched_1_run",
        effective_idempotency_key=None,
        database_path="/tmp/newsletter.db",
        has_async_runtime=False,
    )
    event = generation_route_actions.build_route_side_effect_action(
        schedule_id="schedule-1",
        job_id="schedule_sched_1_run",
        event_type="schedule.run_now.queued",
        source="api.schedule_run_now",
        status="queued",
        payload={"queue_job_id": "job-1"},
    )

    assert queued.mode == "queued"
    assert queued.task_call.queue_kwargs == {
        "job_id": "schedule_sched_1_run",
        "job_timeout": "10m",
    }
    assert queued.task_call.args[2] is True
    assert completed.mode == "immediate"
    assert completed.task_call.queue_kwargs == {"job_id": "schedule_sched_1_run"}
    assert completed.task_call.args[2] is False
    assert event == generation_route_actions.RouteSideEffectAction(
        schedule_id="schedule-1",
        job_id="schedule_sched_1_run",
        event_type="schedule.run_now.queued",
        source="api.schedule_run_now",
        status="queued",
        payload={"queue_job_id": "job-1"},
    )
    assert event.as_record_kwargs() == {
        "event_type": "schedule.run_now.queued",
        "schedule_id": "schedule-1",
        "job_id": "schedule_sched_1_run",
        "source": "api.schedule_run_now",
        "status": "queued",
        "payload": {"queue_job_id": "job-1"},
    }


def test_build_schedule_create_and_run_event_helpers_preserve_contract() -> None:
    created = generation_route_actions.build_schedule_create_action(
        schedule_id="schedule-1",
        params={"keywords": ["AI"], "email": "queue@example.com"},
        rrule="FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
        next_run_iso="2026-03-16T09:00:00+00:00",
        is_test=False,
        expires_at=None,
    )
    requested = generation_route_actions.build_schedule_run_requested_action(
        schedule_id="schedule-1",
        job_id="schedule_sched_1_run",
        idempotency_key="schedule:key",
    )
    queued = generation_route_actions.build_schedule_run_queued_action(
        schedule_id="schedule-1",
        job_id="schedule_sched_1_run",
        queue_job_id="rq-job-1",
    )
    completed = generation_route_actions.build_schedule_run_completed_action(
        schedule_id="schedule-1",
        job_id="schedule_sched_1_run",
        result_status="success",
    )
    failed = generation_route_actions.build_schedule_run_failed_action(
        schedule_id="schedule-1",
        job_id="schedule_sched_1_run",
        error="queue unavailable",
    )

    assert created.insert_values == (
        "schedule-1",
        '{"keywords": ["AI"], "email": "queue@example.com"}',
        "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
        "2026-03-16T09:00:00+00:00",
        0,
        None,
    )
    assert created.created_event.as_record_kwargs() == {
        "event_type": "schedule.created",
        "schedule_id": "schedule-1",
        "source": "api.schedule",
        "status": "scheduled",
        "payload": {
            "rrule": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
            "email": "queue@example.com",
            "is_test": False,
            "require_approval": False,
            "expires_at": None,
        },
    }
    assert requested.as_record_kwargs()["payload"] == {
        "idempotency_key": "schedule:key"
    }
    assert queued.as_record_kwargs()["payload"] == {"queue_job_id": "rq-job-1"}
    assert completed.as_record_kwargs()["status"] == "success"
    assert failed.as_record_kwargs()["payload"] == {"error": "queue unavailable"}


def test_build_sync_email_action_respects_preview_gate_and_subject_builder() -> None:
    builder_calls: list[dict[str, Any]] = []

    def _subject_builder(**kwargs: Any) -> str:
        builder_calls.append(kwargs)
        return "Newsletter: AI"

    skipped = generation_route_actions.build_sync_email_action(
        email="reader@example.com",
        preview_only=True,
        result={"content": "<html>preview</html>", "title": "Ignored"},
        keywords=["AI"],
        domain="",
        subject_builder=_subject_builder,
    )
    action = generation_route_actions.build_sync_email_action(
        email="reader@example.com",
        preview_only=False,
        result={"content": "<html>real</html>", "title": "Generated"},
        keywords=["AI"],
        domain="",
        subject_builder=_subject_builder,
    )

    assert skipped is None
    assert action == generation_route_actions.SyncEmailAction(
        to="reader@example.com",
        subject="Newsletter: AI",
        html="<html>real</html>",
    )
    assert builder_calls == [
        {
            "result_title": "Generated",
            "keywords": ["AI"],
            "domain": "",
        }
    ]


def test_generate_route_delegates_pre_dispatch_action_helper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: dict[str, Any] = {}

    class FakeQueue:
        def enqueue(self, func: Any, *args: Any, **kwargs: Any) -> None:
            observed["queued_func"] = func
            observed["queued_args"] = args
            observed["queued_kwargs"] = kwargs

    app = _build_generation_app(str(tmp_path / "storage.db"), task_queue=FakeQueue())

    def fake_resolve_generation_job(
        **_kwargs: Any,
    ) -> generation_route_dispatch.GenerationJobResolution:
        return generation_route_dispatch.GenerationJobResolution(
            job_id="job_123",
            deduplicated=False,
            stored_status="pending",
            idempotency_key="generate:key",
            effective_idempotency_key="generate:key",
        )

    def fake_build_generation_dispatch_action(**kwargs: Any) -> Any:
        observed["dispatch_action_kwargs"] = kwargs
        return generation_route_actions.GenerationDispatchAction(
            via="redis",
            response_status="queued",
            task_call=generation_route_actions.build_task_dispatch_call(
                payload=kwargs["payload"],
                job_id=kwargs["job_id"],
                send_email=kwargs["send_email"],
                idempotency_key=kwargs["task_idempotency_key"],
                database_path=kwargs["database_path"],
                queue_job_id=kwargs["job_id"],
            ),
            processing_task=None,
            thread_kwargs=None,
        )

    monkeypatch.setattr(
        routes_generation, "_resolve_generation_job", fake_resolve_generation_job
    )
    monkeypatch.setattr(
        routes_generation,
        "build_generation_dispatch_action",
        fake_build_generation_dispatch_action,
    )

    with app.test_client() as client:
        response = client.post(
            "/api/generate",
            data=json.dumps({"keywords": ["AI"], "email": "reader@example.com"}),
            content_type="application/json",
        )

    assert response.status_code == 202
    assert observed["dispatch_action_kwargs"]["dispatch_via"] == "redis"
    assert observed["dispatch_action_kwargs"]["send_email"] is True
    assert observed["queued_func"] is routes_generation.generate_newsletter_task
    assert observed["queued_args"][1] == "job_123"
    assert observed["queued_args"][2] is True
    assert observed["queued_kwargs"] == {"job_id": "job_123"}


def test_schedule_run_now_delegates_pre_side_effect_helpers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: dict[str, Any] = {"events": [], "recorded": []}

    class FakeQueue:
        def enqueue(self, func: Any, *args: Any, **kwargs: Any) -> Any:
            observed["queued_func"] = func
            observed["queued_args"] = args
            observed["queued_kwargs"] = kwargs
            return SimpleNamespace(id="queue-run-now-job")

    app = _build_generation_app(
        str(tmp_path / "storage.db"),
        task_queue=FakeQueue(),
        redis_conn=object(),
    )

    def fake_build_schedule_run_dispatch_action(**kwargs: Any) -> Any:
        observed["schedule_dispatch_kwargs"] = kwargs
        return generation_route_actions.ScheduleRunDispatchAction(
            mode="queued",
            task_call=generation_route_actions.build_task_dispatch_call(
                payload=kwargs["params"],
                job_id=kwargs["immediate_job_id"],
                send_email=kwargs["params"].get("send_email", False),
                idempotency_key=kwargs["effective_idempotency_key"],
                database_path=kwargs["database_path"],
                queue_job_id=kwargs["immediate_job_id"],
                job_timeout="10m",
            ),
        )

    def _record_event(event: generation_route_actions.RouteSideEffectAction) -> None:
        observed["events"].append(event.as_record_kwargs())

    def fake_build_schedule_create_action(**kwargs: Any) -> Any:
        observed["schedule_create_kwargs"] = kwargs
        event = generation_route_actions.RouteSideEffectAction(
            schedule_id=kwargs["schedule_id"],
            job_id=None,
            event_type="schedule.created",
            source="api.schedule",
            status="scheduled",
            payload={"rrule": kwargs["rrule"]},
        )
        _record_event(event)
        return generation_route_actions.ScheduleCreateAction(
            insert_values=(
                kwargs["schedule_id"],
                json.dumps(kwargs["params"]),
                kwargs["rrule"],
                kwargs["next_run_iso"],
                int(kwargs["is_test"]),
                kwargs["expires_at"],
            ),
            created_event=event,
        )

    def fake_build_schedule_run_requested_action(**kwargs: Any) -> Any:
        observed["requested_kwargs"] = kwargs
        event = generation_route_actions.RouteSideEffectAction(
            schedule_id=kwargs["schedule_id"],
            job_id=kwargs["job_id"],
            event_type="schedule.run_now.requested",
            source="api.schedule_run_now",
            status="requested",
            payload={"idempotency_key": kwargs["idempotency_key"]},
        )
        _record_event(event)
        return event

    def fake_build_schedule_run_queued_action(**kwargs: Any) -> Any:
        observed["queued_event_kwargs"] = kwargs
        event = generation_route_actions.RouteSideEffectAction(
            schedule_id=kwargs["schedule_id"],
            job_id=kwargs["job_id"],
            event_type="schedule.run_now.queued",
            source="api.schedule_run_now",
            status="queued",
            payload={"queue_job_id": kwargs["queue_job_id"]},
        )
        _record_event(event)
        return event

    def fake_build_schedule_run_completed_action(**kwargs: Any) -> Any:
        observed["completed_event_kwargs"] = kwargs
        return generation_route_actions.RouteSideEffectAction(
            schedule_id=kwargs["schedule_id"],
            job_id=kwargs["job_id"],
            event_type="schedule.run_now.completed",
            source="api.schedule_run_now",
            status=kwargs["result_status"],
            payload=None,
        )

    def fake_record_schedule_event(
        _database_path: str,
        *,
        event_type: str,
        schedule_id: str,
        job_id: str | None = None,
        source: str,
        status: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        observed["recorded"].append(
            {
                "event_type": event_type,
                "schedule_id": schedule_id,
                "job_id": job_id,
                "source": source,
                "status": status,
                "payload": payload,
            }
        )

    monkeypatch.setattr(
        routes_generation,
        "build_schedule_run_dispatch_action",
        fake_build_schedule_run_dispatch_action,
    )
    monkeypatch.setattr(
        routes_generation,
        "build_schedule_create_action",
        fake_build_schedule_create_action,
    )
    monkeypatch.setattr(
        routes_generation,
        "build_schedule_run_requested_action",
        fake_build_schedule_run_requested_action,
    )
    monkeypatch.setattr(
        routes_generation,
        "build_schedule_run_queued_action",
        fake_build_schedule_run_queued_action,
    )
    monkeypatch.setattr(
        routes_generation,
        "build_schedule_run_completed_action",
        fake_build_schedule_run_completed_action,
    )
    monkeypatch.setattr(
        routes_generation, "record_schedule_event", fake_record_schedule_event
    )

    with app.test_client() as client:
        create_response = client.post(
            "/api/schedule",
            data=json.dumps(
                {
                    "keywords": ["AI"],
                    "email": "queue@example.com",
                    "rrule": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
                }
            ),
            content_type="application/json",
        )
        created_payload = create_response.get_json()
        assert create_response.status_code == 201
        assert created_payload is not None

        run_response = client.post(
            f"/api/schedule/{created_payload['schedule_id']}/run"
        )

    assert run_response.status_code == 200
    run_payload = run_response.get_json()
    assert run_payload is not None
    assert run_payload["status"] == "queued"
    assert observed["schedule_create_kwargs"]["params"]["email"] == "queue@example.com"
    assert observed["schedule_dispatch_kwargs"]["has_async_runtime"] is True
    assert observed["requested_kwargs"]["idempotency_key"].startswith("schedule:")
    assert observed["queued_event_kwargs"]["queue_job_id"] == "queue-run-now-job"
    assert observed["queued_func"] is routes_generation.generate_newsletter_task
    assert observed["queued_kwargs"]["job_timeout"] == "10m"
    assert {event["event_type"] for event in observed["events"]} >= {
        "schedule.created",
        "schedule.run_now.requested",
        "schedule.run_now.queued",
    }
    assert {event["event_type"] for event in observed["recorded"]} >= {
        "schedule.created",
        "schedule.run_now.requested",
        "schedule.run_now.queued",
    }
