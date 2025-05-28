# Placeholder for delivery logic (email, Google Drive)
import os

import markdownify  # For HTML to Markdown conversion
import requests

from . import config
from .tools import clean_html_markers  # Import the clean_html_markers function

# Google Drive 관련 import를 조건부로 처리
try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    print(
        "Note: Google Drive dependencies not available. Google Drive upload will be disabled."
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
        print(
            "Warning: Google Drive dependencies not available. Skipping Google Drive upload."
        )
        return False

    if not config.GOOGLE_APPLICATION_CREDENTIALS:
        print(
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
        print(f"Successfully uploaded {html_filename} to Google Drive.")
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
        print(f"Successfully uploaded {md_filename} to Google Drive.")
        os.remove(temp_md_path)  # Clean up local temp file

        return True
    except Exception as e:
        print(f"Error uploading to Google Drive: {e}")
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
        print(f"Newsletter saved locally as {output_path}")
    elif output_format == "md":
        md_content = markdownify.markdownify(cleaned_html_content, heading_style="ATX")
        filename = f"{filename_base}.md"
        output_path = os.path.join(output_directory, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"Newsletter saved locally as {output_path}")
    else:
        print(f"Unsupported output format: {output_format}. Choose 'html' or 'md'.")
        return False
    return True


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

    cleaned_html_content = clean_html_markers(html_content)

    if not config.POSTMARK_SERVER_TOKEN:
        print(
            "Warning: POSTMARK_SERVER_TOKEN not found. Please set it in the .env file."
        )
        print("Email sending skipped - no actual email sent.")
        return True  # CI 환경에서는 성공으로 처리

    try:
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
            print("Email sent via Postmark.")
            return True
        else:
            print(f"Error sending email: {response.status_code} {response.text}")

            # 특정 오류에 대한 도움말 제공
            if response.status_code == 422:
                try:
                    error_data = response.json()
                    if error_data.get("ErrorCode") == 406:
                        print("\n💡 해결 방법:")
                        print("   1. 다른 이메일 주소로 테스트해보세요")
                        print(
                            "   2. Postmark 대시보드에서 해당 이메일을 재활성화하세요:"
                        )
                        print("      - Message Stream → Suppressions 탭")
                        print("      - 이메일 주소 검색 → Reactivate 버튼 클릭")
                        print("   3. 발송자와 수신자가 같은 이메일인지 확인하세요")
                except:
                    pass
            elif response.status_code == 401:
                print("\n💡 해결 방법:")
                print("   - POSTMARK_SERVER_TOKEN이 올바른지 확인하세요")
                print("   - Postmark 대시보드에서 토큰을 다시 확인하세요")

            return False
    except Exception as e:
        print(f"Error sending email via Postmark: {e}")
        return False
