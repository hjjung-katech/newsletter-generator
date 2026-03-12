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


def test_build_generation_dispatch_plan_preserves_runtime_modes() -> None:
    queued = generation_route_dispatch.build_generation_dispatch_plan(
        has_task_queue=True,
        is_testing=False,
    )
    in_memory = generation_route_dispatch.build_generation_dispatch_plan(
        has_task_queue=False,
        is_testing=True,
    )

    assert queued == generation_route_dispatch.GenerationDispatchPlan(
        via="redis",
        response_status="queued",
        should_start_in_memory_thread=False,
    )
    assert in_memory == generation_route_dispatch.GenerationDispatchPlan(
        via="in_memory",
        response_status="processing",
        should_start_in_memory_thread=False,
    )


def test_build_schedule_helpers_preserve_response_contracts() -> None:
    schedule_entry = generation_route_dispatch.build_schedule_entry(
        (
            "schedule-1",
            '{"keywords":["AI"]}',
            "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
            "2026-03-19T00:00:00Z",
            "2026-03-12T00:00:00Z",
            1,
        ),
        parse_params=json.loads,
        serialize_timestamp=lambda value: value,
    )

    created_payload = generation_route_dispatch.build_schedule_created_response(
        schedule_id="schedule-1",
        next_run="2026-03-19T00:00:00Z",
    )
    created_event = generation_route_dispatch.build_schedule_created_event_payload(
        params={"email": "reader@example.com", "require_approval": True},
        rrule="FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
        is_test=False,
        expires_at=None,
    )

    assert schedule_entry["id"] == "schedule-1"
    assert schedule_entry["params"] == {"keywords": ["AI"]}
    assert schedule_entry["enabled"] is True
    assert created_payload == {
        "status": "scheduled",
        "schedule_id": "schedule-1",
        "next_run": "2026-03-19T00:00:00Z",
    }
    assert created_event == {
        "rrule": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
        "email": "reader@example.com",
        "is_test": False,
        "require_approval": True,
        "expires_at": None,
    }


def test_build_schedule_run_resolution_and_responses_preserve_contract() -> None:
    intended_run_at = routes_generation.get_utc_now()
    resolution = generation_route_dispatch.build_schedule_run_resolution(
        "schedule-1",
        {"keywords": ["AI"], "send_email": True},
        intended_run_at=intended_run_at,
        idempotency_enabled=True,
        schedule_idempotency_key_builder=lambda **kwargs: "schedule:key",
        derive_job_id_fn=lambda *_args, **_kwargs: "sched_suffix",
        to_iso_utc_fn=routes_generation.to_iso_utc,
    )

    queued_payload = generation_route_dispatch.build_schedule_run_response(
        resolution=resolution,
        status="queued",
    )
    completed_payload = generation_route_dispatch.build_schedule_run_response(
        resolution=resolution,
        status="completed",
        result={"status": "success", "title": "Newsletter"},
    )

    assert resolution.immediate_job_id == "schedule_schedule-1_suffix"
    assert queued_payload == {
        "status": "queued",
        "job_id": "schedule_schedule-1_suffix",
        "idempotency_key": "schedule:key",
        "message": "Newsletter generation started",
    }
    assert completed_payload == {
        "status": "completed",
        "job_id": "schedule_schedule-1_suffix",
        "idempotency_key": "schedule:key",
        "result": {"status": "success", "title": "Newsletter"},
    }
    assert generation_route_dispatch.build_schedule_run_requested_payload(
        "schedule:key"
    ) == {"idempotency_key": "schedule:key"}
    assert generation_route_dispatch.build_schedule_run_event_payload(
        queue_job_id="job-1"
    ) == {"queue_job_id": "job-1"}
    assert generation_route_dispatch.build_schedule_run_failed_payload("boom") == {
        "error": "boom"
    }


def test_build_in_memory_task_helpers_preserve_shape() -> None:
    processing = generation_route_dispatch.build_in_memory_processing_task(
        started_at="2026-03-12T00:00:00Z",
        idempotency_key="generate:key",
    )
    completed = generation_route_dispatch.build_in_memory_completed_task(
        result={"status": "success"},
        updated_at="2026-03-12T00:01:00Z",
    )
    failed = generation_route_dispatch.build_in_memory_failed_task(
        error="boom",
        updated_at="2026-03-12T00:01:00Z",
    )

    assert processing == {
        "status": "processing",
        "started_at": "2026-03-12T00:00:00Z",
        "idempotency_key": "generate:key",
    }
    assert completed == {
        "status": "completed",
        "result": {"status": "success"},
        "updated_at": "2026-03-12T00:01:00Z",
    }
    assert failed == {
        "status": "failed",
        "error": "boom",
        "updated_at": "2026-03-12T00:01:00Z",
    }


