"""Route registration for email configuration/test endpoints."""

import logging
from types import ModuleType
from typing import cast

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue
from tenacity import RetryError


def _resolve_mail_module() -> ModuleType:
    """Resolve mail module in both script and package execution modes."""
    try:
        import mail

        return cast(ModuleType, mail)
    except ImportError:
        from . import mail  # pragma: no cover

        return cast(ModuleType, mail)


def register_email_api_routes(app: Flask) -> None:
    """Register email config and test routes on the given Flask app."""

    @app.route("/api/email-config")  # type: ignore[untyped-decorator]
    def check_email_config() -> ResponseReturnValue:
        """이메일 설정 상태를 확인"""
        try:
            mail_module = _resolve_mail_module()
            config_status = mail_module.check_email_configuration()

            return jsonify(
                {
                    "postmark_token_configured": config_status[
                        "postmark_token_configured"
                    ],
                    "from_email_configured": config_status["from_email_configured"],
                    "ready": config_status["ready"],
                    "message": (
                        "이메일 발송 준비 완료" if config_status["ready"] else "환경변수 설정이 필요합니다"
                    ),
                }
            )

        except Exception as e:
            logging.error(f"Email config check failed: {e}")
            return jsonify({"error": f"설정 확인 실패: {str(e)}"}), 500

    @app.route("/api/test-email", methods=["POST"])  # type: ignore[untyped-decorator]
    def send_test_email_api() -> ResponseReturnValue:
        """테스트 이메일을 발송"""
        try:
            data = request.get_json()
            email = data.get("email")

            if not email:
                return jsonify({"error": "이메일 주소가 필요합니다"}), 400

            # 이메일 형식 간단 검증
            if "@" not in email or "." not in email:
                return jsonify({"success": False, "error": "Invalid email format"}), 400

            mail_module = _resolve_mail_module()
            response = mail_module.send_test_email(to=email)

            return jsonify(
                {
                    "success": True,
                    "message": f"테스트 이메일이 {email}로 발송되었습니다",
                    "message_id": response.get("MessageID") if response else None,
                }
            )

        except Exception as e:
            logging.error(f"Test email sending failed: {e}")
            if isinstance(e, RetryError):
                return (
                    jsonify(
                        {
                            "error": f"RetryError[<Future at {hex(id(e))} state=finished raised RuntimeError>]"
                        }
                    ),
                    500,
                )
            return jsonify({"error": f"테스트 이메일 발송 실패: {str(e)}"}), 500
