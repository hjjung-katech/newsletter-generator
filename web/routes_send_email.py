"""Route registration for newsletter send-email endpoint."""

import json
import logging
import sqlite3

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue

try:
    from mail import get_newsletter_subject, send_email_with_outbox
except ImportError:
    from .mail import get_newsletter_subject, send_email_with_outbox  # pragma: no cover

try:
    from db_state import (
        APPROVAL_STATUS_APPROVED,
        APPROVAL_STATUS_NOT_REQUESTED,
        DELIVERY_STATUS_SENT,
        update_history_review_state,
    )
except ImportError:
    from web.db_state import (  # pragma: no cover
        APPROVAL_STATUS_APPROVED,
        APPROVAL_STATUS_NOT_REQUESTED,
        DELIVERY_STATUS_SENT,
        update_history_review_state,
    )

try:
    from ops_logging import log_exception, log_info
except ImportError:
    from web.ops_logging import log_exception, log_info  # pragma: no cover


logger = logging.getLogger("web.routes_send_email")


def register_send_email_route(app: Flask, database_path: str) -> None:
    """Register send-email route on the given Flask app."""

    @app.route("/api/send-email", methods=["POST"])  # type: ignore[untyped-decorator]
    def send_email_api() -> ResponseReturnValue:
        """생성된 뉴스레터를 이메일로 발송"""
        try:
            data = request.get_json()
            job_id = data.get("job_id")
            email = data.get("email")

            if not job_id or not email:
                return jsonify({"error": "job_id와 email이 필요합니다"}), 400

            conn = sqlite3.connect(database_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT status, result, params, approval_status
                FROM history
                WHERE id = ?
                """,
                (job_id,),
            )
            row = cursor.fetchone()
            conn.close()

            if not row:
                return jsonify({"error": "작업을 찾을 수 없습니다"}), 404

            status, result_json, params_json, approval_status = row
            if status != "completed":
                return jsonify({"error": "완료되지 않은 작업입니다"}), 400

            if approval_status not in (
                None,
                APPROVAL_STATUS_NOT_REQUESTED,
                APPROVAL_STATUS_APPROVED,
            ):
                return jsonify({"error": "승인 대기 중인 작업입니다"}), 409

            result = json.loads(result_json) if result_json else {}
            params = json.loads(params_json) if params_json else {}

            html_content = result.get("html_content")
            if not html_content:
                return jsonify({"error": "발송할 콘텐츠가 없습니다"}), 400

            subject = get_newsletter_subject(result=result, params=params)
            send_result = send_email_with_outbox(
                db_path=database_path,
                job_id=job_id,
                to=email,
                subject=subject,
                html=html_content,
            )
            send_key = send_result["send_key"]

            if send_result.get("skipped"):
                update_history_review_state(
                    db_path=database_path,
                    job_id=job_id,
                    delivery_status=DELIVERY_STATUS_SENT,
                )
                log_info(
                    logger,
                    "email.send.deduplicated",
                    job_id=job_id,
                    email=email,
                    send_key=send_key,
                )
                return jsonify(
                    {
                        "success": True,
                        "message": "이미 발송된 이메일입니다",
                        "deduplicated": True,
                        "send_key": send_key,
                    }
                )

            update_history_review_state(
                db_path=database_path,
                job_id=job_id,
                delivery_status=DELIVERY_STATUS_SENT,
            )
            log_info(
                logger,
                "email.send.completed",
                job_id=job_id,
                email=email,
                send_key=send_key,
            )
            return jsonify(
                {
                    "success": True,
                    "message": "이메일이 성공적으로 발송되었습니다",
                    "deduplicated": False,
                    "send_key": send_key,
                }
            )

        except Exception as e:
            log_exception(
                logger,
                "email.send.failed",
                e,
                job_id=locals().get("job_id"),
                email=locals().get("email"),
            )
            return jsonify({"error": f"이메일 발송 실패: {str(e)}"}), 500
