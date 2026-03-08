# -*- coding: utf-8 -*-
"""
Unit tests for F-14 Centralized Settings Layer
"""

import logging
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import SecretStr, ValidationError

from newsletter.centralized_settings import (
    CentralizedSettings,
    _SecretFilter,
    clear_settings_cache,
    disable_test_mode,
    enable_test_mode,
    get_settings,
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

        enable_test_mode(env_vars)
        try:
            settings = CentralizedSettings()
            assert settings.email_sender == env_vars["EMAIL_SENDER"]
            assert settings.port == 8000  # 기본값
        finally:
            disable_test_mode()

    def test_invalid_port_raises_validation_error(self):
        """유효하지 않은 포트 범위는 ValidationError를 발생시켜야 한다."""
        env_vars = {
            "EMAIL_SENDER": "test@example.com",
            "OPENAI_API_KEY": "sk-test-openai-key-1234567890123456",
            "PORT": "70000",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError):
                CentralizedSettings()

    def test_api_key_length_validation(self):
        """API 키 길이 검증 (최소 16자)"""
        env_vars = {
            "SERPER_API_KEY": "short",  # 16자 미만
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "EMAIL_SENDER": "test@example.com",
            "OPENAI_API_KEY": "sk-test-openai-key-1234567890123456",
        }

        # 테스트 모드를 사용하지 않고 직접 환경변수 패치
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError):
                CentralizedSettings()

    def test_at_least_one_llm_key_required(self):
        """LLM API 키 중 하나는 반드시 필요"""
        env_vars = {
            "SERPER_API_KEY": "test-serper-key-1234567890123456",
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "EMAIL_SENDER": "test@example.com",
            # LLM 키들 모두 누락
            "F14_FORCE_VALIDATION": "1",  # F-14: 검증 강제 모드 활성화
        }

        # 테스트 모드를 사용하지 않고 직접 환경변수 패치
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(
                ValueError, match="At least one LLM API key is required"
            ):
                CentralizedSettings()


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

        enable_test_mode(env_vars)
        try:
            clear_settings_cache()
            s1 = get_settings()
            s2 = get_settings()
            assert s1 is s2
        finally:
            disable_test_mode()


@pytest.fixture(autouse=True)
def clear_settings_cache_fixture():
    """각 테스트 전후에 설정 캐시를 클리어"""
    clear_settings_cache()
    disable_test_mode()
    yield
    clear_settings_cache()
    disable_test_mode()


class TestEnvironmentSpecific:
    """환경별 설정 테스트"""

    @pytest.mark.parametrize("app_env", ["development", "testing", "production"])
    def test_environment_settings(self, app_env):
        """환경별 설정 동작 확인"""
        env_vars = {
            "APP_ENV": app_env,
            "SERPER_API_KEY": "test-serper-key-1234567890123456",
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "EMAIL_SENDER": "test@example.com",
            "OPENAI_API_KEY": "sk-test-openai-key-1234567890123456",
        }

        enable_test_mode(env_vars)
        try:
            settings = CentralizedSettings()
            assert settings.app_env == app_env
        finally:
            disable_test_mode()


