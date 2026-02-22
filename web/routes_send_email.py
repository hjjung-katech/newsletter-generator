"""Route registration for newsletter send-email endpoint."""

import json
import logging
import sqlite3
from types import ModuleType
from typing import cast

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue


def _resolve_mail_module() -> ModuleType:
    """Resolve mail module in both script and package execution modes."""
    try:
        import mail

        return cast(ModuleType, mail)
    except ImportError:
        from . import mail  # pragma: no cover

        return cast(ModuleType, mail)


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
                "SELECT status, result, params FROM history WHERE id = ?", (job_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if not row:
                return jsonify({"error": "작업을 찾을 수 없습니다"}), 404

            status, result_json, params_json = row
            if status != "completed":
                return jsonify({"error": "완료되지 않은 작업입니다"}), 400

            result = json.loads(result_json) if result_json else {}
            params = json.loads(params_json) if params_json else {}

            html_content = result.get("html_content")
            if not html_content:
                return jsonify({"error": "발송할 콘텐츠가 없습니다"}), 400

            mail_module = _resolve_mail_module()

            keywords = params.get("keywords", [])
            if isinstance(keywords, str):
                keywords = [keywords]

            subject = (
                f"Newsletter: {', '.join(keywords) if keywords else 'Your Newsletter'}"
            )

            mail_module.send_email(to=email, subject=subject, html=html_content)

            return jsonify({"success": True, "message": "이메일이 성공적으로 발송되었습니다"})

        except Exception as e:
            logging.error(f"Email sending failed: {e}")
            return jsonify({"error": f"이메일 발송 실패: {str(e)}"}), 500
