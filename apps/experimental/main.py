"""Experimental FastAPI runtime entrypoint.

This module is not part of the canonical Flask runtime path.
Install optional dependencies with:
    pip install "newsletter-generator[api_experimental]"
"""

import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from newsletter.security.config import SecurityConfig
from newsletter.security.logging import setup_secure_logging
from newsletter.security.middleware import setup_security_middleware
from newsletter.security.validation import FileValidationError, InputValidationError

# 보안 설정 로드
security_config = SecurityConfig()

# 보안 로깅 설정
setup_secure_logging()

# 환경별 설정
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = ENVIRONMENT == "development"

app = FastAPI(
    title="Newsletter Generator",
    description="안전한 뉴스레터 생성 API",
    version="1.0.0",
    debug=DEBUG,
)

# 보안 미들웨어 설정
setup_security_middleware(app)

# 추가 CORS 설정 (개발 환경에서만)
if DEBUG:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(InputValidationError)  # type: ignore[untyped-decorator]
async def validation_exception_handler(
    request: Request, exc: InputValidationError
) -> JSONResponse:
    """입력 검증 오류 처리"""
    logging.warning(f"Input validation error: {exc}")
    return JSONResponse(status_code=400, content={"error": "입력값이 유효하지 않습니다"})


@app.exception_handler(FileValidationError)  # type: ignore[untyped-decorator]
async def file_validation_exception_handler(
    request: Request, exc: FileValidationError
) -> JSONResponse:
    """파일 검증 오류 처리"""
    logging.warning(f"File validation error: {exc}")
    return JSONResponse(status_code=400, content={"error": "파일이 유효하지 않습니다"})


@app.exception_handler(HTTPException)  # type: ignore[untyped-decorator]
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP 예외 처리"""
    logging.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code, content={"error": "요청을 처리할 수 없습니다"}
    )


@app.exception_handler(Exception)  # type: ignore[untyped-decorator]
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """일반 예외 처리"""
    logging.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": "서버 내부 오류가 발생했습니다"})


@app.get("/")  # type: ignore[untyped-decorator]
async def root() -> dict[str, str]:
    """루트 엔드포인트"""
    return {"message": "Newsletter Generator API", "version": "1.0.0"}


@app.get("/health")  # type: ignore[untyped-decorator]
async def health_check() -> dict[str, str]:
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "environment": ENVIRONMENT}


def main() -> None:
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(
        "apps.experimental.main:app",
        host=host,
        port=port,
        reload=DEBUG,
        log_level="info" if not DEBUG else "debug",
    )


if __name__ == "__main__":
    main()
