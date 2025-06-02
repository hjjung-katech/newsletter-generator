import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from newsletter.config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    """ConfigManager 클래스 테스트"""

    def setUp(self):
        """테스트 전 설정"""
        # 싱글톤 인스턴스 초기화
        ConfigManager._instance = None
        ConfigManager._config_cache = {}

    def test_singleton_pattern(self):
        """싱글톤 패턴 테스트"""
        manager1 = ConfigManager()
        manager2 = ConfigManager()
        self.assertIs(manager1, manager2)

    @patch.dict(
        os.environ,
        {
            "EMAIL_SENDER": "test@example.com",
            "POSTMARK_SERVER_TOKEN": "test_token",
            "GEMINI_API_KEY": "test_gemini_key",
        },
    )
    def test_environment_variables_loading(self):
        """환경 변수 로딩 테스트"""
        manager = ConfigManager()
        self.assertEqual(manager.EMAIL_SENDER, "test@example.com")
        self.assertEqual(manager.POSTMARK_SERVER_TOKEN, "test_token")
        self.assertEqual(manager.GEMINI_API_KEY, "test_gemini_key")

    @patch.dict(os.environ, {"POSTMARK_FROM_EMAIL": "old@example.com"}, clear=True)
    def test_email_compatibility_fallback(self):
        """이메일 호환성 fallback 테스트"""
        manager = ConfigManager()
        self.assertEqual(manager.EMAIL_SENDER, "old@example.com")

    @patch.dict(
        os.environ,
        {"EMAIL_SENDER": "new@example.com", "POSTMARK_FROM_EMAIL": "old@example.com"},
    )
    def test_email_sender_priority(self):
        """EMAIL_SENDER 우선순위 테스트"""
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

        expected_keys = {"recency", "relevance", "credibility", "diversity"}
        self.assertEqual(set(weights.keys()), expected_keys)
        self.assertAlmostEqual(sum(weights.values()), 1.0)

    def test_get_scoring_weights_invalid_sum(self):
        """잘못된 가중치 합계 테스트"""
        manager = ConfigManager()
        config_data = {
            "scoring": {
                "recency": 0.5,
                "relevance": 0.5,  # 합계가 1.0이 아님
                "credibility": 0.5,
                "diversity": 0.5,
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

    @patch.dict(
        os.environ,
        {"POSTMARK_SERVER_TOKEN": "valid_token", "EMAIL_SENDER": "valid@example.com"},
    )
    def test_validate_email_config_valid(self):
        """유효한 이메일 설정 검증 테스트"""
        manager = ConfigManager()
        validation = manager.validate_email_config()

        self.assertTrue(validation["postmark_token_configured"])
        self.assertTrue(validation["from_email_configured"])
        self.assertTrue(validation["ready"])

    @patch.dict(
        os.environ,
        {
            "POSTMARK_SERVER_TOKEN": "your_postmark_server_token_here",
            "EMAIL_SENDER": "noreply@yourdomain.com",
        },
    )
    def test_validate_email_config_invalid(self):
        """무효한 이메일 설정 검증 테스트"""
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


if __name__ == "__main__":
    unittest.main()
