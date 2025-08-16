"""
보안 로깅 시스템
"""

import json
import logging
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from .config import SecurityConfig

security_config = SecurityConfig()


class SecureFormatter(logging.Formatter):
    """민감한 정보를 마스킹하는 로그 포매터"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sensitive_fields = security_config.SENSITIVE_FIELDS

    def _mask_sensitive_data(self, message: str) -> str:
        """민감한 데이터 마스킹"""
        for field in self.sensitive_fields:
            # 정규식 패턴: field=value 또는 "field": "value" 형식 찾기
            patterns = [
                rf"{field}=([^,\s]+)",  # field=value
                rf'"{field}":\s*"([^"]+)"',  # "field": "value"
                rf"'{field}':\s*'([^']+)'",  # 'field': 'value'
            ]

            for pattern in patterns:
                message = re.sub(pattern, f"{field}=*****", message)

        return message

    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드 포맷팅"""
        # 원본 메시지 마스킹
        if isinstance(record.msg, (str, bytes)):
            record.msg = self._mask_sensitive_data(str(record.msg))
        elif isinstance(record.msg, dict):
            # 딕셔너리인 경우 JSON으로 변환 후 마스킹
            record.msg = self._mask_sensitive_data(json.dumps(record.msg))

        return super().format(record)


class SecurityAuditLogger:
    """보안 감사 로그를 남기는 로거"""

    def __init__(self):
        self.logger = logging.getLogger("security_audit")
        self.logger.setLevel(logging.INFO)

        # 로그 디렉토리 생성
        log_dir = Path(security_config.LOG_DIR)
        log_dir.mkdir(exist_ok=True)

        # 파일 핸들러 설정 (로그 로테이션 포함)
        log_file = log_dir / security_config.SECURITY_AUDIT_LOG
        handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
        )
        formatter = SecureFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_security_event(
        self,
        event_type: str,
        user_id: Optional[str],
        details: Dict[str, Any],
        severity: str = "INFO",
    ) -> None:
        """보안 이벤트 로깅

        Args:
            event_type: 이벤트 유형 (예: login_attempt, permission_change)
            user_id: 이벤트와 관련된 사용자 ID
            details: 이벤트 상세 정보
            severity: 이벤트 심각도
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "severity": severity,
            "details": details,
        }

        level = getattr(logging, severity.upper(), logging.INFO)
        self.logger.log(level, json.dumps(log_data))


def setup_secure_logging() -> None:
    """보안 로깅 설정"""
    root_logger = logging.getLogger()

    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 로그 디렉토리 생성
    log_dir = Path(security_config.LOG_DIR)
    log_dir.mkdir(exist_ok=True)

    # 새로운 핸들러 추가
    handler = logging.StreamHandler()
    handler.setFormatter(
        SecureFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    root_logger.addHandler(handler)

    # 파일 핸들러 추가 (로그 로테이션 포함)
    log_file = log_dir / security_config.APPLICATION_LOG
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
    )
    file_handler.setFormatter(
        SecureFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    root_logger.addHandler(file_handler)

    # 로그 레벨 설정
    root_logger.setLevel(logging.INFO)
