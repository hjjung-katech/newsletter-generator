from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

import yaml  # type: ignore[import-untyped]
from pydantic import SecretStr

DEFAULT_CONFIG_PATHS = ("config/config.yml", "config.yml")
_DEFAULT_NEWSLETTER_SETTINGS = {
    "newsletter_title": "주간 산업 동향 뉴스 클리핑",
    "tagline": "이번 주, 주요 산업 동향을 미리 만나보세요.",
    "publisher_name": "Your Company",
    "company_name": "Your Company",
    "company_tagline": "",
    "editor_name": "",
    "editor_title": "편집자",
    "editor_email": "",
    "footer_disclaimer": "이 뉴스레터는 정보 제공을 목적으로 하며, 내용의 정확성을 보장하지 않습니다.",
    "footer_contact": "",
}
_DEFAULT_SCORING_WEIGHTS = {
    "relevance": 0.35,
    "impact": 0.25,
    "novelty": 0.15,
    "source_tier": 0.15,
    "recency": 0.10,
}
_MAJOR_NEWS_SOURCES = {
    "tier1": [
        "조선일보",
        "중앙일보",
        "동아일보",
        "한국일보",
        "한겨레",
        "경향신문",
        "매일경제",
        "한국경제",
        "서울경제",
        "파이낸셜뉴스",
        "연합뉴스",
        "YTN",
        "KBS",
        "MBC",
        "SBS",
        "JTBC",
        "Bloomberg",
        "Reuters",
        "Wall Street Journal",
        "Financial Times",
        "The Economist",
    ],
    "tier2": [
        "뉴시스",
        "뉴스1",
        "아시아경제",
        "아주경제",
        "이데일리",
        "머니투데이",
        "비즈니스워치",
        "디지털타임스",
        "전자신문",
        "IT조선",
        "ZDNet Korea",
        "디지털데일리",
        "테크M",
        "블로터",
        "채널A",
        "MBN",
        "TV조선",
        "TechCrunch",
        "Wired",
    ],
}


def _read_secret(value: SecretStr | None) -> str | None:
    return value.get_secret_value() if value is not None else None


def _build_default_llm_config() -> Dict[str, Any]:
    return {
        "default_provider": "gemini",
        "api_keys": {
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        },
        "models": {
            "keyword_generation": {
                "provider": "gemini",
                "model": "gemini-2.5-pro-preview-03-25",
                "temperature": 0.7,
                "max_retries": 2,
                "timeout": 60,
            },
            "theme_extraction": {
                "provider": "gemini",
                "model": "gemini-1.5-flash-latest",
                "temperature": 0.2,
                "max_retries": 2,
                "timeout": 60,
            },
            "news_summarization": {
                "provider": "gemini",
                "model": "gemini-2.5-pro-preview-03-25",
                "temperature": 0.3,
                "max_retries": 3,
                "timeout": 120,
            },
            "section_regeneration": {
                "provider": "gemini",
                "model": "gemini-1.5-pro",
                "temperature": 0.3,
                "max_retries": 2,
                "timeout": 120,
            },
            "introduction_generation": {
                "provider": "gemini",
                "model": "gemini-1.5-pro",
                "temperature": 0.4,
                "max_retries": 2,
                "timeout": 60,
            },
            "html_generation": {
                "provider": "gemini",
                "model": "gemini-2.5-pro-preview-03-25",
                "temperature": 0.2,
                "max_retries": 3,
                "timeout": 180,
            },
        },
        "provider_models": {
            "gemini": {
                "fast": "gemini-1.5-flash-latest",
                "standard": "gemini-1.5-pro",
                "advanced": "gemini-2.5-pro-preview-03-25",
            },
            "openai": {
                "fast": "gpt-4o-mini",
                "standard": "gpt-4o",
                "advanced": "gpt-4o",
            },
            "anthropic": {
                "fast": "claude-3-haiku-20240307",
                "standard": "claude-3-sonnet-20240229",
                "advanced": "claude-3-5-sonnet-20241022",
            },
        },
    }


def _resolve_llm_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    llm_settings = config_data.get("llm_settings", {})
    if not isinstance(llm_settings, dict) or not llm_settings:
        return _build_default_llm_config()
    return llm_settings


def _resolve_newsletter_settings(config_data: Dict[str, Any]) -> Dict[str, Any]:
    newsletter_settings = config_data.get("newsletter_settings", {})
    merged_settings = deepcopy(_DEFAULT_NEWSLETTER_SETTINGS)
    if isinstance(newsletter_settings, dict):
        merged_settings.update(newsletter_settings)
    return merged_settings


