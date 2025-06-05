import os
from pathlib import Path

from .config_manager import config_manager

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


# 경고 메시지 출력 (ConfigManager에서 처리하므로 간소화)
def log_message(level, message):
    """로거가 없는 경우를 위한 fallback 함수"""
    try:
        from .utils.logger import get_logger

        logger = get_logger()
        getattr(logger, level)(message)
    except ImportError:
        print(f"[{level.upper()}] {message}")


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

# Mock 모드 설정 - 환경 변수에서 로드, 기본값은 False
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"
if MOCK_MODE:
    log_message(
        "warning", "Running in MOCK MODE - using sample data instead of real API calls"
    )
