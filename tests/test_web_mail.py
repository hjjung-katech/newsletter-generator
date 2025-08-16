import os
import unittest
from unittest.mock import patch

import pytest

from web import mail as web_mail


@pytest.mark.unit
class TestWebMail(unittest.TestCase):
    @patch("web.mail.send_email")
    def test_send_test_email_success(self, mock_send_email):
        mock_send_email.return_value = True
        result = web_mail.send_test_email("test@example.com")
        self.assertTrue(result)
        mock_send_email.assert_called_once()

    @patch("web.mail.send_email")
    def test_send_test_email_failure(self, mock_send_email):
        mock_send_email.return_value = False
        result = web_mail.send_test_email("test@example.com")
        self.assertFalse(result)

    def test_check_email_configuration_complete(self):
        with patch.dict(
            os.environ,
            {"POSTMARK_SERVER_TOKEN": "test-token", "EMAIL_SENDER": "test@example.com"},
        ):
            config = web_mail.check_email_configuration()
            self.assertTrue(config["postmark_token_configured"])
            self.assertTrue(config["from_email_configured"])
            self.assertTrue(config["ready"])

    @patch("newsletter.config_manager.config_manager.validate_email_config")
    @patch("web.mail._get_email_config")
    def test_check_email_configuration_incomplete_token(
        self, mock_get_config, mock_validate
    ):
        # config_manager가 ImportError를 일으키도록 설정
        mock_validate.side_effect = ImportError
        # _get_email_config가 빈 토큰을 반환하도록 설정
        mock_get_config.return_value = (None, "test@example.com")

        config = web_mail.check_email_configuration()
        self.assertFalse(config["postmark_token_configured"])
        self.assertTrue(config["from_email_configured"])
        self.assertFalse(config["ready"])

    @patch("newsletter.config_manager.config_manager.validate_email_config")
    @patch("web.mail._get_email_config")
    def test_check_email_configuration_incomplete_sender(
        self, mock_get_config, mock_validate
    ):
        # config_manager가 ImportError를 일으키도록 설정
        mock_validate.side_effect = ImportError
        # _get_email_config가 빈 이메일을 반환하도록 설정
        mock_get_config.return_value = ("test-token", None)

        config = web_mail.check_email_configuration()
        self.assertTrue(config["postmark_token_configured"])
        self.assertFalse(config["from_email_configured"])
        self.assertFalse(config["ready"])
