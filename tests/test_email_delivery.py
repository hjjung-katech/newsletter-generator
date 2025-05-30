"""
이메일 발송 기능 테스트 모듈

이 모듈은 Newsletter Generator의 Postmark 이메일 발송 기능을 테스트합니다.
실제 이메일 발송과 모킹된 테스트를 모두 포함합니다.

테스트 분류:
- @pytest.mark.unit: API 호출 없는 순수 단위 테스트
- @pytest.mark.mock_api: Mock을 사용한 API 테스트 (GitHub Actions 안전)
- @pytest.mark.integration: 실제 API 호출 테스트 (수동 실행 권장)
"""

import os

# 프로젝트 루트를 Python 경로에 추가
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pytest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from newsletter import config
from newsletter import deliver as news_deliver


class TestEmailDelivery(unittest.TestCase):
    """이메일 발송 기능 테스트 클래스"""

    def setUp(self):
        """테스트 설정"""
        self.test_email = "test@example.com"  # 실제 이메일 주소 대신 테스트용 주소 사용
        self.test_subject = "Newsletter Generator 테스트"
        self.test_html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>테스트 이메일</title></head>
        <body>
            <h1>테스트 이메일입니다</h1>
            <p>이것은 Newsletter Generator의 이메일 발송 테스트입니다.</p>
        </body>
        </html>
        """

    @pytest.mark.mock_api
    @patch("newsletter.deliver.requests.post")
    def test_send_email_success(self, mock_post):
        """이메일 발송 성공 테스트 (모킹) - GitHub Actions 안전"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "To": self.test_email,
            "SubmittedAt": "2025-01-26T10:00:00Z",
            "MessageID": "test-message-id",
            "ErrorCode": 0,
            "Message": "OK",
        }
        mock_post.return_value = mock_response

        # Mock config values
        with (
            patch.object(config, "POSTMARK_SERVER_TOKEN", "test-token"),
            patch.object(config, "EMAIL_SENDER", "test@example.com"),
        ):

            result = news_deliver.send_email(
                to_email=self.test_email,
                subject=self.test_subject,
                html_content=self.test_html_content,
            )

        # Verify the result
        self.assertTrue(result)

        # Verify the API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Check URL
        self.assertEqual(call_args[0][0], "https://api.postmarkapp.com/email")

        # Check headers
        headers = call_args[1]["headers"]
        self.assertEqual(headers["X-Postmark-Server-Token"], "test-token")
        self.assertEqual(headers["Content-Type"], "application/json")

        # Check payload
        payload = call_args[1]["json"]
        self.assertEqual(payload["To"], self.test_email)
        self.assertEqual(payload["From"], "test@example.com")
        self.assertEqual(payload["Subject"], self.test_subject)
        self.assertIn("테스트 이메일입니다", payload["HtmlBody"])

    @pytest.mark.mock_api
    @patch("newsletter.deliver.requests.post")
    def test_send_email_failure(self, mock_post):
        """이메일 발송 실패 테스트 (모킹) - GitHub Actions 안전"""
        # Mock failed response
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.text = "Invalid email address"
        mock_post.return_value = mock_response

        with (
            patch.object(config, "POSTMARK_SERVER_TOKEN", "test-token"),
            patch.object(config, "EMAIL_SENDER", "test@example.com"),
        ):

            result = news_deliver.send_email(
                to_email="invalid-email",
                subject=self.test_subject,
                html_content=self.test_html_content,
            )

        # Verify the result
        self.assertFalse(result)

    @pytest.mark.unit
    def test_send_email_no_token(self):
        """Postmark 토큰이 없을 때 테스트 - GitHub Actions 안전"""
        with patch.object(config, "POSTMARK_SERVER_TOKEN", None):
            result = news_deliver.send_email(
                to_email=self.test_email,
                subject=self.test_subject,
                html_content=self.test_html_content,
            )

        # Should return True (simulation mode)
        self.assertTrue(result)

    @pytest.mark.mock_api
    @patch("newsletter.deliver.requests.post")
    def test_send_email_network_error(self, mock_post):
        """네트워크 오류 테스트 - GitHub Actions 안전"""
        # Mock network error
        mock_post.side_effect = Exception("Network error")

        with (
            patch.object(config, "POSTMARK_SERVER_TOKEN", "test-token"),
            patch.object(config, "EMAIL_SENDER", "test@example.com"),
        ):

            result = news_deliver.send_email(
                to_email=self.test_email,
                subject=self.test_subject,
                html_content=self.test_html_content,
            )

        # Verify the result
        self.assertFalse(result)

    @pytest.mark.unit
    def test_html_content_cleaning(self):
        """HTML 내용 정리 기능 테스트 - GitHub Actions 안전"""
        # HTML with markers that should be cleaned
        dirty_html = """
        <html>
        <body>
            <h1>테스트</h1>
            <!-- HTML_MARKER_START -->
            <p>이 부분은 정리되어야 합니다</p>
            <!-- HTML_MARKER_END -->
            <p>이 부분은 유지되어야 합니다</p>
        </body>
        </html>
        """

        with patch.object(config, "POSTMARK_SERVER_TOKEN", None):
            # This will trigger the cleaning function
            result = news_deliver.send_email(
                to_email=self.test_email,
                subject=self.test_subject,
                html_content=dirty_html,
            )

        # Should still return True (simulation mode)
        self.assertTrue(result)

    @pytest.mark.unit
    def test_email_content_encoding(self):
        """이메일 내용 인코딩 테스트 - GitHub Actions 안전"""
        korean_content = """
        <!DOCTYPE html>
        <html>
        <head><title>한글 테스트</title></head>
        <body>
            <h1>안녕하세요! 🇰🇷</h1>
            <p>한글과 이모지가 포함된 테스트입니다. ✅📧</p>
            <p>특수문자: &lt;&gt;&amp;"'</p>
        </body>
        </html>
        """

        with patch.object(config, "POSTMARK_SERVER_TOKEN", None):
            result = news_deliver.send_email(
                to_email=self.test_email,
                subject="한글 제목 테스트 📧",
                html_content=korean_content,
            )

        self.assertTrue(result)

    @pytest.mark.unit
    def test_email_with_existing_html_file(self):
        """기존 HTML 파일을 사용한 이메일 테스트 - GitHub Actions 안전"""
        # 임시 HTML 파일 생성
        test_html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>테스트 뉴스레터</title></head>
        <body>
            <h1>테스트 뉴스레터</h1>
            <p>이것은 기존 HTML 파일을 사용한 이메일 테스트입니다.</p>
            <div class="article">
                <h2>AI 기술 동향</h2>
                <p>최신 AI 기술 동향에 대한 내용입니다.</p>
            </div>
        </body>
        </html>
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", delete=False, encoding="utf-8"
        ) as f:
            f.write(test_html_content)
            temp_html_path = f.name

        try:
            # CLI 명령어 시뮬레이션
            from unittest.mock import patch

            from newsletter.cli import test_email

            with patch("newsletter.deliver.send_email") as mock_send:
                mock_send.return_value = True

                # test_email 함수 직접 호출 (CLI 대신)
                import typer
                from typer.testing import CliRunner

                from newsletter.cli import app

                runner = CliRunner()
                result = runner.invoke(
                    app,
                    [
                        "test-email",
                        "--to",
                        self.test_email,
                        "--template",
                        temp_html_path,
                        "--subject",
                        "기존 HTML 파일 테스트",
                        "--dry-run",
                    ],
                )

                # 결과 검증
                self.assertEqual(result.exit_code, 0)
                self.assertIn("Template loaded successfully", result.stdout)
                self.assertIn("DRY RUN MODE", result.stdout)
                self.assertIn(str(len(test_html_content)), result.stdout)

        finally:
            # 임시 파일 정리
            os.unlink(temp_html_path)

    @pytest.mark.unit
    def test_email_with_nonexistent_template(self):
        """존재하지 않는 템플릿 파일 처리 테스트 - GitHub Actions 안전"""
        from typer.testing import CliRunner

        from newsletter.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "test-email",
                "--to",
                self.test_email,
                "--template",
                "nonexistent_file.html",
                "--dry-run",
            ],
        )

        # 결과 검증
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Template file not found", result.stdout)
        self.assertIn("Using default test content instead", result.stdout)

    @pytest.mark.unit
    def test_email_dry_run_mode(self):
        """Dry run 모드 테스트 - GitHub Actions 안전"""
        from typer.testing import CliRunner

        from newsletter.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "test-email",
                "--to",
                self.test_email,
                "--subject",
                "Dry Run 테스트",
                "--dry-run",
            ],
        )

        # 결과 검증
        self.assertEqual(result.exit_code, 0)
        self.assertIn("DRY RUN MODE", result.stdout)
        self.assertIn("실제 이메일은 발송되지 않습니다", result.stdout)
        self.assertIn("수신자: " + self.test_email, result.stdout)
        self.assertIn("제목: Dry Run 테스트", result.stdout)

    @pytest.mark.unit
    def test_email_config_validation(self):
        """이메일 설정 검증 테스트 - GitHub Actions 안전"""
        from unittest.mock import patch

        from typer.testing import CliRunner

        from newsletter.cli import app

        # POSTMARK_SERVER_TOKEN이 없는 경우 테스트
        with patch("newsletter.config.POSTMARK_SERVER_TOKEN", None):
            runner = CliRunner()
            result = runner.invoke(
                app, ["test-email", "--to", self.test_email, "--dry-run"]
            )

            self.assertEqual(result.exit_code, 0)
            # Rich 색상 태그나 이모지와 상관없이 핵심 메시지만 확인
            self.assertIn("POSTMARK_SERVER_TOKEN", result.stdout)
            self.assertIn("설정되지 않았습니다", result.stdout)

    @pytest.mark.unit
    def test_email_with_real_newsletter_file(self):
        """실제 뉴스레터 파일을 사용한 테스트 - GitHub Actions 안전"""
        import glob

        # output 디렉토리에서 실제 HTML 파일 찾기
        html_files = glob.glob("output/*.html")
        if not html_files:
            self.skipTest("테스트할 HTML 파일이 없습니다")

        # 가장 최근 파일 선택
        latest_file = max(html_files, key=os.path.getctime)

        from typer.testing import CliRunner

        from newsletter.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "test-email",
                "--to",
                self.test_email,
                "--template",
                latest_file,
                "--subject",
                "실제 뉴스레터 파일 테스트",
                "--dry-run",
            ],
        )

        # 결과 검증
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Template loaded successfully", result.stdout)
        self.assertIn("DRY RUN MODE", result.stdout)

        # 파일 크기가 합리적인지 확인 (최소 1000자 이상)
        file_size = os.path.getsize(latest_file)
        self.assertGreater(file_size, 1000, "뉴스레터 파일이 너무 작습니다")


