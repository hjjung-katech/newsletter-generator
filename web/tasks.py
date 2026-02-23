"""Background tasks for newsletter generation."""

from __future__ import annotations

import json
import os
import sqlite3
import traceback
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, cast

from newsletter_core.public.generation import (
    GenerateNewsletterRequest,
    NewsletterGenerationError,
    generate_newsletter,
)

try:
    from db_state import (
        get_or_create_outbox_record,
        hash_subject,
        is_feature_enabled,
        mark_outbox_failed,
        mark_outbox_sent,
        update_history_status,
    )
except ImportError:
    from web.db_state import (  # pragma: no cover
        get_or_create_outbox_record,
        hash_subject,
        is_feature_enabled,
        mark_outbox_failed,
        mark_outbox_sent,
        update_history_status,
    )

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "storage.db")


def _resolve_database_path(database_path: str | None) -> str:
    return database_path or DATABASE_PATH


def _resolve_mail_send_callable() -> Callable[..., Any]:
    try:
        from mail import send_email as send_email_fn

        return cast(Callable[..., Any], send_email_fn)
    except ImportError:
        from .mail import send_email as send_email_fn  # pragma: no cover

        return cast(Callable[..., Any], send_email_fn)


def _send_email_with_outbox(
    db_path: str,
    job_id: str,
    to: str,
    subject: str,
    html: str,
) -> Dict[str, Any]:
    send_email_fn = _resolve_mail_send_callable()
    outbox_enabled = is_feature_enabled("WEB_OUTBOX_ENABLED", default=True)
    send_key = f"{job_id}:{to}:{hash_subject(subject)}"

    if outbox_enabled:
        outbox_status = get_or_create_outbox_record(
            db_path=db_path,
            send_key=send_key,
            job_id=job_id,
            recipient=to,
            subject_hash=hash_subject(subject),
        )
        if outbox_status == "sent":
            return {"sent": True, "skipped": True, "send_key": send_key}

    try:
        provider_response = send_email_fn(to=to, subject=subject, html=html)
        provider_message_id = (
            provider_response.get("MessageID")
            if isinstance(provider_response, dict)
            else None
        )
        if outbox_enabled:
            mark_outbox_sent(
                db_path=db_path,
                send_key=send_key,
                provider_message_id=provider_message_id,
            )
        return {"sent": True, "skipped": False, "send_key": send_key}
    except Exception as exc:
        if outbox_enabled:
            mark_outbox_failed(
                db_path=db_path, send_key=send_key, error_message=str(exc)
            )
        raise


def _build_request(data: Dict[str, Any]) -> GenerateNewsletterRequest:
    return GenerateNewsletterRequest(
        keywords=data.get("keywords"),
        domain=data.get("domain"),
        template_style=data.get("template_style", "compact"),
        email_compatible=bool(data.get("email_compatible", False)),
        period=int(data.get("period", 14)),
        suggest_count=int(data.get("suggest_count", 10)),
    )


def generate_newsletter_task(
    data: Dict[str, Any],
    job_id: str,
    send_email: bool = False,
    idempotency_key: str | None = None,
    database_path: str | None = None,
) -> Dict[str, Any]:
    """Generate newsletter in worker context with stable response schema."""
    db_path = _resolve_database_path(database_path)
    print(f"🔄 Worker: starting newsletter generation for job {job_id}")
    update_history_status(
        db_path=db_path,
        job_id=job_id,
        status="processing",
        params=data,
        idempotency_key=idempotency_key,
    )

    email = data.get("email", "")

    try:
        request = _build_request(data)
        result = generate_newsletter(request)

        response: Dict[str, Any] = {
            "status": result["status"],
            "html_content": result["html_content"],
            "title": result["title"],
            "generation_stats": result.get("generation_stats", {}),
            "input_params": result.get("input_params", {}),
            "error": None,
            "sent": False,
            "email_sent": False,
        }

        if send_email and email:
            try:
                send_result = _send_email_with_outbox(
                    db_path=db_path,
                    job_id=job_id,
                    to=email,
                    subject=result["title"],
                    html=result["html_content"],
                )
                response["sent"] = True
                response["email_sent"] = True
                response["email_to"] = email
                response["email_deduplicated"] = bool(send_result.get("skipped", False))
                response["send_key"] = send_result.get("send_key")
            except Exception as exc:
                response["email_sent"] = False
                response["email_error"] = str(exc)

        update_history_status(
            db_path=db_path,
            job_id=job_id,
            status="completed",
            result=response,
            params=data,
            idempotency_key=idempotency_key,
        )
        return response

    except NewsletterGenerationError as exc:
        error_response = {
            "status": "error",
            "html_content": "",
            "title": "Newsletter Generation Failed",
            "generation_stats": {},
            "input_params": data,
            "error": str(exc),
            "sent": False,
            "email_sent": False,
        }
        update_history_status(
            db_path=db_path,
            job_id=job_id,
            status="failed",
            result=error_response,
            params=data,
            idempotency_key=idempotency_key,
        )
        raise
    except Exception as exc:
        error_response = {
            "status": "error",
            "html_content": "",
            "title": "Newsletter Generation Failed",
            "generation_stats": {},
            "input_params": data,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "sent": False,
            "email_sent": False,
        }
        update_history_status(
            db_path=db_path,
            job_id=job_id,
            status="failed",
            result=error_response,
            params=data,
            idempotency_key=idempotency_key,
        )
        raise


def generate_subject(params: Dict[str, Any]) -> str:
    """Generate newsletter subject based on parameters."""
    keywords = params.get("keywords")
    domain = params.get("domain")

    if keywords:
        if isinstance(keywords, list):
            return f"Newsletter: {', '.join(str(k) for k in keywords[:3])}"
        return f"Newsletter: {keywords}"
    if domain:
        return f"Newsletter: {domain} Insights"
    return f"Newsletter - {datetime.now().strftime('%Y-%m-%d')}"


def create_schedule_entry(params: Dict[str, Any], job_id: str) -> str:
    """Create a scheduled newsletter entry."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    schedule_id = f"schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    next_run = datetime.now() + timedelta(days=7)

    cursor.execute(
        """
        INSERT INTO schedules (id, params, rrule, next_run)
        VALUES (?, ?, ?, ?)
        """,
        (schedule_id, json.dumps(params), params.get("rrule", "FREQ=WEEKLY"), next_run),
    )

    conn.commit()
    conn.close()
    return schedule_id


if __name__ == "__main__":
    test_params = {"keywords": "AI, machine learning", "email": "test@example.com"}
    print(generate_newsletter_task(test_params, "test-job-id"))
