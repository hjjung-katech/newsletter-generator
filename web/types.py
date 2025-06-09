"""
Web application common types
"""

from typing import NewType, Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, Field, field_validator, model_validator
import re

# 이메일 주소 타입
EmailAddress = NewType("EmailAddress", str)

# RFC-5322 이메일 패턴 (간소화된 버전)
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Job 상태 타입
JobStatus = Literal["pending", "processing", "finished", "failed"]


# Newsletter 생성 요청 스키마
class GenerateNewsletterRequest(BaseModel):
    keywords: Optional[str] = None
    domain: Optional[str] = None
    template_style: str = Field(
        default="compact", pattern=r"^(compact|detailed|modern)$"
    )
    email_compatible: bool = False
    period: int = Field(default=14)
    email: Optional[str] = None  # 즉시 발송용 이메일 주소

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: int) -> int:
        if v not in [1, 7, 14, 30]:
            raise ValueError("Invalid period. Must be one of: 1, 7, 14, 30 days")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not EMAIL_PATTERN.match(v):
            raise ValueError("Invalid email format")
        return v

    @model_validator(mode="after")
    def validate_keywords_or_domain(self):
        # keywords와 domain 중 하나는 반드시 있어야 함
        if not self.keywords and not self.domain:
            raise ValueError("Either keywords or domain must be provided")
        return self


# Job 응답 스키마
class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: str
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    sent: Optional[bool] = None  # 이메일 발송 여부


# API 응답 기본 스키마
class APIResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
