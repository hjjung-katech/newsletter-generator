# -*- coding: utf-8 -*-
"""
Unit tests for F-14 Centralized Settings Layer
"""

import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError

from newsletter.centralized_settings import (
    CentralizedSettings,
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

        with patch.dict(os.environ, env_vars, clear=True):
            settings = CentralizedSettings()
            assert settings.email_sender == env_vars["EMAIL_SENDER"]
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
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError):
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

        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            s1 = get_settings()
            s2 = get_settings()
            assert s1 is s2


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """각 테스트 전후에 설정 캐시를 클리어"""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


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

        with patch.dict(os.environ, env_vars, clear=True):
            settings = CentralizedSettings()
            assert settings.app_env == app_env
