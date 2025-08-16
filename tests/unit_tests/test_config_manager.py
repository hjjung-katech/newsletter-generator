import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from newsletter.config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    """ConfigManager 테스트"""

    def setUp(self):
        """각 테스트 전 초기화"""
        ConfigManager.reset_for_testing()

    def test_singleton_pattern(self):
        """싱글톤 패턴 테스트"""
        manager1 = ConfigManager()
        manager2 = ConfigManager()
        self.assertIs(manager1, manager2)

    def test_environment_variables_loading(self):
        """환경 변수 로딩 테스트"""
        test_env = {
            "EMAIL_SENDER": "test@example.com",
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "GEMINI_API_KEY": "test-gemini-key-1234567890123456",
            "SERPER_API_KEY": "test-serper-key-1234567890123456",
        }

        ConfigManager.reset_for_testing(test_env)
        manager = ConfigManager()
        self.assertEqual(manager.EMAIL_SENDER, "test@example.com")
        self.assertEqual(
            manager.POSTMARK_SERVER_TOKEN, "test-postmark-token-1234567890"
        )
        self.assertEqual(manager.GEMINI_API_KEY, "test-gemini-key-1234567890123456")

    def test_email_compatibility_fallback(self):
        """이메일 설정 테스트 - EMAIL_SENDER가 올바르게 설정되는지 확인"""
        # 정상적인 이메일 설정 테스트
        test_env = {
            "email_sender": "test@example.com",  # 명시적으로 EMAIL_SENDER 설정
            "serper_api_key": "test-serper-key-1234567890123456",
            "postmark_server_token": "test-postmark-token-1234567890",
            "openai_api_key": "sk-test-openai-key-1234567890123456",
        }

        ConfigManager.reset_for_testing(test_env)
        manager = ConfigManager()
        # EMAIL_SENDER가 올바르게 설정되어야 함
        self.assertEqual(manager.EMAIL_SENDER, "test@example.com")

    def test_email_sender_priority(self):
        """EMAIL_SENDER 우선순위 테스트"""
        test_env = {
            "EMAIL_SENDER": "new@example.com",
            "POSTMARK_FROM_EMAIL": "old@example.com",
            "SERPER_API_KEY": "test-serper-key-1234567890123456",
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "OPENAI_API_KEY": "sk-test-openai-key-1234567890123456",
        }

        ConfigManager.reset_for_testing(test_env)
        manager = ConfigManager()
        self.assertEqual(manager.EMAIL_SENDER, "new@example.com")

    def test_load_config_file_not_found(self):
        """존재하지 않는 설정 파일 테스트"""
        manager = ConfigManager()
        config = manager.load_config_file("nonexistent.yml")
        self.assertEqual(config, {})

    @patch(
        "builtins.open",
        mock_open(
            read_data="""
llm_settings:
  default_provider: "gemini"
  models:
    keyword_generation:
      provider: "gemini"
      model: "gemini-1.5-pro"
"""
        ),
    )
    @patch("pathlib.Path.exists", return_value=True)
    def test_load_config_file_success(self, mock_exists):
        """설정 파일 로딩 성공 테스트"""
        manager = ConfigManager()
        config = manager.load_config_file("test.yml")

        self.assertIn("llm_settings", config)
        self.assertEqual(config["llm_settings"]["default_provider"], "gemini")

    def test_get_llm_config_default(self):
        """기본 LLM 설정 반환 테스트"""
        manager = ConfigManager()
        with patch.object(manager, "load_config_file", return_value={}):
            llm_config = manager.get_llm_config()

        self.assertEqual(llm_config["default_provider"], "gemini")
        self.assertIn("models", llm_config)
        self.assertIn("keyword_generation", llm_config["models"])

    def test_get_newsletter_settings_default(self):
        """기본 뉴스레터 설정 테스트"""
        manager = ConfigManager()
        with patch.object(manager, "load_config_file", return_value={}):
            settings = manager.get_newsletter_settings()

        self.assertEqual(settings["newsletter_title"], "주간 산업 동향 뉴스 클리핑")
        self.assertEqual(settings["editor_title"], "편집자")

    def test_get_newsletter_settings_with_config(self):
        """설정 파일이 있는 경우 뉴스레터 설정 테스트"""
        manager = ConfigManager()
        config_data = {
            "newsletter_settings": {
                "newsletter_title": "Custom Newsletter",
                "editor_name": "Custom Editor",
            }
        }

        with patch.object(manager, "load_config_file", return_value=config_data):
            settings = manager.get_newsletter_settings()

        self.assertEqual(settings["newsletter_title"], "Custom Newsletter")
        self.assertEqual(settings["editor_name"], "Custom Editor")
        # 기본값은 유지되어야 함
        self.assertEqual(settings["editor_title"], "편집자")

    def test_get_scoring_weights_default(self):
        """기본 스코어링 가중치 테스트"""
        manager = ConfigManager()
        with patch.object(manager, "load_config_file", return_value={}):
            weights = manager.get_scoring_weights()

        expected_keys = {"relevance", "impact", "novelty", "source_tier", "recency"}
        self.assertEqual(set(weights.keys()), expected_keys)
        self.assertAlmostEqual(sum(weights.values()), 1.0)

    def test_get_scoring_weights_invalid_sum(self):
        """잘못된 가중치 합계 테스트"""
        manager = ConfigManager()
        config_data = {
            "scoring": {
                "relevance": 0.5,
                "impact": 0.5,  # 합계가 1.0이 아님
                "novelty": 0.5,
                "source_tier": 0.5,
                "recency": 0.5,
            }
        }

        with patch.object(manager, "load_config_file", return_value=config_data):
            weights = manager.get_scoring_weights()

        # 기본값이 반환되어야 함
        self.assertAlmostEqual(sum(weights.values()), 1.0)

    def test_get_major_news_sources(self):
        """주요 언론사 목록 테스트"""
        manager = ConfigManager()
        sources = manager.get_major_news_sources()

        self.assertIn("tier1", sources)
        self.assertIn("tier2", sources)
        self.assertIn("조선일보", sources["tier1"])
        self.assertIn("뉴시스", sources["tier2"])

    def test_validate_email_config_valid(self):
        """유효한 이메일 설정 검증 테스트"""
        test_env = {
            "POSTMARK_SERVER_TOKEN": "valid-postmark-token-1234567890",
            "EMAIL_SENDER": "valid@example.com",
            "SERPER_API_KEY": "test-serper-key-1234567890123456",
            "OPENAI_API_KEY": "sk-test-openai-key-1234567890123456",
        }

        ConfigManager.reset_for_testing(test_env)
        manager = ConfigManager()
        validation = manager.validate_email_config()

        self.assertTrue(validation["postmark_token_configured"])
        self.assertTrue(validation["from_email_configured"])
        self.assertTrue(validation["ready"])

    def test_validate_email_config_invalid(self):
        """무효한 이메일 설정 검증 테스트"""
        test_env = {
            "POSTMARK_SERVER_TOKEN": "your_postmark_server_token_here",
            "EMAIL_SENDER": "noreply@yourdomain.com",
            "SERPER_API_KEY": "test-serper-key-1234567890123456",
            "OPENAI_API_KEY": "sk-test-openai-key-1234567890123456",
        }

        ConfigManager.reset_for_testing(test_env)
        manager = ConfigManager()
        validation = manager.validate_email_config()

        self.assertFalse(validation["postmark_token_configured"])
        self.assertFalse(validation["from_email_configured"])
        self.assertFalse(validation["ready"])

    def test_config_caching(self):
        """설정 파일 캐싱 테스트"""
        manager = ConfigManager()

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data="test: value")) as mock_file,
        ):
            # 첫 번째 호출
            config1 = manager.load_config_file("test.yml")
            # 두 번째 호출
            config2 = manager.load_config_file("test.yml")

            # 캐시에서 가져왔으므로 파일은 한 번만 열려야 함
            mock_file.assert_called_once()
            self.assertEqual(config1, config2)

    def test_reset_for_testing(self):
        """테스트용 리셋 기능 테스트"""
        # 첫 번째 인스턴스 생성
        manager1 = ConfigManager()

        # 리셋 후 새 인스턴스 생성
        ConfigManager.reset_for_testing()
        manager2 = ConfigManager()

        # 다른 인스턴스여야 함
        self.assertIsNot(manager1, manager2)


if __name__ == "__main__":
    unittest.main()
