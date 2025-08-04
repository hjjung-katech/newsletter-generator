#!/usr/bin/env python3
"""
설정 관련 문제 해결 확인 테스트
"""

import os
import sys
import pytest

# 테스트 환경 설정
os.environ["TESTING"] = "1"
os.environ["MOCK_MODE"] = "true"

# 모듈 캐시 클리어
modules_to_clear = [
    "newsletter.config_manager",
    "newsletter.centralized_settings",
    "newsletter",
]
for module in modules_to_clear:
    if module in sys.modules:
        del sys.modules[module]


def test_config_manager_import():
    """ConfigManager import 테스트"""
    try:
        from newsletter.config_manager import get_config_manager

        config_manager = get_config_manager()
        assert config_manager is not None
        print("✅ ConfigManager import 성공")
    except Exception as e:
        pytest.fail(f"ConfigManager import 실패: {e}")


def test_centralized_settings_import():
    """CentralizedSettings import 테스트"""
    try:
        from newsletter.centralized_settings import get_settings

        settings = get_settings()
        assert settings is not None
        print("✅ CentralizedSettings import 성공")
    except Exception as e:
        pytest.fail(f"CentralizedSettings import 실패: {e}")


def test_optional_fields_handling():
    """Optional 필드 처리 테스트"""
    try:
        from newsletter.config_manager import get_config_manager

        config_manager = get_config_manager()

        # Optional 필드들이 None이어도 오류가 발생하지 않아야 함
        assert config_manager.SERPER_API_KEY is None or isinstance(
            config_manager.SERPER_API_KEY, str
        )
        assert config_manager.POSTMARK_SERVER_TOKEN is None or isinstance(
            config_manager.POSTMARK_SERVER_TOKEN, str
        )
        assert config_manager.EMAIL_SENDER is None or isinstance(
            config_manager.EMAIL_SENDER, str
        )

        print("✅ Optional 필드 처리 성공")
    except Exception as e:
        pytest.fail(f"Optional 필드 처리 실패: {e}")


def test_test_mode_detection():
    """테스트 모드 감지 테스트"""
    try:
        from newsletter.centralized_settings import get_settings

        settings = get_settings()

        # 테스트 모드에서 기본값들이 설정되어야 함
        assert settings.test_mode is True
        assert settings.mock_api_responses is True
        assert settings.skip_real_api_calls is True

        print("✅ 테스트 모드 감지 성공")
    except Exception as e:
        pytest.fail(f"테스트 모드 감지 실패: {e}")


if __name__ == "__main__":
    print("🔧 설정 관련 문제 해결 확인 테스트 시작")

    test_config_manager_import()
    test_centralized_settings_import()
    test_optional_fields_handling()
    test_test_mode_detection()

    print("✅ 모든 테스트 통과!")
