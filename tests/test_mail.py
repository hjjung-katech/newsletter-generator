import os
import pytest
from unittest import mock
import sys

# Add web directory to path for importing mail module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web"))


@mock.patch("web.mail.PostmarkClient")
@mock.patch("web.mail._get_email_config")
def test_send_email_called(mock_get_config, mock_postmark_client):
    """Test that send_email calls Postmark client correctly"""
    # ConfigManager 리셋
    try:
        from newsletter.config_manager import ConfigManager

        ConfigManager.reset_for_testing()
    except ImportError:
        pass

    from web.mail import send_email

    # 모킹된 설정 반환
    mock_get_config.return_value = ("DUMMY_TOKEN", "from@example.com")

    # Mock the client instance and its emails.send method
    mock_client_instance = mock.Mock()
    mock_postmark_client.return_value = mock_client_instance

    # Call send_email
    send_email("to@example.com", "Test Subject", "<b>Test HTML Content</b>")

    # Verify that PostmarkClient was instantiated with correct token
    mock_postmark_client.assert_called_once_with(server_token="DUMMY_TOKEN")

    # Verify that emails.send was called with correct parameters
    mock_client_instance.emails.send.assert_called_once_with(
        From="from@example.com",
        To="to@example.com",
        Subject="Test Subject",
        HtmlBody="<b>Test HTML Content</b>",
    )


@mock.patch("web.mail.PostmarkClient")
def test_send_email_missing_env_vars(mock_postmark_client):
    """Test that send_email raises error when environment variables are missing"""
    from web.mail import send_email

    # 모킹된 클라이언트가 오류를 발생시키도록 설정
    mock_client_instance = mock.Mock()
    mock_postmark_client.return_value = mock_client_instance

    # PostmarkClient 초기화 시점에서 오류 발생시키기
    mock_postmark_client.side_effect = Exception("Token validation failed")

    # 환경변수가 있지만 토큰이 유효하지 않은 경우를 테스트
    # 실제로는 환경변수 부족이 아니라 토큰 검증 실패를 테스트
    with pytest.raises(RuntimeError, match="Postmark 이메일 발송 실패"):
        send_email("to@example.com", "Subject", "<b>Content</b>")


@mock.patch("web.mail.PostmarkClient")
@mock.patch("web.mail._get_email_config")
def test_send_email_with_kwargs(mock_get_config, mock_postmark_client):
    """Test that send_email passes additional kwargs to Postmark client"""
    # ConfigManager 리셋
    try:
        from newsletter.config_manager import ConfigManager

        ConfigManager.reset_for_testing()
    except ImportError:
        pass

    from web.mail import send_email

    # 모킹된 설정 반환
    mock_get_config.return_value = ("DUMMY_TOKEN", "from@example.com")

    # Mock the client instance and its emails.send method
    mock_client_instance = mock.Mock()
    mock_postmark_client.return_value = mock_client_instance

    # Call send_email with additional kwargs
    send_email(
        "to@example.com",
        "Test Subject",
        "<b>Test HTML Content</b>",
        MessageStream="broadcast",
        Tag="newsletter",
    )

    # Verify that emails.send was called with kwargs
    mock_client_instance.emails.send.assert_called_once_with(
        From="from@example.com",
        To="to@example.com",
        Subject="Test Subject",
        HtmlBody="<b>Test HTML Content</b>",
        MessageStream="broadcast",
        Tag="newsletter",
    )


@mock.patch("web.mail._get_email_config")
def test_send_email_no_token(mock_get_config):
    """Test that send_email raises error when no token is configured"""
    from web.mail import send_email

    # 설정 함수가 빈 값을 반환하도록 모킹
    mock_get_config.return_value = (None, None)

    # 토큰이 없으면 RuntimeError가 발생해야 함
    with pytest.raises(
        RuntimeError, match="POSTMARK_SERVER_TOKEN 환경변수가 설정되지 않았습니다"
    ):
        send_email("to@example.com", "Subject", "<b>Content</b>")