class TestEmailIntegration(unittest.TestCase):
    """이메일 통합 테스트 클래스 (실제 API 호출)"""

    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("POSTMARK_SERVER_TOKEN"),
        reason="POSTMARK_SERVER_TOKEN not set - skipping integration test",
    )
    def test_real_email_sending(self):
        """실제 이메일 발송 테스트 (통합 테스트)

        주의: 이 테스트는 실제 Postmark API를 호출하며,
        POSTMARK_SERVER_TOKEN과 EMAIL_SENDER가 설정되어 있어야 합니다.
        또한 TEST_EMAIL_RECIPIENT 환경변수로 수신자를 지정해야 합니다.

        GitHub Actions에서는 자동으로 스킵됩니다.
        """
        test_recipient = os.getenv("TEST_EMAIL_RECIPIENT")
        if not test_recipient:
            self.skipTest("TEST_EMAIL_RECIPIENT not set - skipping real email test")

        test_subject = "Newsletter Generator 실제 테스트 - 자동화된 테스트"
        test_content = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <title>실제 이메일 테스트</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f8ff; padding: 20px; border-radius: 5px; }}
                .content {{ margin: 20px 0; }}
                .footer {{ font-size: 0.9em; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🧪 Newsletter Generator 실제 이메일 테스트</h1>
            </div>
            <div class="content">
                <p>이것은 Newsletter Generator의 실제 이메일 발송 기능을 테스트하는 자동화된 테스트입니다.</p>
                <p><strong>테스트 시간:</strong> {os.environ.get('GENERATION_DATE', 'Unknown')} {os.environ.get('GENERATION_TIMESTAMP', 'Unknown')}</p>
                <p><strong>수신자:</strong> {test_recipient}</p>
                <p>이 이메일을 받으셨다면 Postmark 통합이 정상적으로 작동하고 있습니다! ✅</p>
            </div>
            <div class="footer">
                <p>이 메시지는 자동화된 테스트에 의해 생성되었습니다.</p>
            </div>
        </body>
        </html>
        """

        result = news_deliver.send_email(
            to_email=test_recipient, subject=test_subject, html_content=test_content
        )

        self.assertTrue(result, "실제 이메일 발송이 실패했습니다")
        print(f"✅ 실제 이메일이 {test_recipient}로 성공적으로 발송되었습니다")


def create_test_html_file():
    """테스트용 HTML 파일 생성 유틸리티"""
    test_html = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>테스트 뉴스레터</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .article { margin-bottom: 20px; padding: 15px; border-left: 3px solid #007bff; }
            .title { font-size: 1.2em; font-weight: bold; color: #333; }
            .summary { margin-top: 10px; color: #666; }
        </style>
    </head>
    <body>
        <h1>📰 주간 기술 뉴스 클리핑</h1>
        
        <div class="article">
            <div class="title">AI 기술의 최신 동향</div>
            <div class="summary">
                인공지능 기술이 빠르게 발전하면서 다양한 산업 분야에 적용되고 있습니다.
                특히 자연어 처리와 컴퓨터 비전 분야에서 괄목할 만한 성과를 보이고 있습니다.
            </div>
        </div>
        
        <div class="article">
            <div class="title">클라우드 컴퓨팅의 미래</div>
            <div class="summary">
                클라우드 서비스 시장이 지속적으로 성장하고 있으며,
                엣지 컴퓨팅과 서버리스 아키텍처가 주목받고 있습니다.
            </div>
        </div>
        
        <div class="article">
            <div class="title">사이버 보안 트렌드</div>
            <div class="summary">
                제로 트러스트 보안 모델과 AI 기반 위협 탐지 시스템이
                차세대 보안 솔루션으로 각광받고 있습니다.
            </div>
        </div>
        
        <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666;">
            <p>이 뉴스레터는 Newsletter Generator에 의해 자동 생성되었습니다.</p>
        </footer>
    </body>
    </html>
    """

    # Create temporary file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(test_html)
        return f.name


if __name__ == "__main__":
    # 환경 변수 설정 (테스트용)
    os.environ["GENERATION_DATE"] = "2025-01-26"
    os.environ["GENERATION_TIMESTAMP"] = "10:00:00"

    # 테스트 실행
    unittest.main(verbosity=2)
