"""Background tasks for newsletter generation."""

from __future__ import annotations

import json
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
    from db_state import update_history_status
except ImportError:
    from web.db_state import update_history_status  # pragma: no cover

try:
    from mail import get_newsletter_subject, send_email_with_outbox
except ImportError:
    from .mail import get_newsletter_subject, send_email_with_outbox  # pragma: no cover

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "storage.db")


def _resolve_database_path(database_path: str | None) -> str:
    return database_path or DATABASE_PATH


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
