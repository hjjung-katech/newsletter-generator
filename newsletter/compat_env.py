"""
newsletter/compat_env.py
Legacy Compatibility Shim for Environment Variables

이 모듈은 기존 os.getenv() 호출을 점진적으로 centralized settings로 마이그레이션하기 위한
호환성 레이어입니다.

사용법:
    from newsletter.compat_env import getenv_compat

    # 기존: value = os.getenv("SERPER_API_KEY")
    # 새로운: value = getenv_compat("SERPER_API_KEY")
"""

import logging
import os
from typing import Any, List, cast

from newsletter_core.public.settings import get_setting_value

from .utils.error_handling import handle_exception
from .utils.subprocess_utils import run_command_safely

logger = logging.getLogger(__name__)

_KNOWN_COMPAT_KEYS = {
    "ADDITIONAL_RSS_FEEDS",
    "ANTHROPIC_API_KEY",
    "APP_ENV",
    "APP_VERSION",
    "DATABASE_URL",
    "DEBUG",
    "DEFAULT_PERIOD",
    "DEFAULT_TEMPLATE_STYLE",
    "EMAIL_SENDER",
    "ENVIRONMENT",
    "GEMINI_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "HOST",
    "LOG_FORMAT",
    "LOG_LEVEL",
    "MOCK_MODE",
    "NAVER_CLIENT_ID",
    "NAVER_CLIENT_SECRET",
    "OPENAI_API_KEY",
    "PORT",
    "POSTMARK_FROM_EMAIL",
    "POSTMARK_SERVER_TOKEN",
    "PRODUCTION_URL",
    "RAILWAY_PRODUCTION_URL",
    "REDIS_URL",
    "RQ_QUEUE",
    "SENTRY_DSN",
    "SENTRY_PROFILES_SAMPLE_RATE",
    "SENTRY_TRACES_SAMPLE_RATE",
    "SECRET_KEY",
    "SERPER_API_KEY",
    "TEST_BASE_URL",
    "TEST_EMAIL_RECIPIENT",
}


def getenv_compat(key: str, default: Any = None) -> Any:
    """
    레거시 os.getenv() 호출을 centralized settings로 연결하는 호환 함수

    Args:
        key: 환경변수 키 (예: "SERPER_API_KEY")
        default: 기본값

    Returns:
        설정값 또는 기본값

    Note:
        이 함수는 마이그레이션 기간 동안만 사용하고,
        점진적으로 get_settings() 직접 호출로 교체해야 합니다.
    """
    normalized_key = str(key or "").strip().upper()
    value = get_setting_value(normalized_key)
    if value is not None:
        return value

    if normalized_key in _KNOWN_COMPAT_KEYS:
        return default

    logger.warning(
        "Key '%s' not mapped to centralized settings, falling back to os.getenv",
        key,
    )
    return os.getenv(key, default)


def find_env_usage() -> List[str]:
    """
    프로젝트에서 os.getenv 사용을 찾아 반환
    """
    try:
        # ripgrep 시도
        result = run_command_safely(
            ["rg", "-n", r"os\.getenv", "--type", "py", "."],
            capture_output=True,
            text=True,
            cwd=".",
        )
        if result.returncode == 0:
            return cast(list[str], result.stdout.splitlines())
    except Exception as e:
        handle_exception(
            e,
            "ripgrep으로 환경 변수 사용 검색",
            log_level=logging.WARNING,
        )

        # grep으로 대체 시도
        try:
            result = run_command_safely(
                ["grep", "-rn", "os.getenv", "--include=*.py", "."],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return cast(list[str], result.stdout.splitlines())
        except Exception as e:
            handle_exception(
                e,
                "grep으로 환경 변수 사용 검색",
                log_level=logging.ERROR,
            )

    return []


def migrate_getenv_calls() -> None:
    """
    모든 os.getenv 호출을 찾아서 마이그레이션이 필요한 곳을 보고하는 유틸리티

    개발자가 수동으로 실행하여 마이그레이션 진행도를 확인할 수 있습니다.
    """
    found_usages = find_env_usage()
    if found_usages:
        print("🔍 Found os.getenv calls that need migration:")
        for usage in found_usages:
            print(usage)
    else:
        print("✅ No os.getenv calls found!")


if __name__ == "__main__":
    # 스크립트로 실행 시 마이그레이션 체크 실행
    migrate_getenv_calls()
