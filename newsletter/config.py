import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 로깅 시스템 import (config 로드 후)
try:
    from .utils.logger import get_logger

    logger = get_logger()
except ImportError:
    # config.py가 먼저 로드되는 경우를 위한 fallback
    logger = None


def log_message(level, message):
    """로거가 없는 경우를 위한 fallback 함수"""
    if logger:
        getattr(logger, level)(message)
    else:
        print(f"[{level.upper()}] {message}")


# 기존 API 키 설정
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # 통합된 API 키
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # OpenAI API 키 추가
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")  # Anthropic API 키 추가
GOOGLE_APPLICATION_CREDENTIALS = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS"
)  # 새로 추가

# 새로운 API 키 설정
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")  # 네이버 API 클라이언트 ID
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")  # 네이버 API 클라이언트 시크릿
ADDITIONAL_RSS_FEEDS = os.getenv(
    "ADDITIONAL_RSS_FEEDS", ""
)  # 추가 RSS 피드 URL (쉼표로 구분)

# 이메일 발송 설정 (Postmark)
POSTMARK_SERVER_TOKEN = os.getenv("POSTMARK_SERVER_TOKEN")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")

# Google Drive 설정
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")


# LLM 설정을 위한 config.yml 로드
def load_llm_config():
    """config.yml에서 LLM 설정을 로드합니다."""
    try:
        with open("config.yml", "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
            return config_data.get("llm_settings", {})
    except FileNotFoundError:
        log_message(
            "warning", "Warning: config.yml not found. Using default LLM settings."
        )
        return get_default_llm_config()
    except Exception as e:
        log_message(
            "warning",
            f"Warning: Error loading config.yml: {e}. Using default LLM settings.",
        )
        return get_default_llm_config()


def get_default_llm_config():
    """기본 LLM 설정을 반환합니다."""
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


# LLM 설정 로드
LLM_CONFIG = load_llm_config()

# 경고 메시지 출력
# 필수 API 키
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
