# web/mail.py
from postmarker.core import PostmarkClient
import os
import logging
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def _get_email_config():
    """이메일 설정을 동적으로 가져옵니다 (테스트 호환성 고려)"""
    try:
        from newsletter.config_manager import config_manager

        return config_manager.POSTMARK_SERVER_TOKEN, config_manager.EMAIL_SENDER
    except (ImportError, AttributeError):
        # Fallback to direct env access
        postmark_token = os.getenv("POSTMARK_SERVER_TOKEN")
        email_sender = os.getenv("EMAIL_SENDER") or os.getenv("POSTMARK_FROM_EMAIL")
        return postmark_token, email_sender


def send_email(to: str, subject: str, html: str, **kwargs):
    """단일 수신자용 Postmark 발송 래퍼."""
    # 동적으로 설정 가져오기
    token, from_email = _get_email_config()

    if not token:
        error_msg = (
            "POSTMARK_SERVER_TOKEN 환경변수가 설정되지 않았습니다. "
            "Postmark 계정에서 서버 토큰을 발급받아 설정해주세요. "
            "https://postmarkapp.com/ 에서 가입할 수 있습니다."
        )
        logging.error(error_msg)
        raise RuntimeError(error_msg)

    if not from_email:
        error_msg = (
            "EMAIL_SENDER 환경변수가 설정되지 않았습니다. "
            "발신자 이메일 주소를 설정해주세요."
        )
        logging.error(error_msg)
        raise RuntimeError(error_msg)

    try:
        client = PostmarkClient(server_token=token)
        response = client.emails.send(
            From=from_email,
            To=to,
            Subject=subject,
            HtmlBody=html,
            **kwargs,  # Attachments, MessageStream 등
        )

        logging.info(
            f"이메일 발송 성공: {to} (Message ID: {response.get('MessageID', 'N/A')})"
        )
        return response

    except Exception as e:
        error_msg = f"Postmark 이메일 발송 실패: {str(e)}"
        logging.error(error_msg)
        raise RuntimeError(error_msg)


def check_email_configuration():
    """이메일 설정 상태를 확인합니다."""
    try:
        from newsletter.config_manager import config_manager

        return config_manager.validate_email_config()
    except (ImportError, AttributeError):
        # Fallback 로직
        token, from_email = _get_email_config()

        return {
            "postmark_token_configured": bool(
                token
                and token != "your_postmark_server_token_here"
                and token != "your-postmark-server-token-here"
            ),
            "from_email_configured": bool(
                from_email
                and from_email != "noreply@yourdomain.com"
                and from_email != "your_verified_email@yourdomain.com"
            ),
            "ready": bool(
                token
                and from_email
                and token
                not in [
                    "your_postmark_server_token_here",
                    "your-postmark-server-token-here",
                ]
                and from_email
                not in ["noreply@yourdomain.com", "your_verified_email@yourdomain.com"]
            ),
        }


def send_test_email(to: str):
    """테스트 이메일을 발송합니다."""
    import datetime

    token, from_email = _get_email_config()

    test_html = """
    <html>
    <body>
        <h2>Newsletter Generator 테스트 이메일</h2>
        <p>이 메시지는 Newsletter Generator의 이메일 발송 기능이 정상적으로 작동하는지 확인하기 위한 테스트 이메일입니다.</p>
        <p><strong>발송 시간:</strong> {timestamp}</p>
        <p>문제없이 수신되었다면 이메일 발송 기능이 정상적으로 설정되었습니다.</p>
        <hr>
        <p style="font-size: 12px; color: #666;">
            설정된 발송자: {sender}<br>
            설정된 토큰: {token_masked}
        </p>
    </body>
    </html>
    """.format(
        timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        sender=from_email or "Unknown",
        token_masked=("***" + (token or "")[-4:] if token else "Not Set"),
    )

    return send_email(
        to=to, subject="Newsletter Generator 테스트 이메일", html=test_html
    )
