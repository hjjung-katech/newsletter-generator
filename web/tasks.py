"""Background tasks for newsletter generation."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict

from newsletter_core.public.generation import (
    GenerateNewsletterRequest,
    NewsletterGenerationError,
    generate_newsletter,
)

try:
    from db_state import (
        APPROVAL_STATUS_NOT_REQUESTED,
        APPROVAL_STATUS_PENDING,
        DELIVERY_STATUS_DRAFT,
        DELIVERY_STATUS_PENDING_APPROVAL,
        DELIVERY_STATUS_SEND_FAILED,
        DELIVERY_STATUS_SENT,
        get_active_source_policies,
        update_history_review_state,
        update_history_status,
    )
except ImportError:
    from web.db_state import (  # pragma: no cover
        APPROVAL_STATUS_NOT_REQUESTED,
        APPROVAL_STATUS_PENDING,
        DELIVERY_STATUS_DRAFT,
        DELIVERY_STATUS_PENDING_APPROVAL,
        DELIVERY_STATUS_SEND_FAILED,
        DELIVERY_STATUS_SENT,
        get_active_source_policies,
        update_history_review_state,
        update_history_status,
    )

try:
    from mail import get_newsletter_subject, send_email_with_outbox
except ImportError:
    from .mail import get_newsletter_subject, send_email_with_outbox  # pragma: no cover

try:
    from ops_logging import log_exception, log_info, log_warning
except ImportError:
    from web.ops_logging import log_exception, log_info, log_warning  # pragma: no cover

try:
    from analytics import (
        record_email_event,
        record_generation_completed,
        record_generation_failed,
        record_generation_started,
    )
except ImportError:
    from web.analytics import (  # pragma: no cover
        record_email_event,
        record_generation_completed,
        record_generation_failed,
        record_generation_started,
    )

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "storage.db")
logger = logging.getLogger("web.tasks")


def _resolve_database_path(database_path: str | None) -> str:
    return database_path or DATABASE_PATH


def _build_request(
    data: Dict[str, Any], source_policies: Dict[str, list[str]] | None = None
) -> GenerateNewsletterRequest:
    policies = source_policies or {"allowlist": [], "blocklist": []}
    return GenerateNewsletterRequest(
        keywords=data.get("keywords"),
        domain=data.get("domain"),
        template_style=data.get("template_style", "compact"),
        email_compatible=bool(data.get("email_compatible", False)),
        period=int(data.get("period", 14)),
        suggest_count=int(data.get("suggest_count", 10)),
        source_allowlist=policies.get("allowlist") or [],
        source_blocklist=policies.get("blocklist") or [],
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
    log_info(
        logger,
        "worker.job.started",
        job_id=job_id,
        send_email=send_email,
        idempotency_key=idempotency_key,
        db_path=db_path,
    )
    update_history_status(
        db_path=db_path,
        job_id=job_id,
        status="processing",
        params=data,
        idempotency_key=idempotency_key,
    )
    record_generation_started(
        db_path,
        job_id=job_id,
        params=data,
        send_email=send_email,
        source="worker",
        idempotency_key=idempotency_key,
    )

    email = data.get("email", "")
    approval_required = bool(data.get("require_approval")) and bool(email)

    try:
        source_policies = get_active_source_policies(db_path)
        request = _build_request(data, source_policies=source_policies)
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
            "approval_required": approval_required,
            "approval_status": (
                APPROVAL_STATUS_PENDING
                if approval_required
                else APPROVAL_STATUS_NOT_REQUESTED
            ),
            "delivery_status": (
                DELIVERY_STATUS_PENDING_APPROVAL
                if approval_required
                else DELIVERY_STATUS_DRAFT
            ),
        }

        if send_email and email and not approval_required:
            try:
                send_result = send_email_with_outbox(
                    db_path=db_path,
                    job_id=job_id,
                    to=email,
                    subject=get_newsletter_subject(result=result, params=data),
                    html=result["html_content"],
                )
                response["sent"] = True
                response["email_sent"] = True
                response["email_to"] = email
                response["email_deduplicated"] = bool(send_result.get("skipped", False))
                response["send_key"] = send_result.get("send_key")
                record_email_event(
                    db_path,
                    event_type=(
                        "email.deduplicated"
                        if response["email_deduplicated"]
                        else "email.sent"
                    ),
                    job_id=job_id,
                    recipient=email,
                    send_key=response["send_key"],
                    source="worker",
                    status="sent",
                    deduplicated=response["email_deduplicated"],
                )
            except Exception as exc:
                response["email_sent"] = False
                response["email_error"] = str(exc)
                response["delivery_status"] = DELIVERY_STATUS_SEND_FAILED
                record_email_event(
                    db_path,
                    event_type="email.failed",
                    job_id=job_id,
                    recipient=email,
                    source="worker",
                    status="failed",
                    error=str(exc),
                )
                log_warning(
                    logger,
                    "worker.email.send_failed",
                    job_id=job_id,
                    email=email,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
        elif response["delivery_status"] == DELIVERY_STATUS_DRAFT and approval_required:
            response["delivery_status"] = DELIVERY_STATUS_PENDING_APPROVAL

        if response["email_sent"]:
            response["delivery_status"] = DELIVERY_STATUS_SENT

        update_history_status(
            db_path=db_path,
            job_id=job_id,
            status="completed",
            result=response,
            params=data,
            idempotency_key=idempotency_key,
        )
        update_history_review_state(
            db_path=db_path,
            job_id=job_id,
            approval_status=response["approval_status"],
            delivery_status=response["delivery_status"],
        )
        record_generation_completed(
            db_path,
            job_id=job_id,
            result=response,
            source="worker",
        )
        log_info(
            logger,
            "worker.job.completed",
            job_id=job_id,
            status=response["status"],
            email_sent=response["email_sent"],
            email_deduplicated=response.get("email_deduplicated"),
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
        record_generation_failed(
            db_path,
            job_id=job_id,
            error=exc,
            source="worker",
        )
        log_exception(logger, "worker.job.generation_error", exc, job_id=job_id)
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
        record_generation_failed(
            db_path,
            job_id=job_id,
            error=exc,
            source="worker",
        )
        log_exception(logger, "worker.job.failed", exc, job_id=job_id)
        raise


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
    log_info(
        logger,
        "worker.job.sample_result",
        result=generate_newsletter_task(test_params, "test-job-id"),
    )
