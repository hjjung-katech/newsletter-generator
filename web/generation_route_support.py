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


_STATUS_CATEGORY_MAP = {
    "pending": "queued",
    "queued": "queued",
    "requested": "queued",
    "processing": "running",
    "running": "running",
    "started": "running",
    "completed": "completed",
    "finished": "completed",
    "success": "completed",
    "failed": "failed",
    "error": "failed",
    "redis_failed": "failed",
}

_STATUS_LABELS = {
    "queued": "대기 중",
    "running": "실행 중",
    "completed": "완료",
    "failed": "실패",
    "empty": "실행 이력 없음",
    "unknown": "상태 미상",
}

_APPROVAL_LABELS = {
    "pending": "승인 대기",
    "approved": "승인 완료",
    "rejected": "반려됨",
    "not_requested": "승인 불필요",
}

_APPROVAL_STATE_LABELS = {
    "pending": "승인 대기",
    "approved": "승인 완료",
    "rejected": "반려됨",
    "unavailable": "승인 불필요",
    "unknown": "승인 상태 미상",
}

_DELIVERY_LABELS = {
    "draft": "초안",
    "pending_approval": "승인 대기",
    "approved": "승인됨",
    "sent": "발송 완료",
    "send_failed": "발송 실패",
}


def _normalize_status_category(status: Any) -> str:
    normalized = str(status or "").strip().lower()
    if not normalized:
        return "unknown"
    return _STATUS_CATEGORY_MAP.get(normalized, "unknown")


def _normalize_approval_state(approval_status: Any) -> str:
    normalized = str(approval_status or "").strip().lower()
    if not normalized or normalized == "not_requested":
        return "unavailable"
    if normalized in {"pending", "approved", "rejected"}:
        return normalized
    return "unknown"


def _resolve_status_message(
    *,
    category: str,
    approval_status: str | None,
    delivery_status: str | None,
    error_message: str | None,
) -> str:
    if category == "queued":
        return "실행이 대기열에 등록되었습니다."
    if category == "running":
        return "실행이 진행 중입니다."
    if category == "failed":
        return error_message or "최근 실행이 실패했습니다."
    if category == "completed":
        if approval_status == "pending" or delivery_status == "pending_approval":
            return "생성은 완료되었고 승인 대기 중입니다."
        if approval_status == "rejected":
            return "생성은 완료되었지만 반려되어 draft 상태로 유지됩니다."
        if delivery_status == "sent":
            return "생성과 발송이 완료되었습니다."
        if delivery_status == "approved":
            return "생성은 완료되었고 발송 준비가 끝났습니다."
        return "최근 실행이 완료되었습니다."
    if category == "empty":
        return "아직 실행 이력이 없습니다."
    return "현재 상태를 확인할 수 없습니다."


def _resolve_approval_message(
    *,
    approval_state: str,
    delivery_status: str | None,
    can_resolve: bool,
) -> str:
    if approval_state == "pending":
        if can_resolve:
            return "검토 후 승인 또는 반려할 수 있습니다."
        return "승인 대기 상태이지만 현재는 처리할 수 없습니다."
    if approval_state == "approved":
        if delivery_status == "sent":
            return "승인 후 발송까지 완료되었습니다."
        if delivery_status == "approved":
            return "승인이 완료되었습니다. 이제 발송할 수 있습니다."
        return "승인이 완료되었습니다."
    if approval_state == "rejected":
        return "반려되어 draft 상태로 유지됩니다."
    if approval_state == "unavailable":
        return "승인 대상이 아닙니다."
    return "승인 상태를 확인할 수 없습니다."


def _resolve_approval_timestamp(
    *,
    approval_state: str,
    created_at: str | None,
    approved_at: str | None,
    rejected_at: str | None,
) -> tuple[str | None, str | None]:
    if approval_state == "approved" and approved_at:
        return approved_at, "승인 시각"
    if approval_state == "rejected" and rejected_at:
        return rejected_at, "반려 시각"
    if approval_state == "pending" and created_at:
        return created_at, "요청 시각"
    if created_at:
        return created_at, "기준 시각"
    return None, None


