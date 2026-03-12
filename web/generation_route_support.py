"""Bounded request/response helpers for generation routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Mapping

if TYPE_CHECKING:
    from web.types import GenerateNewsletterRequest
else:
    try:
        from types import GenerateNewsletterRequest
    except ImportError:
        from web.types import GenerateNewsletterRequest  # pragma: no cover


@dataclass(frozen=True)
class GenerateRequestContext:
    email: str | None
    send_email: bool
    has_domain: bool
    has_keywords: bool


@dataclass(frozen=True)
class PreviewRequestOptions:
    keywords: str
    period: int
    template_style: str


@dataclass(frozen=True)
class SyncGenerationOptions:
    keywords: Any
    domain: Any
    template_style: str
    email_compatible: bool
    period: int
    email: str
    preview_only: bool


@dataclass(frozen=True)
class GenerationInvokePlan:
    mode: str
    kwargs: dict[str, Any]


@dataclass(frozen=True)
class ScheduleCreateOptions:
    rrule: str
    params: dict[str, Any]
    is_test: bool
    expires_at: str | None


def validate_generate_request(data: dict[str, Any]) -> GenerateNewsletterRequest:
    """Validate generation request payload without runtime dynamic loading."""
    return GenerateNewsletterRequest(**data)


def build_generate_request_context(
    validated_data: GenerateNewsletterRequest,
) -> GenerateRequestContext:
    return GenerateRequestContext(
        email=validated_data.email,
        send_email=bool(validated_data.email),
        has_domain=bool(validated_data.domain),
        has_keywords=bool(validated_data.keywords),
    )


def build_generate_response(
    *, job_id: str, status: str, deduplicated: bool, idempotency_key: str
) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "status": status,
        "deduplicated": deduplicated,
        "idempotency_key": idempotency_key,
    }


def parse_preview_request(query_params: Mapping[str, Any]) -> PreviewRequestOptions:
    topic = str(query_params.get("topic", "") or "")
    keywords = query_params["keywords"] if "keywords" in query_params else topic
    template_style = str(query_params.get("template_style", "compact") or "compact")

    period_raw = query_params.get("period", 14)
    try:
        period = int(period_raw)
    except (TypeError, ValueError):
        period = 14

    if period not in {1, 7, 14, 30}:
        raise ValueError("Invalid period. Must be one of: 1, 7, 14, 30 days")
    if not keywords:
        raise ValueError("Missing required parameter: topic or keywords")

    return PreviewRequestOptions(
        keywords=str(keywords),
        period=period,
        template_style=template_style,
    )


def build_sync_generation_options(data: Mapping[str, Any]) -> SyncGenerationOptions:
    return SyncGenerationOptions(
        keywords=data.get("keywords", ""),
        domain=data.get("domain", ""),
        template_style=data.get("template_style", "compact"),
        email_compatible=data.get("email_compatible", False),
        period=data.get("period", 14),
        email=data.get("email", ""),
        preview_only=bool(data.get("preview_only", False)),
    )


def build_generation_invoke_plan(
    options: SyncGenerationOptions,
) -> GenerationInvokePlan:
    shared_kwargs = {
        "template_style": options.template_style,
        "email_compatible": options.email_compatible,
        "period": options.period,
    }
    if options.keywords:
        return GenerationInvokePlan(
            mode="keywords",
            kwargs={"keywords": options.keywords, **shared_kwargs},
        )
    if options.domain:
        return GenerationInvokePlan(
            mode="domain",
            kwargs={"domain": options.domain, **shared_kwargs},
        )
    raise ValueError("Either keywords or domain must be provided")


def build_sync_email_subject(
    *,
    result_title: str | None,
    keywords: Any,
    domain: Any,
) -> str:
    if keywords:
        return f"Newsletter: {keywords}"
    if domain:
        return f"Newsletter: {domain} Insights"
    return result_title or "Newsletter"


def build_sync_generation_response(
    result: Mapping[str, Any],
    *,
    using_real_cli: bool,
    template_style: str,
    email_compatible: bool,
    period: int,
    email_sent: bool,
) -> dict[str, Any]:
    html_content = result.get("content", "")
    title = result.get("title", "Newsletter")
    return {
        "status": result.get("status", "error"),
        "html_content": html_content,
        "title": title,
        "generation_stats": result.get("generation_stats", {}),
        "input_params": result.get("input_params", {}),
        "error": result.get("error"),
        "sent": email_sent,
        "email_sent": email_sent,
        "subject": title,
        "html_size": len(html_content),
        "processing_info": {
            "using_real_cli": using_real_cli,
            "template_style": template_style,
            "email_compatible": email_compatible,
            "period_days": period,
        },
    }


def build_status_response_from_task(
    job_id: str, task: Mapping[str, Any]
) -> dict[str, Any]:
    response = {
        "job_id": job_id,
        "status": task["status"],
        "sent": task.get("sent", False),
        "idempotency_key": task.get("idempotency_key"),
    }

    result = task.get("result")
    if isinstance(result, dict):
        response["result"] = result
        response["sent"] = result.get("sent", False)
        response["approval_status"] = result.get("approval_status")
        response["delivery_status"] = result.get("delivery_status")
    elif result is not None:
        response["result"] = result

    if "error" in task:
        response["error"] = task["error"]
    return response


def build_status_response_from_row(
    job_id: str,
    row: tuple[Any, ...],
    *,
    parse_params: Callable[[str | None], Any],
    parse_result: Callable[[str | None], Any],
) -> dict[str, Any]:
    (
        params,
        result,
        status,
        idempotency_key,
        approval_status,
        delivery_status,
        approved_at,
        rejected_at,
        approval_note,
    ) = row
    response = {
        "job_id": job_id,
        "status": status,
        "params": parse_params(params),
        "sent": False,
        "idempotency_key": idempotency_key,
        "approval_status": approval_status,
        "delivery_status": delivery_status,
        "approved_at": approved_at,
        "rejected_at": rejected_at,
        "approval_note": approval_note,
    }

    result_data = parse_result(result)
    if isinstance(result_data, dict):
        response["result"] = result_data
        response["sent"] = result_data.get("sent", False)
        if response["approval_status"] is None:
            response["approval_status"] = result_data.get("approval_status")
        if response["delivery_status"] is None:
            response["delivery_status"] = result_data.get("delivery_status")
    elif result_data is not None:
        response["result"] = result_data

    return response


def build_history_entry(
    row: tuple[Any, ...],
    *,
    parse_params: Callable[[str | None], Any],
    parse_result: Callable[[str | None], Any],
) -> dict[str, Any]:
    (
        job_id,
        params,
        result,
        created_at,
        status,
        idempotency_key,
        approval_status,
        delivery_status,
        approved_at,
        rejected_at,
        approval_note,
    ) = row
    return {
        "id": job_id,
        "params": parse_params(params),
        "result": parse_result(result),
        "created_at": created_at,
        "status": status,
        "idempotency_key": idempotency_key,
        "approval_status": approval_status,
        "delivery_status": delivery_status,
        "approved_at": approved_at,
        "rejected_at": rejected_at,
        "approval_note": approval_note,
    }


def parse_schedule_create_request(
    data: Mapping[str, Any] | None
) -> ScheduleCreateOptions:
    if not data or not data.get("rrule") or not data.get("email"):
        raise ValueError("Missing required fields: rrule, email")
    if not data.get("keywords") and not data.get("domain"):
        raise ValueError("Either keywords or domain is required")

    return ScheduleCreateOptions(
        rrule=str(data["rrule"]),
        params={
            "keywords": data.get("keywords"),
            "domain": data.get("domain"),
            "email": data["email"],
            "template_style": data.get("template_style", "compact"),
            "email_compatible": data.get("email_compatible", True),
            "period": data.get("period", 14),
            "send_email": True,
            "require_approval": bool(data.get("require_approval", False)),
        },
        is_test=bool(data.get("is_test", False)),
        expires_at=data.get("expires_at"),
    )
