#!/usr/bin/env python3
"""
보안 모듈 테스트
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch
from pathlib import Path

# 테스트 환경 설정
os.environ["TESTING"] = "1"
os.environ["ENVIRONMENT"] = "testing"

# 모듈 캐시 클리어
modules_to_clear = [
    "newsletter.security.config",
    "newsletter.security.logging", 
    "newsletter.security.middleware",
    "newsletter.security.validation",
    "newsletter.main"
]
for module in modules_to_clear:
    if module in sys.modules:
        del sys.modules[module]


class TestSecurityConfig:
    """보안 설정 테스트"""

    def test_environment_variables(self):
        """환경변수 기반 설정 테스트"""
        from newsletter.security.config import SecurityConfig
        
        # 테스트 환경변수 설정
        os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000,https://example.com"
        os.environ["RATE_LIMIT_REQUESTS"] = "50"
        os.environ["JWT_SECRET_KEY"] = "test-secret-key"
        
        config = SecurityConfig()
        
        assert "http://localhost:3000" in config.ALLOWED_ORIGINS
        assert "https://example.com" in config.ALLOWED_ORIGINS
        assert config.RATE_LIMIT_REQUESTS == 50
        assert config.JWT_SECRET_KEY.get_secret_value() == "test-secret-key"

    def test_default_values(self):
        """기본값 테스트"""
        from newsletter.security.config import SecurityConfig
        
        # 환경변수 클리어
        for key in ["ALLOWED_ORIGINS", "RATE_LIMIT_REQUESTS", "JWT_SECRET_KEY"]:
            if key in os.environ:
                del os.environ[key]
        
        config = SecurityConfig()
        
        assert "*" in config.ALLOWED_ORIGINS
        assert config.RATE_LIMIT_REQUESTS == 100
        assert config.JWT_SECRET_KEY.get_secret_value() == "change-this-in-production"


class TestSecurityLogging:
    """보안 로깅 테스트"""

    def test_secure_formatter(self):
        """보안 포매터 테스트"""
        from newsletter.security.logging import SecureFormatter
        
        formatter = SecureFormatter()
        
        # 민감한 정보 마스킹 테스트
        test_message = "password=secret123, token=abc123"
        masked_message = formatter._mask_sensitive_data(test_message)
        
        assert "password=*****" in masked_message
        assert "token=*****" in masked_message
        assert "secret123" not in masked_message
        assert "abc123" not in masked_message

    def test_log_directory_creation(self):
        """로그 디렉토리 생성 테스트"""
        from newsletter.security.logging import setup_secure_logging
        
        # 테스트용 로그 디렉토리
        test_log_dir = Path("test_logs")
        if test_log_dir.exists():
            import shutil
            shutil.rmtree(test_log_dir)
        
        os.environ["LOG_DIR"] = "test_logs"
        
        setup_secure_logging()
        
        assert test_log_dir.exists()
        assert test_log_dir.is_dir()
        
        # 정리
        import shutil
        shutil.rmtree(test_log_dir)


class TestSecurityValidation:
    """보안 검증 테스트"""

    def test_input_sanitizer(self):
        """입력 살균 테스트"""
        from newsletter.security.validation import InputSanitizer
        
        # XSS 공격 테스트
        xss_input = '<script>alert("xss")</script>Hello'
        sanitized = InputSanitizer.sanitize_string(xss_input)
        
        assert "<script>" not in sanitized
        assert "Hello" in sanitized

    def test_sql_injection_detection(self):
        """SQL 인젝션 감지 테스트"""
        from newsletter.security.validation import InputSanitizer
        
        # SQL 인젝션 패턴 테스트
        sql_input = "'; DROP TABLE users; --"
        is_sql_injection = InputSanitizer.is_sql_injection(sql_input)
        
        assert is_sql_injection is True

    def test_file_validation(self):
        """파일 검증 테스트"""
        from newsletter.security.validation import validate_file_extension, validate_file_size
        
        # 파일 확장자 테스트
        assert validate_file_extension("test.txt") is True
        assert validate_file_extension("test.exe") is False
        
        # 파일 크기 테스트
        assert validate_file_size(1024 * 1024) is True  # 1MB
        assert validate_file_size(100 * 1024 * 1024) is False  # 100MB


class TestSecurityMiddleware:
    """보안 미들웨어 테스트"""

    @patch("newsletter.security.middleware.SecurityConfig")
    def test_security_headers_middleware(self, mock_config):
        """보안 헤더 미들웨어 테스트"""
        from newsletter.security.middleware import SecurityHeadersMiddleware
        from fastapi import Request
        from starlette.responses import Response
        
        # Mock 설정
        mock_config.return_value.SECURITY_HEADERS = {
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff"
        }
        
        middleware = SecurityHeadersMiddleware(Mock())
        
        # Mock request와 response
        mock_request = Mock(spec=Request)
        mock_response = Response(content="test")
        
        async def mock_call_next(request):
            return mock_response
        
        # 미들웨어 실행
        import asyncio
        result = asyncio.run(middleware.dispatch(mock_request, mock_call_next))
        
        # 보안 헤더 확인
        assert result.headers["X-Frame-Options"] == "DENY"
        assert result.headers["X-Content-Type-Options"] == "nosniff"

    @patch("newsletter.security.middleware.SecurityConfig")
    def test_rate_limit_middleware(self, mock_config):
        """레이트 리미트 미들웨어 테스트"""
        from newsletter.security.middleware import RateLimitMiddleware
        from fastapi import Request
        
        # Mock 설정
        mock_config.return_value.RATE_LIMIT_ENABLED = True
        mock_config.return_value.RATE_LIMIT_REQUESTS = 2
        mock_config.return_value.RATE_LIMIT_WINDOW = 3600
        
        middleware = RateLimitMiddleware(Mock())
        
        # Mock request
        mock_request = Mock(spec=Request)
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {}
        
        async def mock_call_next(request):
            from starlette.responses import Response
            return Response(content="test")
        
        # 첫 번째 요청 (성공)
        import asyncio
        result1 = asyncio.run(middleware.dispatch(mock_request, mock_call_next))
        assert result1.status_code == 200
        
        # 두 번째 요청 (성공)
        result2 = asyncio.run(middleware.dispatch(mock_request, mock_call_next))
        assert result2.status_code == 200
        
        # 세 번째 요청 (레이트 리미트)
        result3 = asyncio.run(middleware.dispatch(mock_request, mock_call_next))
        assert result3.status_code == 429


class TestMainApp:
    """메인 애플리케이션 테스트"""

    def test_app_creation(self):
        """애플리케이션 생성 테스트"""
        from newsletter.main import app
        
        assert app is not None
        assert app.title == "Newsletter Generator"

    def test_health_endpoint(self):
        """헬스 체크 엔드포인트 테스트"""
        from newsletter.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["environment"] == "testing"

    def test_root_endpoint(self):
        """루트 엔드포인트 테스트"""
        from newsletter.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        assert response.json()["message"] == "Newsletter Generator API"


if __name__ == "__main__":
    print("🔒 보안 모듈 테스트 시작")
    
    # 테스트 실행
    pytest.main([__file__, "-v"])
    
    print("✅ 보안 모듈 테스트 완료!") 