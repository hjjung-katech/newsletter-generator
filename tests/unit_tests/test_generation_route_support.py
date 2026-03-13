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

import generation_route_support  # noqa: E402
import routes_generation  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def _build_generation_app(
    database_path: str,
    *,
    newsletter_cli: Any | None = None,
    in_memory_tasks: dict[str, Any] | None = None,
    task_queue: Any = None,
    redis_conn: Any = None,
) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    routes_generation.register_generation_routes(
        app=app,
        database_path=database_path,
        newsletter_cli=object() if newsletter_cli is None else newsletter_cli,
        in_memory_tasks={} if in_memory_tasks is None else in_memory_tasks,
        task_queue=task_queue,
        redis_conn=redis_conn,
    )
    return app


def test_validate_generate_request_normalizes_keywords_list() -> None:
    validated = generation_route_support.validate_generate_request(
        {
            "keywords": ["AI", "robotics"],
            "email": "reader@example.com",
            "period": 14,
        }
    )

    assert validated.keywords == "AI, robotics"
    assert validated.email == "reader@example.com"


def test_build_generate_request_context_preserves_log_fields() -> None:
    validated = generation_route_support.validate_generate_request(
        {"keywords": "AI", "email": "reader@example.com"}
    )

    context = generation_route_support.build_generate_request_context(validated)

    assert context.email == "reader@example.com"
    assert context.send_email is True
    assert context.has_keywords is True
    assert context.has_domain is False


def test_parse_preview_request_preserves_topic_fallback_and_validation() -> None:
    preview = generation_route_support.parse_preview_request(
        {"topic": "AI", "template_style": "compact"}
    )

    assert preview.keywords == "AI"
    assert preview.period == 14
    assert preview.template_style == "compact"

    with pytest.raises(ValueError, match="Invalid period"):
        generation_route_support.parse_preview_request({"keywords": "AI", "period": 9})

    with pytest.raises(ValueError, match="Missing required parameter"):
        generation_route_support.parse_preview_request({"keywords": ""})


def test_build_generation_invoke_plan_prefers_keywords_then_domain() -> None:
    keyword_options = generation_route_support.build_sync_generation_options(
        {"keywords": "AI", "domain": "mobility", "period": 7}
    )
    keyword_plan = generation_route_support.build_generation_invoke_plan(
        keyword_options
    )

    assert keyword_plan.mode == "keywords"
    assert keyword_plan.kwargs == {
        "keywords": "AI",
        "template_style": "compact",
        "email_compatible": False,
        "period": 7,
    }

    domain_options = generation_route_support.build_sync_generation_options(
        {"domain": "mobility"}
    )
    domain_plan = generation_route_support.build_generation_invoke_plan(domain_options)

    assert domain_plan.mode == "domain"
    assert domain_plan.kwargs["domain"] == "mobility"


def test_build_sync_generation_response_preserves_contract() -> None:
    response = generation_route_support.build_sync_generation_response(
        {
            "status": "success",
            "content": "<html>ok</html>",
            "title": "AI Weekly",
            "generation_stats": {"articles": 4},
            "input_params": {"keywords": "AI"},
            "error": None,
        },
        using_real_cli=True,
        template_style="compact",
        email_compatible=False,
        period=14,
        email_sent=True,
    )

    assert response == {
        "status": "success",
        "html_content": "<html>ok</html>",
        "title": "AI Weekly",
        "generation_stats": {"articles": 4},
        "input_params": {"keywords": "AI"},
        "error": None,
        "sent": True,
        "email_sent": True,
        "subject": "AI Weekly",
        "html_size": len("<html>ok</html>"),
        "processing_info": {
            "using_real_cli": True,
            "template_style": "compact",
            "email_compatible": False,
            "period_days": 14,
        },
    }


def test_build_status_and_history_helpers_preserve_payload_shape() -> None:
    row = (
        '{"keywords":"AI"}',
        '{"sent": true, "approval_status": "approved"}',
        "2026-03-12T00:00:00Z",
        "completed",
        "generate:123",
        None,
        None,
        None,
        None,
        None,
    )

    status_response = generation_route_support.build_status_response_from_row(
        "job-1",
        row,
        parse_params=json.loads,
        parse_result=json.loads,
    )

    assert status_response["params"] == {"keywords": "AI"}
    assert status_response["sent"] is True
    assert status_response["approval_status"] == "approved"
    assert status_response["execution_visibility"]["status_category"] == "completed"
    assert status_response["execution_visibility"]["status_label"] == "완료"
    assert (
        status_response["execution_visibility"]["primary_timestamp"]
        == "2026-03-12T00:00:00Z"
    )

    history_entry = generation_route_support.build_history_entry(
        (
            "job-1",
            '{"keywords":"AI"}',
            '{"status":"success"}',
            "2026-03-12T00:00:00Z",
            "completed",
            "generate:123",
            "pending",
            None,
            None,
            None,
            None,
        ),
        parse_params=json.loads,
        parse_result=json.loads,
    )

    assert history_entry["id"] == "job-1"
    assert history_entry["params"] == {"keywords": "AI"}
    assert history_entry["result"] == {"status": "success"}
    assert history_entry["execution_visibility"]["status_category"] == "completed"
    assert history_entry["execution_visibility"]["status_label"] == "완료"


