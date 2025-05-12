# Placeholder for delivery logic (email, Google Drive)
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import markdownify  # For HTML to Markdown conversion
from . import config


def save_to_drive(html_content: str, filename_base: str):
    """Saves the newsletter content to Google Drive in HTML and Markdown formats."""
    if not config.GOOGLE_APPLICATION_CREDENTIALS:
        print(
            "Warning: GOOGLE_APPLICATION_CREDENTIALS not set. Skipping Google Drive upload."
        )
        return False

    try:
        creds = Credentials.from_service_account_file(
            config.GOOGLE_APPLICATION_CREDENTIALS,
            scopes=["https://www.googleapis.com/auth/drive.file"],
        )
        service = build("drive", "v3", credentials=creds)

        # 1. Save as HTML
        html_filename = f"{filename_base}.html"
        temp_html_path = os.path.join("output", html_filename)  # Save locally first
        os.makedirs("output", exist_ok=True)
        with open(temp_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        file_metadata_html = {"name": html_filename}
        media_html = MediaFileUpload(temp_html_path, mimetype="text/html")
        service.files().create(
            body=file_metadata_html, media_body=media_html, fields="id"
        ).execute()
        print(f"Successfully uploaded {html_filename} to Google Drive.")
        os.remove(temp_html_path)  # Clean up local temp file

        # 2. Convert to Markdown and save
        md_content = markdownify.markdownify(html_content, heading_style="ATX")
        md_filename = f"{filename_base}.md"
        temp_md_path = os.path.join("output", md_filename)  # Save locally first
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


def save_locally(html_content: str, filename_base: str, output_format: str = "html"):
    """Saves the newsletter content locally as HTML or Markdown."""
    os.makedirs("output", exist_ok=True)

    if output_format == "html":
        filename = f"{filename_base}.html"
        output_path = os.path.join("output", filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"Newsletter saved locally as {output_path}")
    elif output_format == "md":
        md_content = markdownify.markdownify(html_content, heading_style="ATX")
        filename = f"{filename_base}.md"
        output_path = os.path.join("output", filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"Newsletter saved locally as {output_path}")
    else:
        print(f"Unsupported output format: {output_format}. Choose 'html' or 'md'.")
        return False
    return True


# send_email 함수는 더 이상 사용하지 않으므로 주석 처리하거나 삭제합니다.
# def send_email(to_email: str, subject: str, html_content: str):
#     if not config.SENDGRID_API_KEY:
#         print("Error: SENDGRID_API_KEY not found. Please set it in the .env file.")
#         print("Email sending skipped.")
#         return False

#     message = Mail(
#         from_email='your_verified_sendgrid_sender@example.com',
#         to_emails=to_email,
#         subject=subject,
#         html_content=html_content
#     )
#     try:
#         sg = SendGridAPIClient(config.SENDGRID_API_KEY)
#         response = sg.send(message)
#         print(f"Email sent to {to_email}! Status Code: {response.status_code}")
#         if 200 <= response.status_code < 300:
#             print("Email sent successfully via SendGrid.")
#             return True
#         else:
#             print(f"Failed to send email. Status Code: {response.status_code}")
#             print(f"Response Body: {response.body}")
#             return False
#     except Exception as e:
#         print(f"Error sending email via SendGrid: {e}")
#         return False
