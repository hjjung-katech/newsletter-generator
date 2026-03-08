"""Analytics capture helpers for the canonical web runtime."""

from __future__ import annotations

from typing import Any, Dict

try:
    from db_state import record_analytics_event
except ImportError:
    from web.db_state import record_analytics_event  # pragma: no cover


def _coerce_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_generation_stats(result: Dict[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    stats = result.get("generation_stats")
    return stats if isinstance(stats, dict) else {}


def _extract_total_time(result: Dict[str, Any] | None) -> float | None:
    return _coerce_float(_extract_generation_stats(result).get("total_time"))


def _extract_total_cost_usd(result: Dict[str, Any] | None) -> float | None:
    stats = _extract_generation_stats(result)
    cost_summary = stats.get("cost_summary")
    if not isinstance(cost_summary, dict):
        return None
    return _coerce_float(cost_summary.get("total_cost_usd"))


def record_generation_started(
    db_path: str,
    *,
    job_id: str,
    params: Dict[str, Any],
    send_email: bool,
    source: str,
    idempotency_key: str | None = None,
    schedule_id: str | None = None,
) -> None:
    """Record the start of a generation attempt."""
    record_analytics_event(
        db_path,
        "generation.started",
        job_id=job_id,
        schedule_id=schedule_id,
        status="processing",
        payload={
            "source": source,
            "send_email": send_email,
            "has_email": bool(str(params.get("email", "") or "").strip()),
            "preview_only": bool(params.get("preview_only")),
            "template_style": params.get("template_style"),
            "period": params.get("period"),
            "idempotency_key": idempotency_key,
        },
    )


def record_generation_completed(
    db_path: str,
    *,
    job_id: str,
    result: Dict[str, Any],
    source: str,
    schedule_id: str | None = None,
) -> None:
    """Record the successful end of a generation attempt."""
    record_analytics_event(
        db_path,
        "generation.completed",
        job_id=job_id,
        schedule_id=schedule_id,
        status=result.get("status"),
        duration_seconds=_extract_total_time(result),
        cost_usd=_extract_total_cost_usd(result),
        payload={
            "source": source,
            "email_sent": bool(result.get("email_sent")),
            "email_deduplicated": bool(result.get("email_deduplicated")),
            "approval_status": result.get("approval_status"),
            "delivery_status": result.get("delivery_status"),
        },
    )


def record_generation_failed(
    db_path: str,
    *,
    job_id: str,
    error: Exception,
    source: str,
    schedule_id: str | None = None,
) -> None:
    """Record a failed generation attempt."""
    record_analytics_event(
        db_path,
        "generation.failed",
        job_id=job_id,
        schedule_id=schedule_id,
        status="error",
        payload={
            "source": source,
            "error": str(error),
            "error_type": type(error).__name__,
        },
    )


def record_email_event(
    db_path: str,
    *,
    event_type: str,
    job_id: str,
    recipient: str,
    source: str,
    send_key: str | None = None,
    schedule_id: str | None = None,
    status: str | None = None,
    deduplicated: bool = False,
    error: str | None = None,
) -> None:
    """Record an email delivery event."""
    payload = {
        "source": source,
        "recipient": recipient,
        "send_key": send_key,
    }
    if error:
        payload["error"] = error

    record_analytics_event(
        db_path,
        event_type,
        job_id=job_id,
        schedule_id=schedule_id,
        status=status,
        deduplicated=deduplicated,
        payload=payload,
    )


def record_schedule_event(
    db_path: str,
    *,
    event_type: str,
    schedule_id: str,
    source: str,
    job_id: str | None = None,
    status: str | None = None,
    payload: Dict[str, Any] | None = None,
) -> None:
    """Record a schedule lifecycle event."""
    event_payload = {"source": source}
    if payload:
        event_payload.update(payload)

    record_analytics_event(
        db_path,
        event_type,
        job_id=job_id,
        schedule_id=schedule_id,
        status=status,
        payload=event_payload,
    )
