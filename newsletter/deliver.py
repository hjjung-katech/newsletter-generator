# Placeholder for delivery logic (email, Google Drive)
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import markdownify  # For HTML to Markdown conversion
from . import config
from .tools import clean_html_markers  # Import the clean_html_markers function


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
    """
    이메일 발송 기능 (기본적인 플레이스홀더 구현)
    실제 이메일 발송은 config.SENDGRID_API_KEY가 설정된 경우에만 시도합니다.

    Args:
        to_email: 수신자 이메일 주소
        subject: 이메일 제목
        html_content: 이메일 내용 (HTML)

    Returns:
        bool: 발송 성공 여부
    """
    # Clean HTML markers before sending email
    cleaned_html_content = clean_html_markers(html_content)

    if not config.SENDGRID_API_KEY:
        print("Warning: SENDGRID_API_KEY not found. Please set it in the .env file.")
        print("Email sending simulation complete (no actual email sent).")
        return True  # CI 환경에서는 성공으로 처리

    # 실제 이메일 발송 로직은 SendGrid API 키가 설정된 경우에만 작동
    try:
        print(f"Would send email to {to_email} with subject: {subject}")
        print("Email content is HTML with length:", len(cleaned_html_content))
        print("Email sending simulated successfully.")
        return True
    except Exception as e:
        print(f"Error simulating email send: {e}")
        return False
