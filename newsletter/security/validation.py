"""
입력 검증 유틸리티
"""

import re
from typing import Any, List, Optional, Pattern
from pathlib import Path

from pydantic import BaseModel, validator
from fastapi import UploadFile

from .config import SecurityConfig

security_config = SecurityConfig()


class InputValidationError(Exception):
    """입력 검증 오류"""

    pass


class FileValidationError(InputValidationError):
    """파일 검증 오류"""

    pass


def validate_file_extension(
    filename: str, allowed_extensions: Optional[List[str]] = None
) -> bool:
    """파일 확장자 검증

    Args:
        filename: 검증할 파일명
        allowed_extensions: 허용된 확장자 목록. None인 경우 기본 설정 사용

    Returns:
        bool: 유효한 확장자인 경우 True
    """
    if allowed_extensions is None:
        allowed_extensions = security_config.ALLOWED_EXTENSIONS

    return Path(filename).suffix.lower() in allowed_extensions


def validate_file_size(file_size: int, max_size: Optional[int] = None) -> bool:
    """파일 크기 검증

    Args:
        file_size: 검증할 파일 크기
        max_size: 최대 허용 크기. None인 경우 기본 설정 사용

    Returns:
        bool: 유효한 크기인 경우 True
    """
    if max_size is None:
        max_size = security_config.MAX_UPLOAD_SIZE

    return file_size <= max_size


async def validate_upload_file(file: UploadFile) -> None:
    """업로드된 파일 검증

    Args:
        file: 검증할 파일

    Raises:
        FileValidationError: 파일이 유효하지 않은 경우
    """
    if not validate_file_extension(file.filename):
        raise FileValidationError("허용되지 않는 파일 형식입니다")

    content = await file.read()
    if not validate_file_size(len(content)):
        raise FileValidationError("파일 크기가 너무 큽니다")

    # 파일 포인터를 다시 처음으로
    await file.seek(0)


class InputSanitizer:
    """입력값 살균 처리"""

    # XSS 공격 패턴 (컴파일된 정규식으로 성능 개선)
    XSS_PATTERNS: List[Pattern] = [
        re.compile(r"<script.*?>.*?</script>", re.I | re.S),
        re.compile(r"javascript:", re.I),
        re.compile(r"on\w+\s*=", re.I),
        re.compile(r"vbscript:", re.I),
        re.compile(r"<iframe.*?>", re.I),
        re.compile(r"<object.*?>", re.I),
        re.compile(r"<embed.*?>", re.I),
    ]

    # SQL 인젝션 패턴 (컴파일된 정규식으로 성능 개선)
    SQL_PATTERNS: List[Pattern] = [
        re.compile(r"(\%27)|(\')|(\-\-)|(\%23)|(#)", re.I),
        re.compile(r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))", re.I),
        re.compile(r"\w*((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))", re.I),
        re.compile(r"(\%27)|(\')|(\-\-)|(\%23)|(#)", re.I),
        re.compile(r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))", re.I),
    ]

    @classmethod
    def sanitize_string(cls, value: str) -> str:
        """문자열 살균 처리

        Args:
            value: 살균할 문자열

        Returns:
            살균된 문자열
        """
        if not isinstance(value, str):
            value = str(value)

        # HTML 이스케이프
        value = (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

        # XSS 패턴 제거
        for pattern in cls.XSS_PATTERNS:
            value = pattern.sub("", value)

        return value.strip()

    @classmethod
    def is_sql_injection(cls, value: str) -> bool:
        """SQL 인젝션 패턴 검사

        Args:
            value: 검사할 문자열

        Returns:
            SQL 인젝션 패턴이 발견된 경우 True
        """
        if not isinstance(value, str):
            value = str(value)

        return any(pattern.search(value) for pattern in cls.SQL_PATTERNS)


class SafeString(str):
    """안전한 문자열 타입"""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> str:
        """문자열 검증 및 살균

        Args:
            v: 검증할 값

        Returns:
            살균된 문자열

        Raises:
            ValueError: SQL 인젝션 패턴이 발견된 경우
        """
        if not isinstance(v, str):
            v = str(v)

        if InputSanitizer.is_sql_injection(v):
            raise ValueError("입력값이 유효하지 않습니다")

        return InputSanitizer.sanitize_string(v)


class SafeInput(BaseModel):
    """안전한 입력을 위한 기본 모델"""

    class Config:
        """Pydantic 설정"""

        arbitrary_types_allowed = True

    @validator("*", pre=True)
    def sanitize_strings(cls, v: Any) -> Any:
        """모든 문자열 필드 살균"""
        if isinstance(v, str):
            return SafeString.validate(v)
        return v
