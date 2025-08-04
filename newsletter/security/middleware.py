"""
보안 미들웨어 모듈
"""

import time
import json
from typing import Callable, Dict, Optional
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .config import SecurityConfig

security_config = SecurityConfig()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """보안 헤더를 추가하는 미들웨어"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.security_headers = security_config.SECURITY_HEADERS

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            for header_name, header_value in self.security_headers.items():
                response.headers[header_name] = header_value
            return response
        except Exception as e:
            # 에러 발생시에도 보안 헤더 추가
            response = Response(
                content=json.dumps({"error": "Internal server error"}),
                status_code=500,
                media_type="application/json",
            )
            for header_name, header_value in self.security_headers.items():
                response.headers[header_name] = header_value
            return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """레이트 리미팅을 구현하는 미들웨어"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.requests: Dict[str, list] = {}
        self.rate_limit_file = Path("rate_limit_cache.json")

    def _get_client_identifier(self, request: Request) -> str:
        """클라이언트 식별자 생성"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0]
        return request.client.host if request.client else "unknown"

    def _load_rate_limit_cache(self) -> None:
        """레이트 리미트 캐시 로드"""
        try:
            if self.rate_limit_file.exists():
                with open(self.rate_limit_file, "r") as f:
                    cached_data = json.load(f)
                    # 만료된 데이터 필터링
                    now = time.time()
                    for identifier, timestamps in cached_data.items():
                        valid_timestamps = [
                            ts
                            for ts in timestamps
                            if now - ts < security_config.RATE_LIMIT_WINDOW
                        ]
                        if valid_timestamps:
                            self.requests[identifier] = valid_timestamps
        except Exception:
            # 캐시 로드 실패시 무시
            pass

    def _save_rate_limit_cache(self) -> None:
        """레이트 리미트 캐시 저장"""
        try:
            with open(self.rate_limit_file, "w") as f:
                json.dump(self.requests, f)
        except Exception:
            # 캐시 저장 실패시 무시
            pass

    def _is_rate_limited(self, identifier: str) -> bool:
        """레이트 리미트 확인"""
        now = time.time()
        if identifier not in self.requests:
            self.requests[identifier] = []

        # 만료된 요청 제거
        self.requests[identifier] = [
            req_time
            for req_time in self.requests[identifier]
            if now - req_time < security_config.RATE_LIMIT_WINDOW
        ]

        # 요청 수 확인
        return len(self.requests[identifier]) >= security_config.RATE_LIMIT_REQUESTS

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not security_config.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # 캐시 로드
        self._load_rate_limit_cache()

        identifier = self._get_client_identifier(request)

        if self._is_rate_limited(identifier):
            # 캐시 저장
            self._save_rate_limit_cache()
            return Response(
                content=json.dumps({"error": "Rate limit exceeded"}),
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(security_config.RATE_LIMIT_WINDOW)},
            )

        # 현재 시간을 요청 목록에 추가
        self.requests[identifier].append(time.time())

        # 캐시 저장
        self._save_rate_limit_cache()

        return await call_next(request)


def setup_security_middleware(app: FastAPI) -> None:
    """보안 미들웨어 설정"""

    # CORS 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=security_config.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=security_config.ALLOWED_METHODS,
        allow_headers=security_config.ALLOWED_HEADERS,
    )

    # 신뢰할 수 있는 호스트 설정
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=security_config.ALLOWED_HOSTS,
    )

    # 보안 헤더 추가
    app.add_middleware(SecurityHeadersMiddleware)

    # 레이트 리미팅 추가
    app.add_middleware(RateLimitMiddleware)
