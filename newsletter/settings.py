"""
newsletter/settings.py
Centralized Settings Layer – auto-validated & type-safe

F-14 "Centralized Settings Layer" 구현:
- 중앙집중식 설정 관리
- 타입 안전성 (Pydantic)
- Fail-Fast 검증
- Secret 마스킹
- 환경별 설정 지원
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseSettings, Field, SecretStr, field_validator
from pydantic_settings import SettingsConfigDict

from .utils.error_handling import handle_exception

# ────────────────────────────────
# 1) .env 로드 (dev 전용·안전하게)
# ────────────────────────────────
APP_ENV = os.getenv("APP_ENV", "production")  # cli, docker, actions에서 주입
if APP_ENV == "development":
    # override=False → 이미 정의된 OS ENV 는 유지
    try:
        from dotenv import load_dotenv

        load_dotenv(".env", override=False)
    except ImportError:
        pass  # dotenv 없어도 괜찮음


# ────────────────────────────────
# 2) Settings 모델
# ────────────────────────────────
class Settings(BaseSettings):
    """중앙집중식 애플리케이션 설정 - 타입 안전 & 자동 검증"""

    # ── 필수 시크릿 ──────────────────────────────────────
    serper_api_key: SecretStr
    postmark_server_token: SecretStr = Field(..., description="Postmark 이메일 발송용 서버 토큰")
    email_sender: str = Field(..., description="이메일 발송자 주소")

    # ── LLM API 키들 (하나 이상 필요) ──────────────────────
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None

    # ── 공통 설정 ───────────────────────────────────────
    secret_key: str = Field(
        default="dev-secret-key-change-in-production", min_length=16
    )
    port: int = Field(8000, ge=1, le=65535, description="웹 서버 포트")
    # Bandit B104: 개발/테스트는 127.0.0.1, 프로덕션만 0.0.0.0 바인딩 (보안 검증됨)  # nosec B104
    host: str = Field(
        default="127.0.0.1" if APP_ENV in ["development", "testing"] else "0.0.0.0",
        description="웹 서버 호스트 (개발/테스트 환경: localhost만, 프로덕션: 모든 인터페이스)",
    )  # nosec B104
    app_env: Literal["development", "testing", "production"] = APP_ENV

    # ── 선택(디폴트) ─────────────────────────────────────
    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = Field(0.1, ge=0.0, le=1.0)
    sentry_profiles_sample_rate: float = Field(0.1, ge=0.0, le=1.0)
    log_level: str = Field("INFO", description="로깅 레벨")
    log_format: str = Field("json", description="로그 포맷 (json/text)")
    mock_mode: bool = Field(False, description="모킹 모드 활성화")
    debug: bool = Field(False, description="디버그 모드")

    # ── 웹 & 인프라 설정 ────────────────────────────────────
    redis_url: str | None = Field(None, description="Redis 연결 URL (큐잉용)")
    rq_queue: str = Field("default", description="RQ 큐 이름")
    database_url: str = Field("sqlite:///storage.db", description="데이터베이스 연결 URL")

    # ── Google & Naver 옵션 API ──────────────────────────
    google_application_credentials: str | None = None
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    naver_client_id: str | None = None
    naver_client_secret: SecretStr | None = None

    # ── 뉴스레터 기본값 ─────────────────────────────────────
    default_period: int = Field(14, ge=1, le=365)
    default_template_style: str = "compact"
    additional_rss_feeds: str = ""

    # ── 테스팅 & 배포 관련 ──────────────────────────────────
    test_base_url: str | None = None
    test_email_recipient: str | None = None
    railway_production_url: str | None = None
    production_url: str | None = None
    app_version: str = "1.0.0"
    environment: str = "production"

    # ── 경로 설정 (computed) ──────────────────────────────
    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent.parent

    @property
    def config_dir(self) -> Path:
        return self.base_dir / "config"

    @property
    def output_dir(self) -> Path:
        return self.base_dir / "output"

    @property
    def templates_dir(self) -> Path:
        return self.base_dir / "templates"

    # ── 모델 설정 ───────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env" if APP_ENV == "development" else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
        # 환경변수명 자동 변환 (SERPER_API_KEY -> serper_api_key)
        env_prefix="",
    )

    # ── 커스텀 검증 ─────────────────────────────────────
    @field_validator("serper_api_key", "postmark_server_token")
    @classmethod
    def _validate_api_keys_length(cls, v: SecretStr) -> SecretStr:
        """API 키는 최소 16자 이상이어야 함"""
        if len(v.get_secret_value()) < 16:
            raise ValueError("API key must be ≥ 16 characters")
        return v

    @field_validator(
        "openai_api_key", "anthropic_api_key", "gemini_api_key", mode="before"
    )
    @classmethod
    def _validate_optional_api_keys(cls, v):
        """선택적 API 키 검증"""
        if v is not None and len(str(v)) < 16:
            raise ValueError("API key must be ≥ 16 characters if provided")
        return v

    def model_post_init(self, __context) -> None:
        """LLM API 키 중 하나는 반드시 있어야 함"""
        llm_keys = [self.openai_api_key, self.anthropic_api_key, self.gemini_api_key]
        if not any(key is not None for key in llm_keys):
            raise ValueError(
                "At least one LLM API key is required: "
                "OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY"
            )

        # 디렉토리 생성
        for dir_path in [self.output_dir, self.config_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    # ── 유틸리티 메서드 ─────────────────────────────────────
    @property
    def valid_periods(self) -> list[int]:
        """지원하는 기간 목록"""
        return [1, 7, 14, 30]

    def get_config_summary(self) -> dict:
        """현재 설정 요약 반환 (보안 정보 마스킹)"""
        return {
            "app_env": self.app_env,
            "log_level": self.log_level,
            "mock_mode": self.mock_mode,
            "debug": self.debug,
            "port": self.port,
            "host": self.host,
            "has_serper_key": bool(self.serper_api_key),
            "has_openai_key": bool(self.openai_api_key),
            "has_anthropic_key": bool(self.anthropic_api_key),
            "has_gemini_key": bool(self.gemini_api_key),
            "has_postmark_token": bool(self.postmark_server_token),
            "has_sentry_dsn": bool(self.sentry_dsn),
            "base_dir": str(self.base_dir),
            "output_dir": str(self.output_dir),
        }


# ────────────────────────────────
# 3) 싱글턴 헬퍼
# ────────────────────────────────
@lru_cache
def get_settings() -> Settings:  # pragma: no cover
    """설정 싱글톤 반환 - 앱 시작 시 한 번만 로드 & 검증"""
    try:
        return Settings()
    except Exception as e:
        logging.critical(f"❌ Settings validation failed: {e}")
        raise


# ────────────────────────────────
# 4) Secret 마스킹 로거 필터
# ────────────────────────────────
class _SecretFilter(logging.Filter):
    """로그에서 시크릿 값을 마스킹하는 필터"""

    def filter(self, record: logging.LogRecord) -> bool:
        """로그 레코드에서 시크릿 값을 ******** 로 대체"""
        try:
            settings = get_settings()
            msg = str(record.msg)

            # 주요 시크릿들 마스킹
            secrets_to_mask = [
                (settings.serper_api_key.get_secret_value(), "SERPER_API_KEY"),
                (settings.postmark_server_token.get_secret_value(), "POSTMARK_TOKEN"),
            ]

            # 선택적 시크릿들
            if settings.openai_api_key:
                secrets_to_mask.append(
                    (settings.openai_api_key.get_secret_value(), "OPENAI_KEY")
                )
            if settings.anthropic_api_key:
                secrets_to_mask.append(
                    (settings.anthropic_api_key.get_secret_value(), "ANTHROPIC_KEY")
                )
            if settings.gemini_api_key:
                secrets_to_mask.append(
                    (settings.gemini_api_key.get_secret_value(), "GEMINI_KEY")
                )
            if settings.google_client_secret:
                secrets_to_mask.append(
                    (settings.google_client_secret.get_secret_value(), "GOOGLE_SECRET")
                )
            if settings.naver_client_secret:
                secrets_to_mask.append(
                    (settings.naver_client_secret.get_secret_value(), "NAVER_SECRET")
                )

            # 마스킹 적용
            for secret_value, name in secrets_to_mask:
                if secret_value and secret_value in msg:
                    masked = f"•••••••••••• ({name}, len: {len(secret_value)})"
                    msg = msg.replace(secret_value, masked)

            record.msg = msg
        except Exception as e:
            handle_exception(e, "로그 메시지 설정", log_level=logging.DEBUG)
            # 필터 자체가 실패해도 로그는 출력되어야 함

        return True


# 전역 로거에 시크릿 필터 추가
logging.getLogger().addFilter(_SecretFilter())


# ────────────────────────────────
# 5) 하위 호환성 유지
# ────────────────────────────────
# 기존 코드와의 호환성을 위한 별칭들
try:
    _settings = get_settings()
except Exception:
    # 개발 중이거나 필수 환경변수가 없는 경우 None으로 설정
    _settings = None


# 기존 Settings 클래스 별칭 (레거시 호환)
class LegacySettings:
    """기존 Settings 클래스와의 호환성을 위한 래퍼"""

    @property
    def MOCK_MODE(self):
        return get_settings().mock_mode if _settings else False

    @property
    def LOG_LEVEL(self):
        return get_settings().log_level if _settings else "INFO"

    @property
    def DEFAULT_PERIOD(self):
        return get_settings().default_period if _settings else 14

    @property
    def VALID_PERIODS(self):
        return get_settings().valid_periods if _settings else [1, 7, 14, 30]

    @property
    def BASE_DIR(self):
        return get_settings().base_dir if _settings else Path(__file__).parent.parent

    @property
    def OUTPUT_DIR(self):
        return (
            get_settings().output_dir
            if _settings
            else Path(__file__).parent.parent / "output"
        )

    @property
    def CONFIG_DIR(self):
        return (
            get_settings().config_dir
            if _settings
            else Path(__file__).parent.parent / "config"
        )

    @property
    def TEMPLATES_DIR(self):
        return (
            get_settings().templates_dir
            if _settings
            else Path(__file__).parent.parent / "templates"
        )

    # 기존 메서드들
    def get_config_summary(self):
        return get_settings().get_config_summary() if _settings else {}


# 레거시 호환 인스턴스 생성
settings = LegacySettings()

# 자주 사용되는 변수들의 직접 별칭
MOCK_MODE = _settings.mock_mode if _settings else False
LOG_LEVEL = _settings.log_level if _settings else "INFO"
DEFAULT_PERIOD = _settings.default_period if _settings else 14
VALID_PERIODS = _settings.valid_periods if _settings else [1, 7, 14, 30]