def test_generate_route_delegates_dispatch_planning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: dict[str, Any] = {}

    class FakeQueue:
        def enqueue(self, _func: Any, *args: Any, **kwargs: Any) -> None:
            observed["enqueue_args"] = args
            observed["enqueue_kwargs"] = kwargs

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

    def fake_build_generation_dispatch_plan(
        *, has_task_queue: bool, is_testing: bool
    ) -> generation_route_dispatch.GenerationDispatchPlan:
        observed["dispatch_plan_args"] = (has_task_queue, is_testing)
        return generation_route_dispatch.GenerationDispatchPlan(
            via="redis",
            response_status="queued",
            should_start_in_memory_thread=False,
        )

    def fake_build_generation_job_response(
        *,
        resolution: generation_route_dispatch.GenerationJobResolution,
        status: str,
        deduplicated: bool,
    ) -> dict[str, Any]:
        observed["response_args"] = (resolution.job_id, status, deduplicated)
        return {
            "job_id": resolution.job_id,
            "status": status,
            "deduplicated": deduplicated,
            "idempotency_key": resolution.idempotency_key,
        }

    monkeypatch.setattr(
        routes_generation, "_resolve_generation_job", fake_resolve_generation_job
    )
    monkeypatch.setattr(
        routes_generation,
        "build_generation_dispatch_plan",
        fake_build_generation_dispatch_plan,
    )
    monkeypatch.setattr(
        routes_generation,
        "build_generation_job_response",
        fake_build_generation_job_response,
    )

    with app.test_client() as client:
        response = client.post(
            "/api/generate",
            data=json.dumps({"keywords": ["AI"]}),
            content_type="application/json",
        )

    assert response.status_code == 202
    assert observed["dispatch_plan_args"] == (True, True)
    assert observed["response_args"] == ("job_123", "queued", False)


def test_schedule_routes_delegate_response_helpers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: dict[str, Any] = {}
    app = _build_generation_app(str(tmp_path / "storage.db"))

    def fake_build_schedule_created_event_payload(**kwargs: Any) -> dict[str, Any]:
        observed["create_event_kwargs"] = kwargs
        return {"rrule": kwargs["rrule"], "email": kwargs["params"]["email"]}

    def fake_build_schedule_created_response(
        *, schedule_id: str, next_run: str
    ) -> dict[str, Any]:
        observed["create_response_args"] = (schedule_id, next_run)
        return {"status": "scheduled", "schedule_id": schedule_id, "next_run": next_run}

    monkeypatch.setattr(
        routes_generation,
        "build_schedule_created_event_payload",
        fake_build_schedule_created_event_payload,
    )
    monkeypatch.setattr(
        routes_generation,
        "build_schedule_created_response",
        fake_build_schedule_created_response,
    )

    with app.test_client() as client:
        response = client.post(
            "/api/schedule",
            data=json.dumps(
                {
                    "keywords": ["AI"],
                    "email": "reader@example.com",
                    "rrule": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
                }
            ),
            content_type="application/json",
        )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload is not None
    assert payload["status"] == "scheduled"
    assert observed["create_event_kwargs"]["params"]["email"] == "reader@example.com"
    assert observed["create_response_args"][0] == payload["schedule_id"]


def test_schedule_run_now_delegates_run_response_helpers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: dict[str, Any] = {}
    app = _build_generation_app(str(tmp_path / "storage.db"))

    monkeypatch.setattr(
        routes_generation,
        "generate_newsletter_task",
        lambda *_args, **_kwargs: {"status": "success", "title": "Scheduled"},
    )

    def fake_build_schedule_run_requested_payload(
        idempotency_key: str,
    ) -> dict[str, Any]:
        observed["requested_payload"] = idempotency_key
        return {"idempotency_key": idempotency_key}

    def fake_build_schedule_run_response(
        *,
        resolution: generation_route_dispatch.ScheduleRunResolution,
        status: str,
        result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        observed["run_response_args"] = (resolution.schedule_id, status, result)
        payload = {
            "status": status,
            "job_id": resolution.immediate_job_id,
            "idempotency_key": resolution.idempotency_key,
        }
        if result is not None:
            payload["result"] = result
        return payload

    monkeypatch.setattr(
        routes_generation,
        "build_schedule_run_requested_payload",
        fake_build_schedule_run_requested_payload,
    )
    monkeypatch.setattr(
        routes_generation,
        "build_schedule_run_response",
        fake_build_schedule_run_response,
    )

    with app.test_client() as client:
        create_response = client.post(
            "/api/schedule",
            data=json.dumps(
                {
                    "keywords": ["AI"],
                    "email": "reader@example.com",
                    "rrule": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
                }
            ),
            content_type="application/json",
        )
        schedule_id = create_response.get_json()["schedule_id"]
        response = client.post(f"/api/schedule/{schedule_id}/run")

    assert response.status_code == 200
    assert observed["requested_payload"].startswith("schedule:")
    assert observed["run_response_args"][0] == schedule_id
    assert observed["run_response_args"][1] == "completed"


def test_get_schedules_delegates_entry_shaping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: dict[str, Any] = {}
    app = _build_generation_app(str(tmp_path / "storage.db"))

    def fake_build_schedule_entry(
        row: tuple[Any, ...],
        *,
        parse_params: Any,
        serialize_timestamp: Any,
    ) -> dict[str, Any]:
        observed["schedule_entry_row"] = row
        return {"id": row[0], "params": parse_params(row[1]), "enabled": bool(row[5])}

    monkeypatch.setattr(
        routes_generation, "build_schedule_entry", fake_build_schedule_entry
    )

    with app.test_client() as client:
        client.post(
            "/api/schedule",
            data=json.dumps(
                {
                    "keywords": ["AI"],
                    "email": "reader@example.com",
                    "rrule": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
                }
            ),
            content_type="application/json",
        )
        response = client.get("/api/schedules")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert observed["schedule_entry_row"][0] == payload[0]["id"]