def build_execution_visibility(
    *,
    status: Any,
    created_at: str | None = None,
    started_at: str | None = None,
    updated_at: str | None = None,
    approved_at: str | None = None,
    rejected_at: str | None = None,
    approval_status: str | None = None,
    delivery_status: str | None = None,
    result: Any = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    result_mapping = result if isinstance(result, Mapping) else {}
    category = _normalize_status_category(status)
    primary_timestamp = (
        updated_at or started_at or approved_at or rejected_at or created_at
    )
    resolved_error = error_message
    if not resolved_error and isinstance(result_mapping, Mapping):
        raw_result_error = result_mapping.get("error")
        if raw_result_error:
            resolved_error = str(raw_result_error)

    return {
        "raw_status": status,
        "status_category": category,
        "status_label": _STATUS_LABELS.get(category, _STATUS_LABELS["unknown"]),
        "status_message": _resolve_status_message(
            category=category,
            approval_status=approval_status,
            delivery_status=delivery_status,
            error_message=resolved_error,
        ),
        "primary_timestamp": primary_timestamp,
        "approval_label": _APPROVAL_LABELS.get(approval_status)
        if approval_status is not None
        else None,
        "delivery_label": _DELIVERY_LABELS.get(delivery_status)
        if delivery_status is not None
        else None,
        "result_title": result_mapping.get("title"),
        "has_result": result is not None,
        "can_view_result": category == "completed" and result is not None,
    }


def build_approval_visibility(
    *,
    status: Any,
    approval_status: str | None,
    delivery_status: str | None,
    created_at: str | None = None,
    approved_at: str | None = None,
    rejected_at: str | None = None,
    result: Any = None,
) -> dict[str, Any]:
    approval_state = _normalize_approval_state(approval_status)
    result_mapping = result if isinstance(result, Mapping) else {}
    status_category = _normalize_status_category(status)
    can_resolve = approval_state == "pending" and status_category == "completed"
    can_approve = can_resolve and bool(result_mapping.get("html_content"))
    can_reject = can_resolve
    primary_timestamp, timestamp_label = _resolve_approval_timestamp(
        approval_state=approval_state,
        created_at=created_at,
        approved_at=approved_at,
        rejected_at=rejected_at,
    )

    return {
        "raw_approval_status": approval_status,
        "approval_state": approval_state,
        "approval_label": _APPROVAL_STATE_LABELS.get(
            approval_state, _APPROVAL_STATE_LABELS["unknown"]
        ),
        "approval_message": _resolve_approval_message(
            approval_state=approval_state,
            delivery_status=delivery_status,
            can_resolve=can_resolve,
        ),
        "primary_timestamp": primary_timestamp,
        "timestamp_label": timestamp_label,
        "can_resolve": can_resolve,
        "can_approve": can_approve,
        "can_reject": can_reject,
    }


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
    response["execution_visibility"] = build_execution_visibility(
        status=task.get("status"),
        started_at=task.get("started_at"),
        updated_at=task.get("updated_at"),
        approval_status=response.get("approval_status"),
        delivery_status=response.get("delivery_status"),
        result=result,
        error_message=task.get("error"),
    )
    response["approval_visibility"] = build_approval_visibility(
        status=task.get("status"),
        approval_status=response.get("approval_status"),
        delivery_status=response.get("delivery_status"),
        created_at=None,
        approved_at=None,
        rejected_at=None,
        result=result,
    )
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
        created_at,
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
        "created_at": created_at,
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

    response["execution_visibility"] = build_execution_visibility(
        status=status,
        created_at=created_at,
        approved_at=approved_at,
        rejected_at=rejected_at,
        approval_status=response.get("approval_status"),
        delivery_status=response.get("delivery_status"),
        result=result_data,
    )
    response["approval_visibility"] = build_approval_visibility(
        status=status,
        created_at=created_at,
        approved_at=approved_at,
        rejected_at=rejected_at,
        approval_status=response.get("approval_status"),
        delivery_status=response.get("delivery_status"),
        result=result_data,
    )
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
    result_data = parse_result(result)
    return {
        "id": job_id,
        "params": parse_params(params),
        "result": result_data,
        "created_at": created_at,
        "status": status,
        "idempotency_key": idempotency_key,
        "approval_status": approval_status,
        "delivery_status": delivery_status,
        "approved_at": approved_at,
        "rejected_at": rejected_at,
        "approval_note": approval_note,
        "execution_visibility": build_execution_visibility(
            status=status,
            created_at=created_at,
            approved_at=approved_at,
            rejected_at=rejected_at,
            approval_status=approval_status,
            delivery_status=delivery_status,
            result=result_data,
        ),
        "approval_visibility": build_approval_visibility(
            status=status,
            created_at=created_at,
            approved_at=approved_at,
            rejected_at=rejected_at,
            approval_status=approval_status,
            delivery_status=delivery_status,
            result=result_data,
        ),
    }


def build_approval_entry(
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
        approval_status,
        delivery_status,
        approved_at,
        rejected_at,
        approval_note,
    ) = row
    result_data = parse_result(result)
    return {
        "id": job_id,
        "params": parse_params(params),
        "result": result_data,
        "created_at": created_at,
        "status": status,
        "approval_status": approval_status,
        "delivery_status": delivery_status,
        "approved_at": approved_at,
        "rejected_at": rejected_at,
        "approval_note": approval_note,
        "execution_visibility": build_execution_visibility(
            status=status,
            created_at=created_at,
            approved_at=approved_at,
            rejected_at=rejected_at,
            approval_status=approval_status,
            delivery_status=delivery_status,
            result=result_data,
        ),
        "approval_visibility": build_approval_visibility(
            status=status,
            created_at=created_at,
            approved_at=approved_at,
            rejected_at=rejected_at,
            approval_status=approval_status,
            delivery_status=delivery_status,
            result=result_data,
        ),
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
