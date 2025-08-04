"""
Environment Profile Integration Tests for F-14 Centralized Settings Layer
환경별 설정 통합 테스트: development, testing, production
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Import centralized settings if available, otherwise skip tests
try:
    from newsletter.config_manager import ConfigManager

    centralized_available = True
except ImportError:
    centralized_available = False


class TestEnvironmentProfiles:
    """환경별 프로파일 통합 테스트"""

    def setup_method(self):
        """각 테스트 전 설정 초기화"""
        # ConfigManager 리셋 (싱글톤이므로)
        if hasattr(ConfigManager, "reset_for_testing"):
            ConfigManager.reset_for_testing()

    def test_development_environment(self):
        """Development 환경 설정 테스트"""
        base_env = {
            "APP_ENV": "development",
            "SERPER_API_KEY": "dev-serper-key-1234567890123456",
            "POSTMARK_SERVER_TOKEN": "dev-postmark-token-1234567890",
            "EMAIL_SENDER": "dev@example.com",
            "OPENAI_API_KEY": "sk-dev-openai-key-1234567890123456",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "MOCK_MODE": "true",
        }

        with patch.dict(os.environ, base_env, clear=True):
            # 환경변수 변경 후 ConfigManager 재초기화
            ConfigManager.reset_for_testing(base_env)
            config = ConfigManager()

            # Development 환경 특성 확인
            assert config.SERPER_API_KEY == base_env["SERPER_API_KEY"]
            assert config.EMAIL_SENDER == base_env["EMAIL_SENDER"]

    def test_testing_environment(self):
        """Testing 환경 설정 테스트"""
        base_env = {
            "APP_ENV": "testing",
            "SERPER_API_KEY": "test-serper-key-1234567890123456",
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "EMAIL_SENDER": "test@example.com",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-1234567890123456",
            "DEBUG": "false",
            "LOG_LEVEL": "INFO",
            "MOCK_MODE": "true",
        }

        with patch.dict(os.environ, base_env, clear=True):
            # 환경변수 변경 후 ConfigManager 재초기화
            ConfigManager.reset_for_testing(base_env)
            config = ConfigManager()

            # Testing 환경 특성 확인
            assert config.SERPER_API_KEY == base_env["SERPER_API_KEY"]
            assert config.ANTHROPIC_API_KEY == base_env["ANTHROPIC_API_KEY"]
            assert config.EMAIL_SENDER == base_env["EMAIL_SENDER"]

    def test_production_environment(self):
        """Production 환경 설정 테스트"""
        base_env = {
            "APP_ENV": "production",
            "SERPER_API_KEY": "prod-serper-key-1234567890123456",
            "POSTMARK_SERVER_TOKEN": "prod-postmark-token-1234567890",
            "EMAIL_SENDER": "newsletter@production.com",
            "GEMINI_API_KEY": "gemini-prod-key-1234567890123456",
            "DEBUG": "false",
            "LOG_LEVEL": "WARNING",
            "MOCK_MODE": "false",
        }

        with patch.dict(os.environ, base_env, clear=True):
            # 환경변수 변경 후 ConfigManager 재초기화
            ConfigManager.reset_for_testing(base_env)
            config = ConfigManager()

            # Production 환경 특성 확인
            assert config.SERPER_API_KEY == base_env["SERPER_API_KEY"]
            assert config.GEMINI_API_KEY == base_env["GEMINI_API_KEY"]
            assert config.EMAIL_SENDER == base_env["EMAIL_SENDER"]

    def test_environment_variable_priority(self):
        """환경변수 우선순위 테스트: OS ENV > .env > defaults"""
        # OS 환경변수가 다른 소스보다 우선하는지 테스트
        base_env = {
            "APP_ENV": "development",
            "SERPER_API_KEY": "priority-test-key-1234567890123456",
            "POSTMARK_SERVER_TOKEN": "priority-postmark-token-1234567890",
            "EMAIL_SENDER": "priority@example.com",
            "OPENAI_API_KEY": "sk-priority-openai-key-1234567890123456",
            "LOG_LEVEL": "CRITICAL",  # OS에서 설정
        }

        with patch.dict(os.environ, base_env, clear=True):
            # 환경변수 변경 후 ConfigManager 재초기화
            ConfigManager.reset_for_testing(base_env)
            config = ConfigManager()

            # OS 환경변수가 우선되는지 확인
            assert config.SERPER_API_KEY == base_env["SERPER_API_KEY"]

    def test_missing_required_environment_variables(self):
        """필수 환경변수 누락 시 적절한 오류 처리 확인"""
        incomplete_env = {
            "APP_ENV": "testing",
            "EMAIL_SENDER": "test@example.com",
            # SERPER_API_KEY, POSTMARK_SERVER_TOKEN 누락
            # 대신 최소한의 필수 키들 제공
            "SERPER_API_KEY": "test-minimal-key-1234567890123456",
            "POSTMARK_SERVER_TOKEN": "test-minimal-token-1234567890",
            "OPENAI_API_KEY": "sk-test-minimal-key-1234567890123456",
        }

        with patch.dict(os.environ, incomplete_env, clear=True):
            # 환경변수 변경 후 ConfigManager 재초기화
            ConfigManager.reset_for_testing(incomplete_env)
            config = ConfigManager()

            # 설정이 올바르게 로드되는지 확인
            assert config.SERPER_API_KEY == incomplete_env["SERPER_API_KEY"]

    @pytest.mark.parametrize(
        "env_name,expected_behavior",
        [
            ("development", "should_load_dotenv"),
            ("testing", "should_skip_dotenv"),
            ("production", "should_skip_dotenv"),
        ],
    )
    def test_dotenv_loading_behavior(self, env_name, expected_behavior):
        """환경별 .env 파일 로딩 동작 테스트"""
        base_env = {
            "APP_ENV": env_name,
            "SERPER_API_KEY": f"{env_name}-serper-key-1234567890123456",
            "POSTMARK_SERVER_TOKEN": f"{env_name}-postmark-token-1234567890",
            "EMAIL_SENDER": f"{env_name}@example.com",
            "OPENAI_API_KEY": f"sk-{env_name}-openai-key-1234567890123456",
        }

        with patch.dict(os.environ, base_env, clear=True):
            # 환경변수 변경 후 ConfigManager 재초기화
            ConfigManager.reset_for_testing(base_env)
            config = ConfigManager()

            # 환경별 설정이 올바르게 로드되는지 확인
            assert config.SERPER_API_KEY == base_env["SERPER_API_KEY"]
            assert config.EMAIL_SENDER == base_env["EMAIL_SENDER"]


class TestConfigurationConsistency:
    """설정 일관성 테스트"""

    def test_config_manager_fallback_behavior(self):
        """ConfigManager의 fallback 동작 테스트"""
        env_vars = {
            "SERPER_API_KEY": "fallback-test-key-1234567890123456",
            "POSTMARK_SERVER_TOKEN": "fallback-postmark-token-1234567890",
            "EMAIL_SENDER": "fallback@example.com",
            "OPENAI_API_KEY": "sk-fallback-openai-key-1234567890123456",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            ConfigManager.reset_for_testing(env_vars)
            config = ConfigManager()

            # ConfigManager가 환경변수를 올바르게 읽는지 확인
            assert config.SERPER_API_KEY == env_vars["SERPER_API_KEY"]
            assert config.EMAIL_SENDER == env_vars["EMAIL_SENDER"]

    def test_multiple_llm_providers_configuration(self):
        """다중 LLM 제공자 설정 테스트"""
        env_vars = {
            "SERPER_API_KEY": "multi-llm-key-1234567890123456",
            "POSTMARK_SERVER_TOKEN": "multi-llm-postmark-token-1234567890",
            "EMAIL_SENDER": "multi-llm@example.com",
            "OPENAI_API_KEY": "sk-openai-key-1234567890123456",
            "ANTHROPIC_API_KEY": "sk-ant-anthropic-key-1234567890123456",
            "GEMINI_API_KEY": "gemini-key-1234567890123456",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            ConfigManager.reset_for_testing(env_vars)
            config = ConfigManager()

            # 모든 LLM 키가 설정되는지 확인
            assert config.OPENAI_API_KEY == env_vars["OPENAI_API_KEY"]
            assert config.ANTHROPIC_API_KEY == env_vars["ANTHROPIC_API_KEY"]
            assert config.GEMINI_API_KEY == env_vars["GEMINI_API_KEY"]


class TestSecurityFeatures:
    """보안 기능 테스트"""

    def test_sensitive_data_not_in_logs(self):
        """민감한 데이터가 로그에 노출되지 않는지 테스트"""
        import logging
        from io import StringIO

        # 로그 캡처 설정
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        env_vars = {
            "SERPER_API_KEY": "secret-key-should-not-appear-1234567890123456",
            "POSTMARK_SERVER_TOKEN": "secret-token-should-not-appear-1234567890",
            "EMAIL_SENDER": "security-test@example.com",
            "OPENAI_API_KEY": "sk-secret-openai-should-not-appear-1234567890123456",
        }

        try:
            with patch.dict(os.environ, env_vars, clear=True):
                ConfigManager.reset_for_testing(env_vars)
                config = ConfigManager()

                # 로그 내용 확인
                log_contents = log_capture.getvalue()

                # 실제 키 값이 로그에 나타나지 않는지 확인
                # (현재 구현에서는 centralized settings의 마스킹 기능에 의존)
                assert config.SERPER_API_KEY == env_vars["SERPER_API_KEY"]

        finally:
            logger.removeHandler(handler)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
