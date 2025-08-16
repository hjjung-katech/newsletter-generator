#!/usr/bin/env python3
"""
F-14 중앙집중식 설정 관리 모듈

이 모듈은 애플리케이션의 모든 설정을 중앙에서 관리하며,
환경변수, .env 파일, 기본값을 통합적으로 처리합니다.
"""

import logging
import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Literal, Tuple, Type

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from .utils.error_handling import handle_exception

# 테스트 모드 플래그
_test_mode = "pytest" in sys.modules or os.getenv("TESTING") == "1"
_test_env_vars = {}


def is_running_in_pytest() -> bool:
    """pytest 환경에서 실행 중인지 확인"""
    return "pytest" in sys.modules or os.getenv("PYTEST_RUNNING") == "1" or _test_mode


def clear_settings_cache():
    """F-14: 설정 캐시를 클리어하여 테스트 격리 지원"""
    if "get_settings" in globals():
        get_settings.cache_clear()


def enable_test_mode(test_env_vars: dict = None):
    """테스트 모드 활성화 - 환경변수 오버라이드 허용"""
    global _test_mode, _test_env_vars
    _test_mode = True
    _test_env_vars = test_env_vars or {}
    clear_settings_cache()


def disable_test_mode():
    """테스트 모드 비활성화"""
    global _test_mode, _test_env_vars
    _test_mode = False
    _test_env_vars = {}
    clear_settings_cache()


def _get_env(key: str, default=None):
    """테스트 모드에서는 테스트 환경변수 우선, 아니면 OS 환경변수"""
    if _test_mode and key in _test_env_vars:
        return _test_env_vars[key]
    return os.getenv(key, default)


# 환경별 .env 로드
def _should_load_dotenv() -> bool:
    """환경에 따라 .env 로드 여부 결정"""
    app_env = _get_env("APP_ENV", "production")
    return app_env == "development"


def _load_dotenv_if_needed():
    """필요한 경우에만 .env 파일 로드"""
    if _should_load_dotenv() and not _test_mode:
        try:
            import os
            import sys

            from dotenv import load_dotenv

            # PyInstaller 환경에서의 경로 처리
            if getattr(sys, "frozen", False):
                # PyInstaller로 빌드된 경우 - exe와 같은 디렉토리에서 .env 찾기
                exe_dir = os.path.dirname(sys.executable)
                env_path = os.path.join(exe_dir, ".env")
            else:
                # 일반 Python 환경
                env_path = ".env"

            load_dotenv(env_path, override=False)
        except ImportError:
            pass


# 초기 로드
_load_dotenv_if_needed()


class TestModeEnvSource(PydanticBaseSettingsSource):
    """테스트 모드에서 환경변수 오버라이드를 위한 소스"""

    def get_field_value(self, field_info, field_name: str) -> Tuple[Any, str, bool]:
        # 테스트 모드에서 환경변수 오버라이드
        if _test_mode and field_name in _test_env_vars:
            return _test_env_vars[field_name], field_name, False

        # 일반 모드에서는 환경변수 읽기
        env_val = _get_env(field_name.upper())

        # EMAIL_SENDER fallback 지원
        if field_name == "email_sender" and env_val is None:
            env_val = _get_env("POSTMARK_FROM_EMAIL")

        if env_val is not None:
            return env_val, field_name, False

        return None, field_name, False

    def prepare_field_value(
        self, field_name: str, field: Any, value: Any, value_is_complex: bool
    ) -> Any:
        return value

    def __call__(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}

        if self.settings_cls.model_config.get("case_sensitive"):
            prepare_field_value = self.prepare_field_value
        else:
            prepare_field_value = lambda field_name, field, value, value_is_complex: self.prepare_field_value(
                field_name, field, value, value_is_complex
            )

        for field_name, field in self.settings_cls.model_fields.items():
            field_value, field_key, value_is_complex = self.get_field_value(
                field, field_name
            )
            if field_value is not None:
                d[field_name] = prepare_field_value(
                    field_name, field, field_value, value_is_complex
                )

        return d


