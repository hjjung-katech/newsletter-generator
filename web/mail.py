# web/mail.py
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Dict, cast

from postmarker.core import PostmarkClient
from tenacity import retry, stop_after_attempt

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

_POSTMARK_TOKEN_PLACEHOLDERS = {
    "your" + "_postmark_server_token_here",
    "your" + "-postmark-server-token-here",
}

try:
    from db_state import (
        get_or_create_outbox_record,
        hash_subject,
        is_feature_enabled,
        mark_outbox_failed,
        mark_outbox_sent,
    )
except ImportError:
    from web.db_state import (  # pragma: no cover
        get_or_create_outbox_record,
        hash_subject,
        is_feature_enabled,
        mark_outbox_failed,
        mark_outbox_sent,
    )


def _get_email_config() -> tuple[str | None, str | None]:
    """이메일 설정을 동적으로 가져옵니다 (테스트 호환성 고려)"""
    try:
        from newsletter_core.public.settings import get_email_config

        token, from_email = get_email_config()
        return token, from_email
    except Exception:
        return None, None


def resolve_mail_send_callable() -> Callable[..., Any]:
    for module_name in ("mail", "web.mail"):
        module = sys.modules.get(module_name)
        candidate = getattr(module, "send_email", None) if module else None
        if callable(candidate):
            return cast(Callable[..., Any], candidate)
    return cast(Callable[..., Any], send_email)


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
    return "Your Newsletter"


def get_newsletter_subject(
    *, result: Dict[str, Any] | None = None, params: Dict[str, Any] | None = None
) -> str:
    """Prefer generated title and fall back to parameter-derived subject."""
    if result:
        title = result.get("title")
        if isinstance(title, str) and title.strip():
            return title
    return generate_subject(params or {})


def send_email_with_outbox(
    *,
    db_path: str,
    job_id: str,
    to: str,
    subject: str,
    html: str,
    send_email_fn: Callable[..., Any] | None = None,
) -> Dict[str, Any]:
    """Send email with shared outbox/send_key duplicate prevention."""
    outbox_enabled = is_feature_enabled("WEB_OUTBOX_ENABLED", default=True)
    subject_hash = hash_subject(subject)
    send_key = f"{job_id}:{to}:{subject_hash}"

    if outbox_enabled:
        outbox_status = get_or_create_outbox_record(
            db_path=db_path,
            send_key=send_key,
            job_id=job_id,
            recipient=to,
            subject_hash=subject_hash,
        )
        if outbox_status == "sent":
            return {"sent": True, "skipped": True, "send_key": send_key}

    try:
        send_fn = send_email_fn or resolve_mail_send_callable()
        provider_response = send_fn(to=to, subject=subject, html=html)
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


@retry(stop=stop_after_attempt(3))  # type: ignore[untyped-decorator]
def send_email(to: str, subject: str, html: str, **kwargs: Any) -> Dict[str, Any]:
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
        error_msg = "EMAIL_SENDER 환경변수가 설정되지 않았습니다. " "발신자 이메일 주소를 설정해주세요."
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
        return cast(Dict[str, Any], response)

    except Exception as e:
        error_msg = f"Postmark 이메일 발송 실패: {str(e)}"
        logging.error(error_msg)
        raise RuntimeError(error_msg)


def check_email_configuration() -> Dict[str, bool]:
    """이메일 설정 상태를 확인합니다."""
    try:
        from newsletter_core.public.settings import validate_email_config

        return cast(Dict[str, bool], validate_email_config())
    except (ImportError, AttributeError):
        # Fallback 로직
        token, from_email = _get_email_config()

        return {
            "postmark_token_configured": bool(
                token and token not in _POSTMARK_TOKEN_PLACEHOLDERS
            ),
            "from_email_configured": bool(
                from_email
                and from_email != "noreply@yourdomain.com"
                and from_email != "your_verified_email@yourdomain.com"
            ),
            "ready": bool(
                token
                and from_email
                and token not in _POSTMARK_TOKEN_PLACEHOLDERS
                and from_email
                not in ["noreply@yourdomain.com", "your_verified_email@yourdomain.com"]
            ),
        }


def send_test_email(to: str) -> Dict[str, Any]:
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

    return cast(
        Dict[str, Any],
        send_email(to=to, subject="Newsletter Generator 테스트 이메일", html=test_html),
    )