def test_build_execution_visibility_exposes_operator_facing_labels() -> None:
    visibility = generation_route_support.build_execution_visibility(
        status="completed",
        created_at="2026-03-12T00:00:00Z",
        approval_status="pending",
        delivery_status="pending_approval",
        result={"title": "AI Weekly"},
    )

    assert visibility == {
        "raw_status": "completed",
        "status_category": "completed",
        "status_label": "완료",
        "status_message": "생성은 완료되었고 승인 대기 중입니다.",
        "primary_timestamp": "2026-03-12T00:00:00Z",
        "approval_label": "승인 대기",
        "delivery_label": "승인 대기",
        "result_title": "AI Weekly",
        "has_result": True,
        "can_view_result": True,
    }


def test_parse_schedule_create_request_builds_normalized_params() -> None:
    request = generation_route_support.parse_schedule_create_request(
        {
            "keywords": ["AI", "robotics"],
            "email": "schedule@example.com",
            "rrule": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
            "require_approval": True,
        }
    )

    assert request.rrule == "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0"
    assert request.params == {
        "keywords": ["AI", "robotics"],
        "domain": None,
        "email": "schedule@example.com",
        "template_style": "compact",
        "email_compatible": True,
        "period": 14,
        "send_email": True,
        "require_approval": True,
    }
    assert request.is_test is False
    assert request.expires_at is None


def test_generate_route_delegates_request_context_helpers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = _build_generation_app(str(tmp_path / "storage.db"))
    observed: dict[str, Any] = {}

    def fake_validate_generate_request(data: dict[str, Any]) -> SimpleNamespace:
        observed["validated_payload"] = data
        return SimpleNamespace(email="reader@example.com", domain=None, keywords="AI")

    def fake_build_generate_request_context(
        validated_data: Any,
    ) -> generation_route_support.GenerateRequestContext:
        observed["validated_data"] = validated_data
        return generation_route_support.GenerateRequestContext(
            email="reader@example.com",
            send_email=True,
            has_domain=False,
            has_keywords=True,
        )

    def fake_resolve_generation_job(
        **kwargs: Any,
    ) -> routes_generation.GenerationJobResolution:
        observed["resolution_payload"] = kwargs["payload"]
        return routes_generation.GenerationJobResolution(
            job_id="job_123",
            deduplicated=False,
            stored_status="pending",
            idempotency_key="generate:abc",
            effective_idempotency_key="generate:abc",
        )

    def fake_dispatch_generation_job(**kwargs: Any) -> dict[str, Any]:
        observed["dispatch_send_email"] = kwargs["send_email"]
        return {
            "job_id": "job_123",
            "status": "processing",
            "deduplicated": False,
            "idempotency_key": "generate:abc",
        }

    monkeypatch.setattr(
        routes_generation, "validate_generate_request", fake_validate_generate_request
    )
    monkeypatch.setattr(
        routes_generation,
        "build_generate_request_context",
        fake_build_generate_request_context,
    )
    monkeypatch.setattr(
        routes_generation, "_resolve_generation_job", fake_resolve_generation_job
    )
    monkeypatch.setattr(
        routes_generation, "_dispatch_generation_job", fake_dispatch_generation_job
    )

    with app.test_client() as client:
        response = client.post(
            "/api/generate",
            json={"keywords": "AI", "email": "reader@example.com"},
        )

    assert response.status_code == 202
    assert observed["validated_payload"] == {
        "keywords": "AI",
        "email": "reader@example.com",
    }
    assert observed["dispatch_send_email"] is True


def test_preview_route_delegates_preview_request_parsing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cli_calls: dict[str, Any] = {}

    class FakeCLI:
        def generate_newsletter(self, **kwargs: Any) -> dict[str, Any]:
            cli_calls["kwargs"] = kwargs
            return {"status": "success", "content": "<html>preview</html>"}

    observed: dict[str, Any] = {}

    def fake_parse_preview_request(
        data: dict[str, Any],
    ) -> generation_route_support.PreviewRequestOptions:
        observed["query"] = data
        return generation_route_support.PreviewRequestOptions(
            keywords="AI",
            period=7,
            template_style="compact",
        )

    monkeypatch.setattr(
        routes_generation, "parse_preview_request", fake_parse_preview_request
    )

    app = _build_generation_app(
        str(tmp_path / "storage.db"),
        newsletter_cli=FakeCLI(),
    )

    with app.test_client() as client:
        response = client.get("/newsletter?topic=ignored")

    assert response.status_code == 200
    assert observed["query"] == {"topic": "ignored"}
    assert cli_calls["kwargs"] == {
        "keywords": "AI",
        "template_style": "compact",
        "email_compatible": False,
        "period": 7,
    }


def test_schedule_create_route_delegates_request_parsing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: dict[str, Any] = {}

    def fake_parse_schedule_create_request(
        data: dict[str, Any] | None,
    ) -> generation_route_support.ScheduleCreateOptions:
        observed["payload"] = data
        return generation_route_support.ScheduleCreateOptions(
            rrule="FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
            params={
                "keywords": "AI",
                "domain": None,
                "email": "schedule@example.com",
                "template_style": "compact",
                "email_compatible": True,
                "period": 14,
                "send_email": True,
                "require_approval": False,
            },
            is_test=False,
            expires_at=None,
        )

    monkeypatch.setattr(
        routes_generation,
        "parse_schedule_create_request",
        fake_parse_schedule_create_request,
    )

    app = _build_generation_app(str(tmp_path / "storage.db"))

    with app.test_client() as client:
        response = client.post(
            "/api/schedule",
            json={
                "keywords": "AI",
                "email": "schedule@example.com",
                "rrule": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
            },
        )

    assert response.status_code == 201
    assert observed["payload"] == {
        "keywords": "AI",
        "email": "schedule@example.com",
        "rrule": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
    }