class CentralizedSettings(BaseSettings):
    """중앙집중식 애플리케이션 설정"""

    # 필수 설정 (F-14: SERPER_API_KEY를 Optional로 변경)
    serper_api_key: SecretStr | None = None
    postmark_server_token: SecretStr | None = Field(None, description="Postmark 서버 토큰")
    email_sender: str | None = Field(None, description="발송자 이메일")

    # LLM API 키 (하나 이상 필수)
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None

    # LLM 성능 설정 (F-14: 중앙화된 성능 관리)
    llm_request_timeout: int = Field(120, description="LLM API 요청 타임아웃 (초)")
    llm_test_timeout: int = Field(60, description="테스트용 LLM 타임아웃 (초)")
    llm_max_retries: int = Field(3, description="LLM API 재시도 횟수")
    llm_retry_delay: float = Field(1.0, description="재시도 간격 (초)")

    # 성능 최적화 설정
    enable_fast_mode: bool = Field(False, description="빠른 모드 활성화")
    batch_processing: bool = Field(True, description="배치 처리 활성화")
    concurrent_requests: int = Field(5, description="동시 요청 수")

    # F-14: 테스트 모드 설정
    test_mode: bool = Field(False, description="테스트 모드 활성화")
    mock_api_responses: bool = Field(False, description="API 응답 모킹 활성화")
    skip_real_api_calls: bool = Field(False, description="실제 API 호출 건너뛰기")
    test_api_key_override: bool = Field(False, description="테스트용 API 키 오버라이드")

    # 공통 설정
    secret_key: str = Field("dev-secret-key-change-in-production", min_length=16)
    port: int = Field(8000, ge=1, le=65535)
    # Bandit B104: 프로덕션 환경에서만 0.0.0.0 바인딩 (보안 검증됨)  # nosec B104
    host: str = Field("0.0.0.0")  # nosec B104
    app_env: Literal["development", "testing", "production"] = Field("production")

    # 선택적 설정
    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = Field(0.1)
    sentry_profiles_sample_rate: float = Field(0.1)
    log_level: str = Field("INFO")
    log_format: str = Field("standard")
    mock_mode: bool = Field(False)
    debug: bool = Field(False)
    environment: str = Field("production")
    app_version: str = Field("1.0.0")

    # 데이터베이스 & Queue 설정
    redis_url: str = Field("redis://localhost:6379/0")
    rq_queue: str = Field("default")
    database_url: str | None = None

    # Google 통합 설정
    google_application_credentials: str | None = None
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None

    # Naver API 설정
    naver_client_id: str | None = None
    naver_client_secret: SecretStr | None = None

    # 기타 설정
    default_period: int = Field(14)
    default_template_style: str = Field("compact")
    additional_rss_feeds: str | None = None
    test_base_url: str | None = None
    test_email_recipient: str | None = None
    railway_production_url: str | None = None
    production_url: str | None = None

    # 경로 설정
    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent.parent

    @property
    def config_dir(self) -> Path:
        return self.base_dir / "config"

    @property
    def output_dir(self) -> Path:
        # Check for web environment override first
        web_output_dir = _get_env("NEWSLETTER_OUTPUT_DIR")
        if web_output_dir:
            return Path(web_output_dir)
        return self.base_dir / "output"

    # 모델 설정
    model_config = SettingsConfigDict(
        env_file=".env" if _should_load_dotenv() else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """설정 소스 커스터마이즈 - 테스트 모드 지원"""
        # 테스트 모드에서는 테스트 환경변수 소스를 우선으로
        test_env_source = TestModeEnvSource(settings_cls)

        return (
            init_settings,  # 명시적으로 전달된 값이 최우선
            test_env_source,  # 테스트 모드 또는 일반 환경변수
            (dotenv_settings if not _test_mode else init_settings),  # 테스트 모드에서는 .env 무시
            file_secret_settings,
        )

    # 검증
    @field_validator("postmark_server_token")
    @classmethod
    def validate_api_keys(cls, v: SecretStr | None) -> SecretStr | None:
        # None인 경우는 허용
        if v is None:
            return v
        # 테스트 모드에서는 검증 우회
        if _test_mode:
            return v
        if len(v.get_secret_value()) < 16:
            raise ValueError("API key must be >= 16 characters")
        return v

    @field_validator("serper_api_key")
    @classmethod
    def validate_optional_serper_key(cls, v: SecretStr | None) -> SecretStr | None:
        # None인 경우는 허용
        if v is None:
            return v
        # 테스트 모드에서는 검증 우회
        if _test_mode:
            return v
        if len(v.get_secret_value()) < 16:
            raise ValueError("API key must be >= 16 characters")
        return v

    def model_post_init(self, __context) -> None:
        """LLM 키 검증 및 디렉토리 생성"""
        # F-14: 테스트 모드 자동 감지 및 설정
        import os
        import sys

        # 명시적으로 F14_FORCE_VALIDATION이 설정된 경우 검증 강제 실행
        force_validation = os.getenv("F14_FORCE_VALIDATION") == "1"

        # pytest 실행 중이거나 TESTING 환경변수가 설정된 경우 테스트 모드 활성화
        # 단, 검증 강제 모드가 아닌 경우에만
        if not force_validation and (
            "pytest" in sys.modules or os.getenv("TESTING") == "1"
        ):
            self.test_mode = True
            self.mock_api_responses = True
            self.skip_real_api_calls = True

        # 테스트 모드에서는 LLM 키 검증 우회 (검증 강제 모드가 아닌 경우)
        if not force_validation and self.test_mode:
            pass  # 검증 우회
        else:
            # 실제 검증 수행
            llm_keys = [
                self.openai_api_key,
                self.anthropic_api_key,
                self.gemini_api_key,
            ]
            if not any(key is not None for key in llm_keys):
                raise ValueError("At least one LLM API key is required")

        # 디렉토리 생성
        for dir_path in [self.output_dir, self.config_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def get_config_summary(self) -> dict:
        """설정 요약 (보안 정보 마스킹)"""
        return {
            "app_env": self.app_env,
            "log_level": self.log_level,
            "mock_mode": self.mock_mode,
            "port": self.port,
            "has_serper_key": bool(self.serper_api_key),
            "has_openai_key": bool(self.openai_api_key),
            "has_anthropic_key": bool(self.anthropic_api_key),
            "has_gemini_key": bool(self.gemini_api_key),
            "has_postmark_token": bool(self.postmark_server_token),
        }


# Note: clear_settings_cache function is defined above to avoid duplicates


@lru_cache
def get_settings() -> CentralizedSettings:
    """설정 싱글톤 반환"""
    try:
        return CentralizedSettings()
    except Exception as e:
        logging.critical(f"Settings validation failed: {e}")
        raise


# Secret 마스킹 필터
class _SecretFilter(logging.Filter):
    """로그에서 시크릿 값을 마스킹하는 필터"""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            settings = get_settings()
            msg = str(record.msg)

            # SecretStr 값들 마스킹
            secrets = [
                ("SERPER_API_KEY", settings.serper_api_key),
                ("POSTMARK_SERVER_TOKEN", settings.postmark_server_token),
                ("OPENAI_API_KEY", settings.openai_api_key),
                ("ANTHROPIC_API_KEY", settings.anthropic_api_key),
                ("GEMINI_API_KEY", settings.gemini_api_key),
            ]

            for name, secret in secrets:
                if secret is not None:
                    secret_value = secret.get_secret_value()
                    if secret_value in msg:
                        masked = f"•••••••••••• ({name}, len: {len(secret_value)})"
                        msg = msg.replace(secret_value, masked)

            record.msg = msg
        except Exception as e:
            handle_exception(e, "로그 메시지 설정", log_level=logging.DEBUG)
            # 에러가 나도 로그는 남겨야 함

        return True


def setup_secret_logging():
    """시크릿 마스킹 로거 설정"""
    root_logger = logging.getLogger()
    secret_filter = _SecretFilter()
    root_logger.addFilter(secret_filter)


@dataclass
class F14PerformanceSettings:
    """F-14 중앙화된 성능 설정 클래스"""

    # 기본 설정값들
    llm_request_timeout: int = 120  # LLM API 요청 타임아웃 (초)
    llm_test_timeout: int = 60  # 테스트 전용 타임아웃 (초)
    llm_max_retries: int = 3  # 최대 재시도 횟수
    llm_retry_delay: float = 1.0  # 재시도 지연 시간 (초)
    enable_fast_mode: bool = False  # 빠른 모드 활성화
    batch_processing: bool = True  # 배치 처리 활성화
    concurrent_requests: int = 5  # 동시 요청 수 제한

    # F-14: 테스트 모드 설정 추가
    test_mode: bool = False  # 테스트 모드 (기본값: False)
    mock_api_responses: bool = False  # API 응답 모킹 비활성화
    skip_real_api_calls: bool = False  # 실제 API 호출 활성화
    test_api_key_override: bool = False  # 테스트용 API 키 오버라이드 비활성화
