"""
보안 관련 설정을 중앙화하는 모듈
"""

import os
from typing import Final, List, Dict
from pydantic import BaseModel, SecretStr, Field


class SecurityConfig(BaseModel):
    """보안 관련 설정"""

    # CORS 설정
    ALLOWED_ORIGINS: List[str] = Field(
        default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "*").split(","),
        description="허용된 CORS 오리진",
    )
    ALLOWED_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    ALLOWED_HEADERS: List[str] = ["*"]

    # 보안 헤더 설정
    SECURITY_HEADERS: Dict[str, str] = {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
    }

    # 레이트 리미팅 설정
    RATE_LIMIT_ENABLED: bool = Field(
        default=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    )
    RATE_LIMIT_REQUESTS: int = Field(
        default=int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    )
    RATE_LIMIT_WINDOW: int = Field(default=int(os.getenv("RATE_LIMIT_WINDOW", "3600")))

    # 세션 설정
    SESSION_COOKIE_SECURE: bool = Field(
        default=os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true"
    )
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"

    # 파일 업로드 설정
    MAX_UPLOAD_SIZE: int = Field(
        default=int(os.getenv("MAX_UPLOAD_SIZE", str(10 * 1024 * 1024)))
    )
    ALLOWED_EXTENSIONS: List[str] = [".txt", ".pdf", ".doc", ".docx"]

    # API 보안 설정
    API_KEY_HEADER: str = "X-API-Key"
    JWT_SECRET_KEY: SecretStr = Field(
        default_factory=lambda: SecretStr(
            os.getenv("JWT_SECRET_KEY", "change-this-in-production")
        )
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    )

    # 로깅 설정
    SENSITIVE_FIELDS: List[str] = [
        "password",
        "token",
        "api_key",
        "secret",
        "credit_card",
    ]

    # 신뢰할 수 있는 호스트 설정
    ALLOWED_HOSTS: List[str] = Field(
        default_factory=lambda: os.getenv("ALLOWED_HOSTS", "*").split(",")
    )

    # 로그 파일 설정
    LOG_DIR: str = Field(default=os.getenv("LOG_DIR", "logs"))
    SECURITY_AUDIT_LOG: str = Field(
        default=os.getenv("SECURITY_AUDIT_LOG", "security_audit.log")
    )
    APPLICATION_LOG: str = Field(
        default=os.getenv("APPLICATION_LOG", "application.log")
    )


# 상수 정의
SECURE_HEADERS: Final[Dict[str, str]] = SecurityConfig().SECURITY_HEADERS
REQUEST_TIMEOUT: Final[int] = 30  # 초
MAX_RETRIES: Final[int] = 3
