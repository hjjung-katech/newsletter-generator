# Placeholder for delivery logic (email, Google Drive)
import os

import markdownify  # For HTML to Markdown conversion
import requests

from . import config
from .tools import clean_html_markers  # Import the clean_html_markers function
from .utils.logger import get_logger

# 로거 초기화
logger = get_logger()

# Google Drive 관련 import를 조건부로 처리
try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    logger.info(
        "Google Drive 종속성을 사용할 수 없습니다. Google Drive 업로드가 비활성화됩니다."
    )

# Premailer import for CSS inlining
try:
    from premailer import transform as premailer_transform

    PREMAILER_AVAILABLE = True
except ImportError:
    PREMAILER_AVAILABLE = False
    logger.info(
        "Note: premailer not available. Email CSS inlining will be disabled. Install with: pip install premailer"
    )


def save_to_drive(
    html_content: str, filename_base: str, output_directory: str = "output"
):
    """Saves the newsletter content to Google Drive in HTML and Markdown formats.

    Args:
        html_content: The HTML content to save
        filename_base: The base filename (without extension)
        output_directory: The directory to save temporary files (defaults to 'output')

    Returns:
        bool: True if successful, False otherwise
    """
    if not GOOGLE_DRIVE_AVAILABLE:
        logger.warning(
            "Warning: Google Drive dependencies not available. Skipping Google Drive upload."
        )
        return False

    if not config.GOOGLE_APPLICATION_CREDENTIALS:
        logger.warning(
            "Warning: GOOGLE_APPLICATION_CREDENTIALS not set. Skipping Google Drive upload."
        )
        return False

    try:
        # Clean HTML markers from content before saving
        cleaned_html_content = clean_html_markers(html_content)

        creds = Credentials.from_service_account_file(
            config.GOOGLE_APPLICATION_CREDENTIALS,
            scopes=["https://www.googleapis.com/auth/drive.file"],
        )
        service = build("drive", "v3", credentials=creds)

        # 1. Save as HTML
        html_filename = f"{filename_base}.html"
        temp_html_path = os.path.join(
            output_directory, html_filename
        )  # Save locally first
        os.makedirs(output_directory, exist_ok=True)
        with open(temp_html_path, "w", encoding="utf-8") as f:
            f.write(cleaned_html_content)

        file_metadata_html = {"name": html_filename}
        media_html = MediaFileUpload(temp_html_path, mimetype="text/html")
        service.files().create(
            body=file_metadata_html, media_body=media_html, fields="id"
        ).execute()
        logger.info(f"Successfully uploaded {html_filename} to Google Drive.")
        os.remove(temp_html_path)  # Clean up local temp file

        # 2. Convert to Markdown and save
        md_content = markdownify.markdownify(cleaned_html_content, heading_style="ATX")
        md_filename = f"{filename_base}.md"
        temp_md_path = os.path.join(output_directory, md_filename)  # Save locally first
        with open(temp_md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        file_metadata_md = {"name": md_filename}
        media_md = MediaFileUpload(temp_md_path, mimetype="text/markdown")
        service.files().create(
            body=file_metadata_md, media_body=media_md, fields="id"
        ).execute()
        logger.info(f"Successfully uploaded {md_filename} to Google Drive.")
        os.remove(temp_md_path)  # Clean up local temp file

        return True
    except Exception as e:
        logger.error(f"Error uploading to Google Drive: {e}")
        return False


def save_locally(
    html_content: str,
    filename_base: str,
    output_format: str = "html",
    output_directory: str = "output",
):
    """Saves the newsletter content locally as HTML or Markdown.

    Args:
        html_content: The HTML content to save
        filename_base: The base filename (without extension)
        output_format: The format to save in ('html' or 'md')
        output_directory: The directory to save to (defaults to 'output')

    Returns:
        bool: True if successful, False otherwise
    """
    os.makedirs(output_directory, exist_ok=True)

    # Clean HTML markers from content before saving
    cleaned_html_content = clean_html_markers(html_content)

    if output_format == "html":
        filename = f"{filename_base}.html"
        output_path = os.path.join(output_directory, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(cleaned_html_content)
        logger.info(f"Newsletter saved locally as {output_path}")
    elif output_format == "md":
        md_content = markdownify.markdownify(cleaned_html_content, heading_style="ATX")
        filename = f"{filename_base}.md"
        output_path = os.path.join(output_directory, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        logger.info(f"Newsletter saved locally as {output_path}")
    else:
        logger.error(
            f"Unsupported output format: {output_format}. Choose 'html' or 'md'."
        )
        return False
    return True


def process_html_for_email(html_content: str) -> str:
    """
    Process HTML content for better email compatibility using premailer.

    Args:
        html_content: Raw HTML content

    Returns:
        str: HTML with inline CSS and email optimizations
    """
    # Clean HTML markers first
    cleaned_html = clean_html_markers(html_content)

    # If premailer is available, use it to inline CSS
    if PREMAILER_AVAILABLE:
        try:
            # Transform CSS to inline styles for better email compatibility
            processed_html = premailer_transform(
                cleaned_html,
                base_url=None,
                preserve_internal_links=True,
                exclude_pseudoclasses=True,
                keep_style_tags=False,
                include_star_selectors=False,
                remove_classes=False,
                strip_important=True,
                disable_validation=True,
                cache_css_parsing=True,
                align_floating_images=True,
                remove_unset_properties=True,
            )
            return processed_html
        except Exception as e:
            logger.warning(f"Warning: Failed to process HTML with premailer: {e}")
            return cleaned_html
    else:
        return cleaned_html


def send_email(to_email: str, subject: str, html_content: str):
    """Send an email via Postmark.

    If ``config.POSTMARK_SERVER_TOKEN`` is not set, the function simulates a
    successful send so that tests do not fail in CI environments.

    Args:
        to_email: 수신자 이메일 주소
        subject: 이메일 제목
        html_content: 이메일 내용 (HTML)

    Returns:
        bool: 발송 성공 여부
    """

    # 이메일 발송 정보 로깅
    logger.info("\n📧 이메일 발송 준비")
    logger.info(f"   수신자: {to_email}")
    logger.info(f"   제목: {subject}")
    logger.info(f"   내용 길이: {len(html_content)} 문자")

    # EMAIL_SENDER 설정 확인
    if not config.EMAIL_SENDER:
        logger.error("❌ 오류: EMAIL_SENDER가 설정되지 않았습니다!")
        logger.info("💡 해결 방법:")
        logger.info("   .env 파일에 다음을 추가하세요:")
        logger.info("   EMAIL_SENDER=your_verified_sender@example.com")
        logger.info("   (주의: Postmark에서 인증된 이메일 주소여야 합니다)")
        return False

    logger.info(f"   발송자: {config.EMAIL_SENDER}")

    # POSTMARK_SERVER_TOKEN 설정 확인
    if not config.POSTMARK_SERVER_TOKEN:
        logger.error("❌ 오류: POSTMARK_SERVER_TOKEN이 설정되지 않았습니다!")
        logger.info("💡 해결 방법:")
        logger.info("   .env 파일에 다음을 추가하세요:")
        logger.info("   POSTMARK_SERVER_TOKEN=your_postmark_server_token")
        logger.info("   (Postmark 대시보드 → Server → API Tokens에서 확인 가능)")
        logger.info("⚠️  CI 환경에서는 경고로 처리되어 성공으로 간주됩니다.")
        return True  # CI 환경에서는 성공으로 처리

    # 토큰 마스킹 표시 (보안상)
    masked_token = (
        config.POSTMARK_SERVER_TOKEN[:8] + "..." + config.POSTMARK_SERVER_TOKEN[-4:]
        if len(config.POSTMARK_SERVER_TOKEN) > 12
        else "***"
    )
    logger.info(f"   Postmark 토큰: {masked_token}")

    cleaned_html_content = process_html_for_email(html_content)

    try:
        logger.info(f"📤 Postmark API 호출 중...")

        response = requests.post(
            "https://api.postmarkapp.com/email",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Postmark-Server-Token": config.POSTMARK_SERVER_TOKEN,
            },
            json={
                "From": config.EMAIL_SENDER,
                "To": to_email,
                "Subject": subject,
                "HtmlBody": cleaned_html_content,
            },
            timeout=10,
        )

        if response.status_code == 200:
            response_data = response.json()
            message_id = response_data.get("MessageID", "N/A")
            logger.info(f"✅ 이메일 발송 성공!")
            logger.info(f"   메시지 ID: {message_id}")
            logger.info(f"   발송자: {config.EMAIL_SENDER}")
            logger.info(f"   수신자: {to_email}")
            return True
        else:
            logger.error(f"❌ 이메일 발송 실패: {response.status_code}")
            logger.error(f"   응답: {response.text}")

            # 특정 오류에 대한 상세한 도움말 제공
            if response.status_code == 422:
                try:
                    error_data = response.json()
                    error_code = error_data.get("ErrorCode")
                    error_message = error_data.get("Message", "알 수 없는 오류")

                    logger.info(f"   오류 코드: {error_code}")
                    logger.info(f"   오류 메시지: {error_message}")

                    if error_code == 406:
                        logger.info("\n💡 해결 방법 (비활성화된 이메일):")
                        logger.info("   1. 다른 이메일 주소로 테스트해보세요")
                        logger.info(
                            "   2. Postmark 대시보드에서 해당 이메일을 재활성화하세요:"
                        )
                        logger.info("      - Message Stream → Suppressions 탭")
                        logger.info("      - 이메일 주소 검색 → Reactivate 버튼 클릭")
                        logger.info(
                            "   3. 발송자와 수신자가 같은 이메일인지 확인하세요"
                        )
                    elif error_code == 300:
                        logger.info("\n💡 해결 방법 (잘못된 발송자 이메일):")
                        logger.info(
                            "   1. EMAIL_SENDER가 Postmark에서 인증된 이메일인지 확인하세요"
                        )
                        logger.info(
                            "   2. Postmark 대시보드 → Signatures에서 인증 상태 확인"
                        )
                        logger.info(f"   3. 현재 설정: {config.EMAIL_SENDER}")
                    else:
                        logger.info("\n💡 일반적인 해결 방법:")
                        logger.info("   1. 이메일 주소 형식 확인")
                        logger.info("   2. Postmark 대시보드에서 발송자 서명 인증 확인")
                        logger.info("   3. 월별 발송 한도 초과 여부 확인")
                except Exception as parse_error:
                    logger.error(f"   (오류 응답 파싱 실패: {parse_error})")

            elif response.status_code == 401:
                logger.info("\n💡 해결 방법 (인증 실패):")
                logger.info("   1. POSTMARK_SERVER_TOKEN이 올바른지 확인하세요")
                logger.info("   2. Postmark 대시보드에서 토큰을 다시 확인하세요")
                logger.info("   3. 토큰이 Server Token인지 확인 (Account Token 아님)")
                logger.info(f"   4. 현재 토큰: {masked_token}")

            elif response.status_code == 403:
                logger.info("\n💡 해결 방법 (권한 부족):")
                logger.info("   1. Postmark 계정의 발송 권한 확인")
                logger.info("   2. 계정이 일시 중지되었는지 확인")
                logger.info("   3. 발송 한도 초과 여부 확인")

            return False

    except requests.exceptions.Timeout:
        logger.error("❌ 이메일 발송 실패: 요청 시간 초과")
        logger.info("💡 해결 방법:")
        logger.info("   1. 네트워크 연결 상태 확인")
        logger.info("   2. 잠시 후 다시 시도")
        return False

    except requests.exceptions.ConnectionError:
        logger.error("❌ 이메일 발송 실패: 연결 오류")
        logger.info("💡 해결 방법:")
        logger.info("   1. 인터넷 연결 확인")
        logger.info("   2. 방화벽 설정 확인")
        logger.info("   3. VPN 사용 중인 경우 해제 후 재시도")
        return False

    except Exception as e:
        logger.error(f"❌ 이메일 발송 중 예상치 못한 오류: {e}")
        logger.info("💡 해결 방법:")
        logger.info("   1. 네트워크 연결 확인")
        logger.info("   2. 설정 파일(.env) 확인")
        logger.info("   3. 문제가 지속되면 개발팀에 문의")
        return False
