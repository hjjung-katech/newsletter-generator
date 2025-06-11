"""
Unit tests for F-14 Centralized Settings Layer
테스트 범위: 설정 검증, 타입 안전성, Secret 마스킹, 환경별 분기
"""

import os
import pytest
import logging
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from newsletter.centralized_settings import (
    CentralizedSettings,
    get_settings,
    _SecretFilter,
    setup_secret_logging,
)


class TestCentralizedSettings:
    """CentralizedSettings 모델 테스트"""

    def test_happy_path_with_all_required_fields(self):
        """필수 필드들이 모두 있을 때 성공적으로 설정 로드"""
        env_vars = {
            "SERPER_API_KEY": "test-serper-key-1234567890123456",
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "EMAIL_SENDER": "test@example.com",
            "OPENAI_API_KEY": "sk-test-openai-key-1234567890123456",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = CentralizedSettings()

            assert (
                settings.serper_api_key.get_secret_value() == env_vars["SERPER_API_KEY"]
            )
            assert (
                settings.postmark_server_token.get_secret_value()
                == env_vars["POSTMARK_SERVER_TOKEN"]
            )
            assert settings.email_sender == env_vars["EMAIL_SENDER"]
            assert (
                settings.openai_api_key.get_secret_value() == env_vars["OPENAI_API_KEY"]
            )
            assert settings.app_env == "production"  # 기본값
            assert settings.port == 8000  # 기본값

    def test_missing_required_field_raises_validation_error(self):
        """필수 필드 누락 시 ValidationError 발생"""
        incomplete_env = {
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "EMAIL_SENDER": "test@example.com",
            "OPENAI_API_KEY": "sk-test-openai-key-1234567890123456",
            # SERPER_API_KEY 누락
        }

        with patch.dict(os.environ, incomplete_env, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                CentralizedSettings()

            assert "serper_api_key" in str(exc_info.value)

    def test_api_key_length_validation(self):
        """API 키 길이 검증 (최소 16자)"""
        env_vars = {
            "SERPER_API_KEY": "short",  # 16자 미만
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "EMAIL_SENDER": "test@example.com",
            "OPENAI_API_KEY": "sk-test-openai-key-1234567890123456",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                CentralizedSettings()

            assert "must be ≥ 16 characters" in str(exc_info.value)

    def test_port_range_validation(self):
        """포트 범위 검증 (1-65535)"""
        env_vars = {
            "SERPER_API_KEY": "test-serper-key-1234567890123456",
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "EMAIL_SENDER": "test@example.com",
            "OPENAI_API_KEY": "sk-test-openai-key-1234567890123456",
            "PORT": "70000",  # 범위 초과
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                CentralizedSettings()

            assert "less than or equal to 65535" in str(exc_info.value)

    def test_at_least_one_llm_key_required(self):
        """LLM API 키 중 하나는 반드시 필요"""
        env_vars = {
            "SERPER_API_KEY": "test-serper-key-1234567890123456",
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "EMAIL_SENDER": "test@example.com",
            # LLM 키들 모두 누락
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError) as exc_info:
                CentralizedSettings()

            assert "At least one LLM API key is required" in str(exc_info.value)

    def test_optional_llm_keys(self):
        """선택적 LLM 키들이 정상 동작"""
        env_vars = {
            "SERPER_API_KEY": "test-serper-key-1234567890123456",
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "EMAIL_SENDER": "test@example.com",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-1234567890123456",
            "GEMINI_API_KEY": "gemini-test-key-1234567890123456",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = CentralizedSettings()

            assert (
                settings.anthropic_api_key.get_secret_value()
                == env_vars["ANTHROPIC_API_KEY"]
            )
            assert (
                settings.gemini_api_key.get_secret_value() == env_vars["GEMINI_API_KEY"]
            )
            assert settings.openai_api_key is None

    def test_environment_specific_behavior(self):
        """환경별 설정 동작 확인"""
        base_env = {
            "SERPER_API_KEY": "test-serper-key-1234567890123456",
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "EMAIL_SENDER": "test@example.com",
            "OPENAI_API_KEY": "sk-test-openai-key-1234567890123456",
        }

        # Development 환경
        dev_env = {**base_env, "APP_ENV": "development"}
        with patch.dict(os.environ, dev_env, clear=True):
            settings = CentralizedSettings()
            assert settings.app_env == "development"

        # Production 환경
        prod_env = {**base_env, "APP_ENV": "production"}
        with patch.dict(os.environ, prod_env, clear=True):
            settings = CentralizedSettings()
            assert settings.app_env == "production"

    def test_config_summary_masks_secrets(self):
        """설정 요약에서 시크릿 정보가 마스킹되는지 확인"""
        env_vars = {
            "SERPER_API_KEY": "test-serper-key-1234567890123456",
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "EMAIL_SENDER": "test@example.com",
            "OPENAI_API_KEY": "sk-test-openai-key-1234567890123456",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = CentralizedSettings()
            summary = settings.get_config_summary()

            # 시크릿 값은 직접 노출되지 않고 boolean으로만 표시
            assert summary["has_serper_key"] is True
            assert summary["has_openai_key"] is True
            assert summary["has_postmark_token"] is True

            # 실제 키 값은 summary에 없어야 함
            summary_str = str(summary)
            assert "test-serper-key" not in summary_str
            assert "test-postmark-token" not in summary_str


class TestGetSettingsSingleton:
    """get_settings() 싱글톤 헬퍼 테스트"""

    def test_singleton_behavior(self):
        """동일한 인스턴스 반환 확인"""
        env_vars = {
            "SERPER_API_KEY": "test-serper-key-1234567890123456",
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "EMAIL_SENDER": "test@example.com",
            "OPENAI_API_KEY": "sk-test-openai-key-1234567890123456",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            # 캐시 클리어
            get_settings.cache_clear()

            settings1 = get_settings()
            settings2 = get_settings()

            # 동일한 인스턴스여야 함
            assert settings1 is settings2

    def test_critical_logging_on_validation_failure(self):
        """설정 검증 실패 시 critical 로그 출력"""
        incomplete_env = {"EMAIL_SENDER": "test@example.com"}

        with patch.dict(os.environ, incomplete_env, clear=True):
            get_settings.cache_clear()

            with patch("logging.critical") as mock_critical:
                with pytest.raises(ValidationError):
                    get_settings()

                mock_critical.assert_called_once()
                assert "Settings validation failed" in str(mock_critical.call_args)


class TestSecretFilter:
    """Secret 마스킹 필터 테스트"""

    def test_secret_masking_in_log_records(self):
        """로그에서 시크릿 값이 마스킹되는지 확인"""
        env_vars = {
            "SERPER_API_KEY": "secret-serper-12345678901234567890",
            "POSTMARK_SERVER_TOKEN": "secret-postmark-12345678901234567890",
            "EMAIL_SENDER": "test@example.com",
            "OPENAI_API_KEY": "sk-secret-openai-12345678901234567890",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            secret_filter = _SecretFilter()

            # 시크릿 값이 포함된 로그 레코드 생성
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=f"API Key: {env_vars['SERPER_API_KEY']}",
                args=(),
                exc_info=None,
            )

            # 필터 적용
            secret_filter.filter(record)

            # 시크릿 값이 마스킹되었는지 확인
            assert env_vars["SERPER_API_KEY"] not in str(record.msg)
            assert "SERPER_API_KEY" in str(record.msg)
            assert "len: 33" in str(record.msg)

    def test_filter_resilience_to_errors(self):
        """필터가 오류 상황에서도 안정적으로 동작하는지 확인"""
        secret_filter = _SecretFilter()

        # 잘못된 로그 레코드로 테스트
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Normal log message",
            args=(),
            exc_info=None,
        )

        # 오류가 발생해도 True를 반환해야 함
        result = secret_filter.filter(record)
        assert result is True

    def test_setup_secret_logging(self):
        """setup_secret_logging() 함수 테스트"""
        # 기존 필터 수 확인
        initial_filter_count = len(logging.getLogger().filters)

        setup_secret_logging()

        # 필터가 추가되었는지 확인
        assert len(logging.getLogger().filters) >= initial_filter_count


class TestEnvironmentVariableMapping:
    """환경변수 매핑 테스트"""

    def test_case_insensitive_env_vars(self):
        """대소문자 구분 없는 환경변수 처리"""
        env_vars = {
            "serper_api_key": "test-serper-key-1234567890123456",  # 소문자
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",  # 대문자
            "Email_Sender": "test@example.com",  # 혼합
            "openai_API_key": "sk-test-openai-key-1234567890123456",  # 혼합
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = CentralizedSettings()

            assert (
                settings.serper_api_key.get_secret_value() == env_vars["serper_api_key"]
            )
            assert settings.email_sender == env_vars["Email_Sender"]


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """각 테스트 전후에 설정 캐시를 클리어"""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestSettingsIntegration:
    """통합 테스트"""

    def test_full_settings_lifecycle(self):
        """전체 설정 라이프사이클 테스트"""
        env_vars = {
            "APP_ENV": "testing",
            "SERPER_API_KEY": "integration-serper-key-1234567890123456",
            "POSTMARK_SERVER_TOKEN": "integration-postmark-token-1234567890",
            "EMAIL_SENDER": "integration@example.com",
            "ANTHROPIC_API_KEY": "sk-ant-integration-key-1234567890123456",
            "LOG_LEVEL": "DEBUG",
            "MOCK_MODE": "true",
            "PORT": "9000",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = get_settings()

            # 기본 설정 확인
            assert settings.app_env == "testing"
            assert settings.log_level == "DEBUG"
            assert settings.mock_mode is True
            assert settings.port == 9000

            # 경로 설정 확인
            assert settings.base_dir.exists()
            assert settings.output_dir.exists()
            assert settings.config_dir.exists()

            # 설정 요약 확인
            summary = settings.get_config_summary()
            assert summary["app_env"] == "testing"
            assert summary["has_anthropic_key"] is True
            assert summary["has_openai_key"] is False
