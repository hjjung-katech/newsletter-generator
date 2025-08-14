"""
보안 관련 설정을 중앙화하는 모듈
"""

import os
import sys
from typing import Final, List, Dict
from pydantic import BaseModel, SecretStr, Field


def _get_allowed_hosts() -> List[str]:
    """허용된 호스트 목록 반환 (테스트 환경 고려)"""
    default_hosts = os.getenv("ALLOWED_HOSTS", "*").split(",")
    
    # 테스트 환경에서는 testserver 추가
    if ("pytest" in os.getenv("_", "") or 
        "pytest" in " ".join(sys.argv) or 
        os.getenv("TESTING", "").lower() == "true"):
        if "testserver" not in default_hosts:
            default_hosts.append("testserver")
    
    return default_hosts


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
        default_factory=lambda: _get_allowed_hosts()
    )

    # 로그 파일 설정
    LOG_DIR: str = Field(default=os.getenv("LOG_DIR", "logs"))
    SECURITY_AUDIT_LOG: str = Field(
        default=os.getenv("SECURITY_AUDIT_LOG", "security_audit.log")
    )
    APPLICATION_LOG: str = Field(
        default=os.getenv("APPLICATION_LOG", "application.log")
    )

    def model_post_init(self, __context) -> None:
        """로그 디렉토리 자동 생성"""
        from pathlib import Path
        
        log_dir = Path(self.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)


# 상수 정의
SECURE_HEADERS: Final[Dict[str, str]] = SecurityConfig().SECURITY_HEADERS
REQUEST_TIMEOUT: Final[int] = 30  # 초
MAX_RETRIES: Final[int] = 3
