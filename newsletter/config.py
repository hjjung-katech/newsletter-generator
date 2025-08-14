import os
from pathlib import Path

# 순환 import 방지를 위한 lazy import
def _get_config_manager():
    """config_manager를 lazy import로 가져오기"""
    try:
        from .config_manager import config_manager
        return config_manager
    except Exception:
        # 테스트 환경이나 import 실패 시 fallback
        class MockConfigManager:
            def __init__(self):
                self.SERPER_API_KEY = os.getenv('SERPER_API_KEY')
                self.GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
                self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
                self.ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
                self.GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                self.NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
                self.NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')
                self.ADDITIONAL_RSS_FEEDS = os.getenv('ADDITIONAL_RSS_FEEDS', "")
                self.POSTMARK_SERVER_TOKEN = os.getenv('POSTMARK_SERVER_TOKEN')
                self.EMAIL_SENDER = os.getenv('EMAIL_SENDER') or os.getenv('POSTMARK_FROM_EMAIL')
                self.GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
                self.GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
        
            def get_llm_config(self):
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
                            "model": "gemini-2.0-flash-exp",
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
                            "model": "gemini-2.0-flash-exp",
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
                            "model": "gemini-2.0-flash-exp",
                            "temperature": 0.2,
                            "max_retries": 3,
                            "timeout": 180,
                        },
                    },
                    "provider_models": {
                        "gemini": {
                            "fast": "gemini-1.5-flash-latest",
                            "standard": "gemini-1.5-pro",
                            "advanced": "gemini-2.0-flash-exp",
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
            
            def get_major_news_sources(self):
                return {
                    "tier1": ["연합뉴스", "조선일보", "중앙일보", "동아일보", "한국일보", "경향신문"],
                    "tier2": ["매일경제", "한국경제", "서울경제", "이데일리", "뉴스1", "뉴시스"]
                }
        
        return MockConfigManager()

# config_manager 인스턴스 가져오기
config_manager = _get_config_manager()

# 하위 호환성을 위한 변수들 (ConfigManager에서 가져옴)
SERPER_API_KEY = config_manager.SERPER_API_KEY
GEMINI_API_KEY = config_manager.GEMINI_API_KEY
OPENAI_API_KEY = config_manager.OPENAI_API_KEY
ANTHROPIC_API_KEY = config_manager.ANTHROPIC_API_KEY
GOOGLE_APPLICATION_CREDENTIALS = config_manager.GOOGLE_APPLICATION_CREDENTIALS
NAVER_CLIENT_ID = config_manager.NAVER_CLIENT_ID
NAVER_CLIENT_SECRET = config_manager.NAVER_CLIENT_SECRET
ADDITIONAL_RSS_FEEDS = config_manager.ADDITIONAL_RSS_FEEDS

# 이메일 발송 설정 (Postmark 사용)
POSTMARK_SERVER_TOKEN = config_manager.POSTMARK_SERVER_TOKEN
EMAIL_SENDER = config_manager.EMAIL_SENDER

# Google Drive 설정
GOOGLE_CLIENT_ID = config_manager.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = config_manager.GOOGLE_CLIENT_SECRET

# LLM 설정
LLM_CONFIG = config_manager.get_llm_config()

# 주요 언론사 설정
MAJOR_NEWS_SOURCES = config_manager.get_major_news_sources()

# 호환성을 위한 flat한 주요 언론사 목록 (tier1 + tier2)
ALL_MAJOR_NEWS_SOURCES = MAJOR_NEWS_SOURCES["tier1"] + MAJOR_NEWS_SOURCES["tier2"]

# Mock 모드 설정 - 환경 변수에서 로드, 기본값은 False
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

# 경고 메시지 출력 (ConfigManager에서 처리하므로 간소화)
def log_message(level, message):
    """로거가 없는 경우를 위한 fallback 함수"""
    # 테스트 환경에서는 경고 최소화
    if 'pytest' in os.getenv('_', '') or os.getenv('TESTING') == '1':
        return
    try:
        from .utils.logger import get_logger
        logger = get_logger()
        getattr(logger, level)(message)
    except ImportError:
        print(f"[{level.upper()}] {message}")

# 테스트가 아닌 경우에만 경고 메시지 출력
if not ('pytest' in os.getenv('_', '') or os.getenv('TESTING') == '1'):
    # 필수 API 키 검증
    if not SERPER_API_KEY:
        log_message("warning", "Warning: SERPER_API_KEY not found in .env file.")
    if not GEMINI_API_KEY:
        log_message(
            "warning",
            "Warning: GEMINI_API_KEY not found in .env file. Gemini-based features may not work.",
        )

    # 새로 추가된 LLM API 키 경고
    if not OPENAI_API_KEY:
        log_message(
            "info",
            "Note: OPENAI_API_KEY not found in .env file. OpenAI/ChatGPT features will be disabled.",
        )
    if not ANTHROPIC_API_KEY:
        log_message(
            "info",
            "Note: ANTHROPIC_API_KEY not found in .env file. Anthropic/Claude features will be disabled.",
        )

    # 선택적 API 키
    if not GOOGLE_APPLICATION_CREDENTIALS:
        log_message(
            "warning",
            "Warning: GOOGLE_APPLICATION_CREDENTIALS not found in .env file. Google Drive upload will not work.",
        )

    # Postmark 설정 경고
    if not POSTMARK_SERVER_TOKEN:
        log_message(
            "warning",
            "Warning: POSTMARK_SERVER_TOKEN not found in .env file. Email sending will not work.",
        )

    # 새로 추가된 API 키에 대한 경고 (선택적)
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        log_message(
            "info",
            "Note: Naver News API credentials not found. Naver News API source will be disabled.",
        )

    if MOCK_MODE:
        log_message(
            "warning", "Running in MOCK MODE - using sample data instead of real API calls"
        )