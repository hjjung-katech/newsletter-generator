"""
구조화된 로깅 설정 모듈
JSON 포맷으로 로그를 출력하고 환경 변수로 레벨 조정
"""

import os
import sys
import logging
import logging.config
import json
from datetime import datetime
from typing import Dict, Any


class JSONFormatter(logging.Formatter):
    """JSON 형태로 로그를 포맷하는 커스텀 포맷터"""

    def format(self, record: logging.LogRecord) -> str:
        # 기본 로그 정보
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 예외 정보 추가
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 추가 필드들 (로그 호출 시 extra로 전달된 것들)
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # 서비스 정보
        log_data["service"] = "newsletter-generator"
        log_data["environment"] = os.getenv("ENVIRONMENT", "development")

        # 프로세스 정보
        log_data["process_id"] = os.getpid()

        return json.dumps(log_data, ensure_ascii=False)


class StructuredAdapter(logging.LoggerAdapter):
    """구조화된 로깅을 위한 어댑터"""

    def process(self, msg: Any, kwargs: Dict[str, Any]) -> tuple:
        # extra 필드를 처리
        if "extra" in kwargs:
            if not hasattr(kwargs["extra"], "extra_fields"):
                kwargs["extra"]["extra_fields"] = kwargs["extra"]
        else:
            kwargs["extra"] = {"extra_fields": {}}

        return msg, kwargs


# 로깅 설정 딕셔너리
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": JSONFormatter},
        "simple": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": (
                "json"
                if os.getenv("LOG_FORMAT", "json").lower() == "json"
                else "simple"
            ),
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": "logs/newsletter.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8",
        },
    },
    "loggers": {
        "newsletter": {
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "handlers": ["console"],
            "propagate": False,
        },
        "web": {
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "handlers": ["console"],
            "propagate": False,
        },
        "uvicorn": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "uvicorn.access": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    },
    "root": {"level": os.getenv("LOG_LEVEL", "INFO"), "handlers": ["console"]},
}


def setup_logging():
    """로깅 설정을 초기화합니다."""

    # 로그 디렉토리 생성
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # 로깅 설정 적용
    logging.config.dictConfig(LOGGING_CONFIG)

    # 루트 로거에 구조화 어댑터 적용
    logger = logging.getLogger()

    print(
        f"✅ Logging configured - Level: {os.getenv('LOG_LEVEL', 'INFO')}, Format: {os.getenv('LOG_FORMAT', 'json')}"
    )


def get_structured_logger(name: str) -> StructuredAdapter:
    """구조화된 로거를 반환합니다."""
    base_logger = logging.getLogger(name)
    return StructuredAdapter(base_logger, {})


def log_with_context(logger: logging.Logger, level: str, message: str, **context):
    """컨텍스트와 함께 로그를 기록합니다."""
    log_func = getattr(logger, level.lower())
    log_func(message, extra=context)


# 편의 함수들
def log_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **kwargs,
):
    """HTTP 요청 로그"""
    log_with_context(
        logger,
        "info",
        f"{method} {path} - {status_code}",
        request_method=method,
        request_path=path,
        response_status=status_code,
        duration_ms=duration_ms,
        **kwargs,
    )


def log_error(logger: logging.Logger, error: Exception, context: str = "", **kwargs):
    """에러 로그"""
    log_with_context(
        logger,
        "error",
        f"Error in {context}: {str(error)}",
        error_type=type(error).__name__,
        error_message=str(error),
        context=context,
        **kwargs,
    )


def log_performance(
    logger: logging.Logger, operation: str, duration_ms: float, **kwargs
):
    """성능 로그"""
    log_with_context(
        logger,
        "info",
        f"Performance: {operation} completed in {duration_ms:.2f}ms",
        operation=operation,
        duration_ms=duration_ms,
        **kwargs,
    )


# 모듈 로드 시 자동 설정
if __name__ != "__main__":
    setup_logging()
