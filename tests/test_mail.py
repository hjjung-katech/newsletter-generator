import os
import pytest
from unittest import mock
import sys

# Add web directory to path for importing mail module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web"))


@mock.patch("web.mail.PostmarkClient")
@mock.patch.dict(
    os.environ,
    {"POSTMARK_SERVER_TOKEN": "DUMMY_TOKEN", "POSTMARK_FROM_EMAIL": "from@example.com"},
)
def test_send_email_called(mock_postmark_client):
    """Test that send_email calls Postmark client correctly"""
    from web.mail import send_email

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


@mock.patch.dict(os.environ, {}, clear=True)
def test_send_email_missing_env_vars():
    """Test that send_email raises error when environment variables are missing"""
    from web.mail import send_email

    with pytest.raises(RuntimeError, match="Postmark env vars missing"):
        send_email("to@example.com", "Subject", "<b>Content</b>")


@mock.patch("web.mail.PostmarkClient")
@mock.patch.dict(
    os.environ,
    {"POSTMARK_SERVER_TOKEN": "DUMMY_TOKEN", "POSTMARK_FROM_EMAIL": "from@example.com"},
)
def test_send_email_with_kwargs(mock_postmark_client):
    """Test that send_email passes additional kwargs to Postmark client"""
    from web.mail import send_email

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
