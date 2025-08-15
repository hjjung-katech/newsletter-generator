# -*- coding: utf-8 -*-
"""
이메일 및 로컬 파일 전송(Delivery) 기능 통합 테스트
- Postmark API를 이용한 이메일 발송 기능 검증 (모킹 및 실제)
- 로컬 파일 저장 기능 검증
- 설정 및 예외 처리 검증
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import pytest

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from newsletter import config
from newsletter import deliver as news_deliver

@pytest.fixture
def email_data():
    """테스트용 이메일 데이터를 제공하는 Fixture"""
    return {
        "to_email": "test@example.com",
        "subject": "Newsletter Generator 테스트",
        "html_content": "<html><body><h1>테스트</h1></body></html>"
    }

@pytest.mark.mock_api
@patch("newsletter.deliver.requests.post")
def test_send_email_success(mock_post, email_data):
    """이메일 발송 성공 케이스 테스트 (모킹)"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"MessageID": "test-message-id"}
    mock_post.return_value = mock_response

    with patch.object(config, "POSTMARK_SERVER_TOKEN", "test-token"), \
         patch.object(config, "EMAIL_SENDER", "sender@example.com"):
        result = news_deliver.send_email(**email_data)

    assert result is True
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[1]["headers"]["X-Postmark-Server-Token"] == "test-token"
    assert call_args[1]["json"]["To"] == email_data["to_email"]
    assert call_args[1]["json"]["From"] == "sender@example.com"

@pytest.mark.mock_api
@patch("newsletter.deliver.requests.post")
def test_send_email_failure(mock_post, email_data):
    """이메일 발송 실패 케이스 테스트 (모킹)"""
    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_response.text = "Invalid email address"
    mock_post.return_value = mock_response

    with patch.object(config, "POSTMARK_SERVER_TOKEN", "test-token"), \
         patch.object(config, "EMAIL_SENDER", "sender@example.com"):
        result = news_deliver.send_email(**email_data)

    assert result is False

@pytest.mark.unit
def test_send_email_no_token_simulation(email_data):
    """Postmark 토큰이 없을 때 시뮬레이션 모드가 정상 동작하는지 테스트"""
    with patch.object(config, "POSTMARK_SERVER_TOKEN", None):
        result = news_deliver.send_email(**email_data)
    assert result is True

@pytest.mark.mock_api
@patch("newsletter.deliver.requests.post", side_effect=Exception("Network error"))
def test_send_email_network_error(mock_post, email_data):
    """네트워크 오류 발생 시 실패 처리 테스트 (모킹)"""
    with patch.object(config, "POSTMARK_SERVER_TOKEN", "test-token"), \
         patch.object(config, "EMAIL_SENDER", "sender@example.com"):
        result = news_deliver.send_email(**email_data)
    assert result is False

@pytest.mark.unit
def test_save_locally(tmp_path):
    """뉴스레터를 로컬 파일로 저장하는 기능 테스트"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    filename_base = "test_newsletter"
    html_content = "<html><body>Test</body></html>"

    # HTML 저장 테스트
    result_html = news_deliver.save_locally(html_content, filename_base, "html", str(output_dir))
    html_file = output_dir / f"{filename_base}.html"
    assert result_html is True
    assert html_file.exists()
    assert html_file.read_text(encoding="utf-8") == html_content

    # Markdown 저장 테스트
    result_md = news_deliver.save_locally(html_content, filename_base, "md", str(output_dir))
    md_file = output_dir / f"{filename_base}.md"
    assert result_md is True
    assert md_file.exists()
    assert "Test" in md_file.read_text(encoding="utf-8")

@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("POSTMARK_SERVER_TOKEN"), reason="POSTMARK_SERVER_TOKEN is not set")
def test_real_email_sending():
    """실제 Postmark API를 이용한 이메일 발송 통합 테스트"""
    test_recipient = os.getenv("TEST_EMAIL_RECIPIENT")
    if not test_recipient:
        pytest.skip("TEST_EMAIL_RECIPIENT is not set")

    subject = f"Newsletter Generator 실제 통합 테스트 - {os.environ.get('GENERATION_DATE', '')}"
    content = "<h1>실제 이메일 테스트</h1><p>이 이메일은 통합 테스트에 의해 발송되었습니다.</p>"

    result = news_deliver.send_email(to_email=test_recipient, subject=subject, html_content=content)
    assert result is True, "실제 이메일 발송에 실패했습니다."