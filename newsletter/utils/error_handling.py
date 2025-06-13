"""
예외 처리 유틸리티
"""

import logging
from typing import Optional, Any, Callable
from functools import wraps

logger = logging.getLogger(__name__)


def handle_exception(
    e: Exception,
    context: str,
    fallback_value: Any = None,
    log_level: int = logging.WARNING,
    should_raise: bool = False,
) -> Any:
    """
    예외를 일관되게 처리하는 유틸리티 함수

    Args:
        e: 발생한 예외
        context: 예외가 발생한 컨텍스트 설명
        fallback_value: 예외 발생시 반환할 기본값
        log_level: 로깅 레벨
        should_raise: 예외를 다시 발생시킬지 여부

    Returns:
        fallback_value 또는 None
    """
    error_msg = f"{context} 중 오류 발생: {str(e)}"
    logger.log(log_level, error_msg, exc_info=True)

    if should_raise:
        raise e

    return fallback_value


def safe_operation(
    context: str,
    fallback_value: Any = None,
    log_level: int = logging.WARNING,
    should_raise: bool = False,
) -> Callable:
    """
    안전한 작업 수행을 위한 데코레이터

    Args:
        context: 작업 컨텍스트 설명
        fallback_value: 예외 발생시 반환할 기본값
        log_level: 로깅 레벨
        should_raise: 예외를 다시 발생시킬지 여부

    Returns:
        데코레이터 함수
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return handle_exception(
                    e, context, fallback_value, log_level, should_raise
                )

        return wrapper

    return decorator
