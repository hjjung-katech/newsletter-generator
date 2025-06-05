"""
공통 설정 모듈 - CLI와 Web 양쪽에서 사용하는 설정들
"""

import os
from pathlib import Path
from typing import Optional


class Settings:
    """애플리케이션 공통 설정"""

    # 기본 디렉토리 설정
    BASE_DIR = Path(__file__).parent.parent
    CONFIG_DIR = BASE_DIR / "config"
    OUTPUT_DIR = BASE_DIR / "output"
    TEMPLATES_DIR = BASE_DIR / "templates"

    # 로그 설정
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # API 키들
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # 이메일 설정 (Postmark 사용)
    POSTMARK_SERVER_TOKEN = os.getenv("POSTMARK_SERVER_TOKEN")
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")

    # Google 설정
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

    # Naver API
    NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
    NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

    # 모드 설정
    MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # 모니터링
    SENTRY_DSN = os.getenv("SENTRY_DSN")

    # Web 전용 설정
    WEB_PORT = int(os.getenv("PORT", 8000))
    WEB_HOST = os.getenv("HOST", "0.0.0.0")

    # Redis 설정 (Web 큐잉용)
    REDIS_URL = os.getenv("REDIS_URL")

    # 데이터베이스 설정
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///storage.db")

    # 뉴스레터 기본 설정
    DEFAULT_PERIOD = 14
    VALID_PERIODS = [1, 7, 14, 30]
    DEFAULT_TEMPLATE_STYLE = "compact"

    @classmethod
    def get_required_env_vars(cls) -> list[str]:
        """필수 환경 변수 목록 반환"""
        return ["SERPER_API_KEY"]  # Serper API 키와 LLM API 키 중 하나는 필요

    @classmethod
    def validate_settings(cls) -> list[str]:
        """설정 검증 및 누락된 필수 설정 반환"""
        missing = []

        # 필수 환경 변수 확인
        if not cls.SERPER_API_KEY:
            missing.append("SERPER_API_KEY")

        # LLM API 키 중 하나는 필요
        if not any([cls.OPENAI_API_KEY, cls.GEMINI_API_KEY, cls.ANTHROPIC_API_KEY]):
            missing.append(
                "At least one LLM API key (OPENAI_API_KEY, GEMINI_API_KEY, or ANTHROPIC_API_KEY)"
            )

        # 디렉토리 존재 확인
        for dir_path in [cls.OUTPUT_DIR, cls.CONFIG_DIR]:
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    missing.append(f"Cannot create directory {dir_path}: {e}")

        return missing

    @classmethod
    def get_config_summary(cls) -> dict:
        """현재 설정 요약 반환 (보안 정보 제외)"""
        return {
            "log_level": cls.LOG_LEVEL,
            "mock_mode": cls.MOCK_MODE,
            "debug": cls.DEBUG,
            "web_port": cls.WEB_PORT,
            "has_serper_key": bool(cls.SERPER_API_KEY),
            "has_openai_key": bool(cls.OPENAI_API_KEY),
            "has_sentry_dsn": bool(cls.SENTRY_DSN),
            "base_dir": str(cls.BASE_DIR),
            "output_dir": str(cls.OUTPUT_DIR),
        }


# 싱글톤 인스턴스
settings = Settings()

# 하위 호환성을 위한 별칭들
MOCK_MODE = settings.MOCK_MODE
LOG_LEVEL = settings.LOG_LEVEL
DEFAULT_PERIOD = settings.DEFAULT_PERIOD
VALID_PERIODS = settings.VALID_PERIODS
