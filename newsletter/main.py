from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

# 웹 서비스 모드 체크 - FastAPI 앱 중복 실행 방지
if os.environ.get("WEB_SERVICE_MODE") == "1":
    # 웹 서비스에서 호출된 경우 FastAPI 앱 시작 방지
    os.environ["PORT"] = "0"  # 포트 0으로 설정하여 바인딩 방지

from .security.middleware import setup_security_middleware
from .security.logging import setup_secure_logging
from .security.validation import InputValidationError, FileValidationError
from .security.config import SecurityConfig

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


@app.exception_handler(InputValidationError)
async def validation_exception_handler(request: Request, exc: InputValidationError):
    """입력 검증 오류 처리"""
    logging.warning(f"Input validation error: {exc}")
    return JSONResponse(
        status_code=400, content={"error": "입력값이 유효하지 않습니다"}
    )


@app.exception_handler(FileValidationError)
async def file_validation_exception_handler(request: Request, exc: FileValidationError):
    """파일 검증 오류 처리"""
    logging.warning(f"File validation error: {exc}")
    return JSONResponse(status_code=400, content={"error": "파일이 유효하지 않습니다"})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 처리"""
    logging.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code, content={"error": "요청을 처리할 수 없습니다"}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 처리"""
    logging.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500, content={"error": "서버 내부 오류가 발생했습니다"}
    )


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {"message": "Newsletter Generator API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "environment": ENVIRONMENT}


if __name__ == "__main__":
    import uvicorn

    # 환경별 포트 설정 (기본값 5000으로 통일)
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")

    uvicorn.run(
        "newsletter.main:app",
        host=host,
        port=port,
        reload=DEBUG,
        log_level="info" if not DEBUG else "debug",
    )
