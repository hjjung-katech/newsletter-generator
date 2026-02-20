"""Background tasks for newsletter generation."""

from __future__ import annotations

import json
import os
import sqlite3
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from newsletter.api import (
    GenerateNewsletterRequest,
    NewsletterGenerationError,
    generate_newsletter,
)

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "storage.db")


def _ensure_history_row(job_id: str, params: Optional[Dict[str, Any]] = None) -> None:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM history WHERE id = ?", (job_id,))
    exists = cursor.fetchone() is not None

    if not exists:
        cursor.execute(
            "INSERT INTO history (id, params, status) VALUES (?, ?, ?)",
            (job_id, json.dumps(params or {}), "pending"),
        )

    conn.commit()
    conn.close()


def update_job_status(
    job_id: str,
    status: str,
    result: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> None:
    """Update job status in database, creating the row if needed."""
    _ensure_history_row(job_id, params)

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    if result is not None:
        cursor.execute(
            "UPDATE history SET status = ?, result = ? WHERE id = ?",
            (status, json.dumps(result), job_id),
        )
    else:
        cursor.execute("UPDATE history SET status = ? WHERE id = ?", (status, job_id))

    conn.commit()
    conn.close()


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
) -> Dict[str, Any]:
    """Generate newsletter in worker context with stable response schema."""
    print(f"🔄 Worker: starting newsletter generation for job {job_id}")
    update_job_status(job_id, "processing", params=data)

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
                from mail import send_email as mail_send_email

                mail_send_email(
                    to=email,
                    subject=result["title"],
                    html=result["html_content"],
                )
                response["sent"] = True
                response["email_sent"] = True
                response["email_to"] = email
            except Exception as exc:
                response["email_sent"] = False
                response["email_error"] = str(exc)

        update_job_status(job_id, "completed", response)
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
        update_job_status(job_id, "failed", error_response)
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
        update_job_status(job_id, "failed", error_response)
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