class TestF14PerformanceSettings:
    """F-14: 중앙화된 성능 설정 테스트"""

    def test_performance_settings_default_values(self):
        """성능 설정의 기본값을 테스트합니다."""
        env_vars = {
            "SERPER_API_KEY": "test-serper-key-1234567890",
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "EMAIL_SENDER": "test@example.com",
            "GEMINI_API_KEY": "test-gemini-key-1234567890",
        }

        enable_test_mode(env_vars)
        try:
            settings = CentralizedSettings()

            # F-14 성능 설정 기본값 확인
            assert settings.llm_request_timeout == 120
            assert settings.llm_test_timeout == 60
            assert settings.llm_max_retries == 3
            assert settings.llm_retry_delay == 1.0
            assert settings.enable_fast_mode is False
            assert settings.batch_processing is True
            assert settings.concurrent_requests == 5
        finally:
            disable_test_mode()

    def test_performance_settings_custom_values(self):
        """사용자 정의 성능 설정을 테스트합니다."""
        env_vars = {
            "SERPER_API_KEY": "test-serper-key-1234567890",
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "EMAIL_SENDER": "test@example.com",
            "GEMINI_API_KEY": "test-gemini-key-1234567890",
            "LLM_REQUEST_TIMEOUT": "180",
            "LLM_TEST_TIMEOUT": "90",
            "LLM_MAX_RETRIES": "5",
            "LLM_RETRY_DELAY": "2.0",
            "ENABLE_FAST_MODE": "true",
            "CONCURRENT_REQUESTS": "10",
        }

        enable_test_mode(env_vars)
        try:
            settings = CentralizedSettings()

            # 사용자 정의 값 확인
            assert settings.llm_request_timeout == 180
            assert settings.llm_test_timeout == 90
            assert settings.llm_max_retries == 5
            assert settings.llm_retry_delay == 2.0
            assert settings.enable_fast_mode is True
            assert settings.concurrent_requests == 10
        finally:
            disable_test_mode()

    def test_fast_mode_environment_variable(self):
        """환경변수를 통한 빠른 모드 설정을 테스트합니다."""
        env_vars = {
            "SERPER_API_KEY": "test-serper-key-1234567890",
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "EMAIL_SENDER": "test@example.com",
            "GEMINI_API_KEY": "test-gemini-key-1234567890",
            "ENABLE_FAST_MODE": "true",
            "LLM_REQUEST_TIMEOUT": "150",
        }

        enable_test_mode(env_vars)
        try:
            settings = get_settings()
            assert settings.enable_fast_mode is True
            assert settings.llm_request_timeout == 150
        finally:
            disable_test_mode()

    def test_performance_settings_validation(self):
        """성능 설정의 유효성 검증을 테스트합니다."""
        env_vars = {
            "SERPER_API_KEY": "test-serper-key-1234567890",
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "EMAIL_SENDER": "test@example.com",
            "GEMINI_API_KEY": "test-gemini-key-1234567890",
            "LLM_REQUEST_TIMEOUT": "60",
            "LLM_MAX_RETRIES": "1",
            "CONCURRENT_REQUESTS": "1",
        }

        enable_test_mode(env_vars)
        try:
            settings = CentralizedSettings()

            assert settings.llm_request_timeout >= 60
            assert settings.llm_max_retries >= 1
            assert settings.concurrent_requests >= 1
        finally:
            disable_test_mode()

    def test_settings_config_summary(self):
        """설정 요약 기능을 테스트합니다."""
        env_vars = {
            "SERPER_API_KEY": "test-serper-key-1234567890",
            "POSTMARK_SERVER_TOKEN": "test-postmark-token-1234567890",
            "EMAIL_SENDER": "test@example.com",
            "GEMINI_API_KEY": "test-gemini-key-1234567890",
            "ENABLE_FAST_MODE": "true",
        }

        enable_test_mode(env_vars)
        try:
            settings = CentralizedSettings()
            summary = settings.get_config_summary()

            # 기본 설정 확인
            assert "app_env" in summary
            assert "has_gemini_key" in summary

            # F-14: 성능 설정이 올바르게 로드되는지 확인
            assert settings.enable_fast_mode is True
            assert summary["has_gemini_key"] is True
            assert summary["has_postmark_token"] is True
            assert env_vars["GEMINI_API_KEY"] not in str(summary)
            assert env_vars["POSTMARK_SERVER_TOKEN"] not in str(summary)
        finally:
            disable_test_mode()

    def test_secret_filter_masks_values_in_log_messages(self):
        """로그 필터가 시크릿 원문을 남기지 않아야 한다."""
        secret = "test-postmark-token-1234567890"
        fake_settings = SimpleNamespace(
            serper_api_key=None,
            postmark_server_token=SecretStr(secret),
            openai_api_key=None,
            anthropic_api_key=None,
            gemini_api_key=None,
        )
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=0,
            msg=f"token={secret}",
            args=(),
            exc_info=None,
        )

        with patch(
            "newsletter.centralized_settings.get_settings",
            return_value=fake_settings,
        ):
            assert _SecretFilter().filter(record) is True

        assert secret not in record.msg
        assert "POSTMARK_SERVER_TOKEN" in record.msg
        assert "len:" in record.msg

    def test_get_settings_logs_critical_on_validation_failure(self, caplog):
        """설정 생성 실패 시 critical 로그를 남기고 예외를 다시 발생시킨다."""
        clear_settings_cache()
        with (
            patch("newsletter.centralized_settings._load_dotenv_if_needed"),
            patch(
                "newsletter.centralized_settings.CentralizedSettings",
                side_effect=ValueError("boom"),
            ),
            caplog.at_level(logging.CRITICAL),
            pytest.raises(ValueError, match="boom"),
        ):
            get_settings()

        assert "Settings validation failed: boom" in caplog.text
