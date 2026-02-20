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
from typing import Any, List

from .utils.error_handling import handle_exception
from .utils.subprocess_utils import run_command_safely

logger = logging.getLogger(__name__)


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
    try:
        # centralized settings에서 먼저 시도
        from newsletter.centralized_settings import get_settings

        settings = get_settings()
        key_lower = key.lower()

        # 주요 매핑들
        mapping = {
            "serper_api_key": lambda s: s.serper_api_key.get_secret_value(),
            "openai_api_key": lambda s: (
                s.openai_api_key.get_secret_value() if s.openai_api_key else None
            ),
            "anthropic_api_key": lambda s: (
                s.anthropic_api_key.get_secret_value() if s.anthropic_api_key else None
            ),
            "gemini_api_key": lambda s: (
                s.gemini_api_key.get_secret_value() if s.gemini_api_key else None
            ),
            "postmark_server_token": (
                lambda s: s.postmark_server_token.get_secret_value()
            ),
            "email_sender": lambda s: s.email_sender,
            "secret_key": lambda s: s.secret_key,
            "port": lambda s: s.port,
            "host": lambda s: s.host,
            "app_env": lambda s: s.app_env,
            "sentry_dsn": lambda s: s.sentry_dsn,
            "sentry_traces_sample_rate": lambda s: s.sentry_traces_sample_rate,
            "sentry_profiles_sample_rate": lambda s: s.sentry_profiles_sample_rate,
            "log_level": lambda s: s.log_level,
            "log_format": lambda s: s.log_format,
            "mock_mode": lambda s: s.mock_mode,
            "debug": lambda s: s.debug,
            "redis_url": lambda s: s.redis_url,
            "rq_queue": lambda s: s.rq_queue,
            "database_url": lambda s: s.database_url,
            "google_application_credentials": (
                lambda s: s.google_application_credentials
            ),
            "google_client_id": lambda s: s.google_client_id,
            "google_client_secret": lambda s: (
                s.google_client_secret.get_secret_value()
                if s.google_client_secret
                else None
            ),
            "naver_client_id": lambda s: s.naver_client_id,
            "naver_client_secret": lambda s: (
                s.naver_client_secret.get_secret_value()
                if s.naver_client_secret
                else None
            ),
            "default_period": lambda s: s.default_period,
            "default_template_style": lambda s: s.default_template_style,
            "additional_rss_feeds": lambda s: s.additional_rss_feeds,
            "test_base_url": lambda s: s.test_base_url,
            "test_email_recipient": lambda s: s.test_email_recipient,
            "railway_production_url": lambda s: s.railway_production_url,
            "production_url": lambda s: s.production_url,
            "app_version": lambda s: s.app_version,
            "environment": lambda s: s.environment,
        }

        if key_lower in mapping:
            value = mapping[key_lower](settings)
            if value is not None:
                return value

        # 설정에 없으면 경고 후 fallback to os.getenv
        logger.warning(
            f"Key '{key}' not found in centralized settings, falling back to os.getenv"
        )

    except Exception as e:
        # centralized settings 로드 실패 시 fallback
        logger.debug(f"Centralized settings unavailable for key '{key}': {e}")

    # fallback to 기존 os.getenv
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
            return result.stdout.splitlines()
    except Exception as e:
        handle_exception(e, "ripgrep으로 환경 변수 사용 검색", log_level=logging.WARNING)

        # grep으로 대체 시도
        try:
            result = run_command_safely(
                ["grep", "-rn", "os.getenv", "--include=*.py", "."],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.splitlines()
        except Exception as e:
            handle_exception(e, "grep으로 환경 변수 사용 검색", log_level=logging.ERROR)

    return []


def migrate_getenv_calls():
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