def _resolve_scoring_weights(
    config_data: Dict[str, Any],
    log_warning: Callable[[str], None],
) -> Dict[str, float]:
    scoring_config = config_data.get("scoring", {})
    default_weights = dict(_DEFAULT_SCORING_WEIGHTS)

    if not scoring_config:
        return default_weights

    required_keys = set(default_weights.keys())
    config_keys = set(scoring_config.keys())

    if not required_keys.issubset(config_keys):
        missing_keys = required_keys - config_keys
        log_warning(f"스코어링 가중치 키가 누락되었습니다: {missing_keys}. 기본값을 사용합니다.")
        return default_weights

    try:
        weights = {k: float(scoring_config[k]) for k in required_keys}
        total = sum(weights.values())
        if abs(total - 1.0) < 0.01:
            return weights
        log_warning(f"스코어링 가중치의 합이 {total:.3f}이며 1.0이 아닙니다. 기본값을 사용합니다.")
        return default_weights
    except (ValueError, TypeError) as e:
        log_warning(f"스코어링 가중치 값이 올바르지 않습니다: {e}. 기본값을 사용합니다.")
        return default_weights


def _clone_major_news_sources() -> Dict[str, list[str]]:
    return {tier: list(sources) for tier, sources in _MAJOR_NEWS_SOURCES.items()}


def _validate_email_settings(
    postmark_server_token: str | None,
    email_sender: str | None,
) -> Dict[str, bool]:
    token_valid = bool(
        postmark_server_token
        and postmark_server_token
        not in [
            "your_postmark_server_token_here",
            "your-postmark-server-token-here",
        ]
    )

    email_valid = bool(
        email_sender
        and email_sender
        not in ["noreply@yourdomain.com", "your_verified_email@yourdomain.com"]
    )

    return {
        "postmark_token_configured": token_valid,
        "from_email_configured": email_valid,
        "ready": token_valid and email_valid,
    }


class ConfigFileLoader:
    """YAML config file loading and cache alias management."""

    def __init__(
        self,
        cache: Dict[str, Dict[str, Any]],
        log_warning: Callable[[str], None],
    ) -> None:
        self._cache = cache
        self._log_warning = log_warning

    def load(self, config_file: str = "config.yml") -> Dict[str, Any]:
        cached = self._cache.get(config_file)
        if cached is not None:
            return cached

        config_candidates = self.resolve_candidates(config_file)
        resolved_config_path = next(
            (candidate for candidate in config_candidates if candidate.exists()),
            None,
        )
        if resolved_config_path is None:
            search_paths = ", ".join(str(candidate) for candidate in config_candidates)
            self._log_warning(
                f"설정 파일을 찾을 수 없습니다: {config_file} (searched: {search_paths})"
            )
            return {}

        resolved_key = str(resolved_config_path)
        resolved_cached = self._cache.get(resolved_key)
        if resolved_cached is not None:
            self._cache[config_file] = resolved_cached
            return resolved_cached

        try:
            config_data = self._read_yaml_file(resolved_config_path)
        except Exception as e:
            self._log_warning(f"설정 파일 로딩 실패 {resolved_config_path}: {e}")
            return {}

        self._cache[resolved_key] = config_data
        self._cache[config_file] = config_data
        return config_data

    @staticmethod
    def resolve_candidates(config_file: str) -> list[Path]:
        """기본 경로/레거시 경로를 포함해 탐색 후보를 반환합니다."""
        config_path = Path(config_file)
        if config_path.is_absolute():
            return [config_path]

        normalized = config_file.replace("\\", "/").lstrip("./")
        if normalized in {"config.yml", "config/config.yml"}:
            return [Path(path) for path in DEFAULT_CONFIG_PATHS]

        return [config_path]

    @staticmethod
    def _read_yaml_file(config_path: Path) -> Dict[str, Any]:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}


