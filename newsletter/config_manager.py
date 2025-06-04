import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


class ConfigManager:
    """중앙 집중식 설정 관리자"""

    _instance = None
    _config_cache = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._load_environment_variables()

    @classmethod
    def reset_for_testing(cls):
        """테스트용으로 싱글톤 인스턴스와 캐시를 리셋합니다."""
        cls._instance = None
        cls._config_cache = {}

    def _load_environment_variables(self):
        """환경 변수 로딩"""
        # API 키들
        self.SERPER_API_KEY = os.getenv("SERPER_API_KEY")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

        # Google 관련
        self.GOOGLE_APPLICATION_CREDENTIALS = os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS"
        )
        self.GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
        self.GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

        # 네이버 API
        self.NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
        self.NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

        # 이메일 설정 통합 (POSTMARK_FROM_EMAIL은 호환성용)
        self.EMAIL_SENDER = os.getenv("EMAIL_SENDER") or os.getenv(
            "POSTMARK_FROM_EMAIL"
        )
        self.POSTMARK_SERVER_TOKEN = os.getenv("POSTMARK_SERVER_TOKEN")

        # 기타 설정
        self.ADDITIONAL_RSS_FEEDS = os.getenv("ADDITIONAL_RSS_FEEDS", "")

        # 호환성 경고
        if os.getenv("POSTMARK_FROM_EMAIL") and not os.getenv("EMAIL_SENDER"):
            self._log_warning(
                "POSTMARK_FROM_EMAIL은 deprecated됩니다. EMAIL_SENDER를 사용하세요."
            )

    def load_config_file(self, config_file: str = "config.yml") -> Dict[str, Any]:
        """YAML 설정 파일 로딩 (캐시 지원)"""
        if config_file in self._config_cache:
            return self._config_cache[config_file]

        try:
            config_path = Path(config_file)
            if not config_path.exists():
                self._log_warning(f"설정 파일을 찾을 수 없습니다: {config_file}")
                return {}

            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}

            self._config_cache[config_file] = config_data
            return config_data

        except Exception as e:
            self._log_warning(f"설정 파일 로딩 실패 {config_file}: {e}")
            return {}

    def get_llm_config(self) -> Dict[str, Any]:
        """LLM 설정 반환"""
        config_data = self.load_config_file()
        llm_settings = config_data.get("llm_settings", {})

        if not llm_settings:
            return self._get_default_llm_config()

        return llm_settings

    def get_newsletter_settings(self) -> Dict[str, Any]:
        """뉴스레터 설정 반환"""
        config_data = self.load_config_file()
        newsletter_settings = config_data.get("newsletter_settings", {})

        # 기본값과 병합
        default_settings = {
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

        default_settings.update(newsletter_settings)
        return default_settings

    def get_scoring_weights(self) -> Dict[str, float]:
        """스코어링 가중치 반환"""
        config_data = self.load_config_file()
        scoring_config = config_data.get("scoring", {})

        default_weights = {
            "recency": 0.3,
            "relevance": 0.4,
            "credibility": 0.2,
            "diversity": 0.1,
        }

        if not scoring_config:
            return default_weights

        # 필수 키 검증
        required_keys = set(default_weights.keys())
        config_keys = set(scoring_config.keys())

        if not required_keys.issubset(config_keys):
            missing_keys = required_keys - config_keys
            self._log_warning(
                f"스코어링 가중치 키가 누락되었습니다: {missing_keys}. 기본값을 사용합니다."
            )
            return default_weights

        try:
            weights = {k: float(scoring_config[k]) for k in required_keys}
            total = sum(weights.values())

            if abs(total - 1.0) < 0.01:  # 허용 오차
                return weights
            else:
                self._log_warning(
                    f"스코어링 가중치의 합이 {total:.3f}이며 1.0이 아닙니다. 기본값을 사용합니다."
                )
                return default_weights

        except (ValueError, TypeError) as e:
            self._log_warning(
                f"스코어링 가중치 값이 올바르지 않습니다: {e}. 기본값을 사용합니다."
            )
            return default_weights

    def _get_default_llm_config(self) -> Dict[str, Any]:
        """기본 LLM 설정 반환"""
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

    def get_major_news_sources(self) -> Dict[str, list]:
        """주요 언론사 목록 반환"""
        return {
            "tier1": [
                # 국내 주요 일간지
                "조선일보",
                "중앙일보",
                "동아일보",
                "한국일보",
                "한겨레",
                "경향신문",
                # 국내 주요 경제지
                "매일경제",
                "한국경제",
                "서울경제",
                "파이낸셜뉴스",
                # 국내 주요 방송/통신사
                "연합뉴스",
                "YTN",
                "KBS",
                "MBC",
                "SBS",
                "JTBC",
                # 해외 주요 언론사
                "Bloomberg",
                "Reuters",
                "Wall Street Journal",
                "Financial Times",
                "The Economist",
            ],
            "tier2": [
                # 국내 주요 통신사
                "뉴시스",
                "뉴스1",
                # 국내 경제/산업 전문지
                "아시아경제",
                "아주경제",
                "이데일리",
                "머니투데이",
                "비즈니스워치",
                # 국내 IT/기술 전문지
                "디지털타임스",
                "전자신문",
                "IT조선",
                "ZDNet Korea",
                "디지털데일리",
                "테크M",
                "블로터",
                # 국내 기타 방송사
                "채널A",
                "MBN",
                "TV조선",
                # 해외 기술 전문지
                "TechCrunch",
                "Wired",
            ],
        }

    def validate_email_config(self) -> Dict[str, bool]:
        """이메일 설정 검증"""
        token_valid = bool(
            self.POSTMARK_SERVER_TOKEN
            and self.POSTMARK_SERVER_TOKEN
            not in [
                "your_postmark_server_token_here",
                "your-postmark-server-token-here",
            ]
        )

        email_valid = bool(
            self.EMAIL_SENDER
            and self.EMAIL_SENDER
            not in ["noreply@yourdomain.com", "your_verified_email@yourdomain.com"]
        )

        return {
            "postmark_token_configured": token_valid,
            "from_email_configured": email_valid,
            "ready": token_valid and email_valid,
        }

    def _log_warning(self, message: str):
        """경고 메시지 출력"""
        try:
            from .utils.logger import get_logger

            logger = get_logger()
            logger.warning(message)
        except ImportError:
            print(f"[WARNING] {message}")


# 싱글톤 인스턴스
config_manager = ConfigManager()