class ConfigManager:
    """중앙 집중식 설정 관리자"""

    _instance: "ConfigManager | None" = None
    _config_cache: Dict[str, Dict[str, Any]] = {}

    def __new__(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._config_loader = ConfigFileLoader(
                self._config_cache, self._log_warning
            )
            self._load_environment_variables()

    @classmethod
    def reset_for_testing(cls, test_env_vars: Dict[str, str] | None = None) -> None:
        """테스트용으로 싱글톤 인스턴스와 캐시를 리셋합니다."""
        cls._instance = None
        cls._config_cache = {}

        # CentralizedSettings 캐시도 클리어하고 테스트 모드 활성화
        try:
            from newsletter.centralized_settings import enable_test_mode

            if test_env_vars:
                enable_test_mode(test_env_vars)
        except ImportError:
            pass

    def _load_environment_variables(self) -> None:
        """환경 변수 로딩 - Centralized Settings 단일 경로 사용"""
        from newsletter.centralized_settings import get_settings

        settings = get_settings()

        self.SERPER_API_KEY = _read_secret(settings.serper_api_key)
        self.GEMINI_API_KEY = _read_secret(settings.gemini_api_key)
        self.OPENAI_API_KEY = _read_secret(settings.openai_api_key)
        self.ANTHROPIC_API_KEY = _read_secret(settings.anthropic_api_key)

        self.GOOGLE_APPLICATION_CREDENTIALS = settings.google_application_credentials
        self.GOOGLE_CLIENT_ID = settings.google_client_id
        self.GOOGLE_CLIENT_SECRET = _read_secret(settings.google_client_secret)

        self.NAVER_CLIENT_ID = settings.naver_client_id
        self.NAVER_CLIENT_SECRET = _read_secret(settings.naver_client_secret)

        self.EMAIL_SENDER = settings.email_sender
        self.POSTMARK_SERVER_TOKEN = _read_secret(settings.postmark_server_token)
        self.ADDITIONAL_RSS_FEEDS = settings.additional_rss_feeds or ""

    def load_config_file(self, config_file: str = "config.yml") -> Dict[str, Any]:
        """YAML 설정 파일 로딩 (캐시 지원)"""
        return self._config_loader.load(config_file)

    @staticmethod
    def _resolve_config_candidates(config_file: str) -> list[Path]:
        return ConfigFileLoader.resolve_candidates(config_file)

    def get_llm_config(self) -> Dict[str, Any]:
        """LLM 설정 반환"""
        return _resolve_llm_config(self.load_config_file())

    def get_newsletter_settings(self) -> Dict[str, Any]:
        """뉴스레터 설정 반환"""
        return _resolve_newsletter_settings(self.load_config_file())

    def get_scoring_weights(self) -> Dict[str, float]:
        """스코어링 가중치 반환"""
        return _resolve_scoring_weights(self.load_config_file(), self._log_warning)

    def _get_default_llm_config(self) -> Dict[str, Any]:
        """기본 LLM 설정 반환"""
        return _build_default_llm_config()

    def get_major_news_sources(self) -> Dict[str, list]:
        """주요 언론사 목록 반환"""
        return _clone_major_news_sources()

    def validate_email_config(self) -> Dict[str, bool]:
        """이메일 설정 검증"""
        return _validate_email_settings(
            self.POSTMARK_SERVER_TOKEN,
            self.EMAIL_SENDER,
        )

    def _log_warning(self, message: str) -> None:
        """경고 메시지 출력"""
        try:
            from .utils.logger import get_logger

            logger = get_logger()
            logger.warning(message)
        except ImportError:
            print(f"[WARNING] {message}")


# 싱글톤 인스턴스 (지연 초기화)
_config_manager_instance: ConfigManager | None = None


def get_config_manager() -> ConfigManager:
    """설정 관리자 싱글톤 인스턴스 반환 (지연 초기화)"""
    global _config_manager_instance
    if _config_manager_instance is None:
        _config_manager_instance = ConfigManager()
    return _config_manager_instance


def get_llm_config() -> Dict[str, Any]:
    return _resolve_llm_config(get_config_manager().load_config_file())


def get_newsletter_settings() -> Dict[str, Any]:
    return _resolve_newsletter_settings(get_config_manager().load_config_file())


def get_scoring_weights() -> Dict[str, float]:
    manager = get_config_manager()
    return _resolve_scoring_weights(manager.load_config_file(), manager._log_warning)


def get_major_news_sources() -> Dict[str, list[str]]:
    return _clone_major_news_sources()


def validate_email_config() -> Dict[str, bool]:
    manager = get_config_manager()
    return _validate_email_settings(
        manager.POSTMARK_SERVER_TOKEN,
        manager.EMAIL_SENDER,
    )


# 하위 호환성을 위한 별칭
class _LazyConfigManager:
    """Lazy proxy to prevent eager settings initialization at import time."""

    def __getattr__(self, item: str) -> Any:
        return getattr(get_config_manager(), item)

    def __repr__(self) -> str:  # pragma: no cover
        return "<LazyConfigManager proxy>"


config_manager = _LazyConfigManager()
