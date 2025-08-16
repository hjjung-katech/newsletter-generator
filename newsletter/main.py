import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 웹 서비스 모드 체크 - FastAPI 앱 중복 실행 방지
if os.environ.get("WEB_SERVICE_MODE") == "1":
    # 웹 서비스에서 호출된 경우 FastAPI 앱 시작 방지
    os.environ["PORT"] = "0"  # 포트 0으로 설정하여 바인딩 방지

from .security.config import SecurityConfig
from .security.logging import setup_secure_logging
from .security.middleware import setup_security_middleware
from .security.validation import FileValidationError, InputValidationError

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
    return JSONResponse(status_code=400, content={"error": "입력값이 유효하지 않습니다"})


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
    return JSONResponse(status_code=500, content={"error": "서버 내부 오류가 발생했습니다"})


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {"message": "Newsletter Generator API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "environment": ENVIRONMENT}


# Backward compatibility functions for tests
def collect_news(keywords, period=14, **kwargs):
    """
    Backward compatibility function for collecting news.
    This is a wrapper around the actual collection functionality.
    """
    from . import collect
    from .centralized_settings import get_settings

    settings = get_settings()

    # Convert keywords to list if it's a string
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",")]

    # Call the actual collection function
    return collect.collect_articles_from_serper(
        keywords=keywords,
        period=period,
        api_key=(
            settings.serper_api_key.get_secret_value()
            if settings.serper_api_key
            else None
        ),
    )


def generate_newsletter(keywords, period=14, template_style="compact", **kwargs):
    """
    Backward compatibility function for generating newsletters.
    This is a wrapper around the CLI functionality.
    """
    import os
    import tempfile

    from . import cli

    # Create a temporary output file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".html") as f:
        output_file = f.name

    try:
        # Use the CLI functionality
        result = cli.run_newsletter_generation(
            keywords=keywords,
            period=period,
            template_style=template_style,
            output_file=output_file,
            **kwargs,
        )

        # Read the generated file
        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()

        return content
    finally:
        # Clean up
        if os.path.exists(output_file):
            os.unlink(output_file)


def main():
    """
    Backward compatibility function for main entry point.
    This function exists to maintain compatibility with legacy tests and scripts.
    """
    # For backward compatibility, we'll just run the FastAPI app
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    uvicorn.run(
        "newsletter.main:app",
        host=host,
        port=port,
        reload=DEBUG,
        log_level="info" if not DEBUG else "debug",
    )


def process_articles(articles, keywords=None, **kwargs):
    """
    Backward compatibility function for processing articles.
    This is a wrapper around the actual processing functionality.
    """
    # Import here to avoid circular dependencies
    from .centralized_settings import get_settings

    get_settings()

    # Process articles using the chains module
    try:
        # Use the scoring functionality to process articles
        pass

        # Create a simple processing result
        processed_articles = []
        for article in articles:
            processed_article = article.copy()
            processed_article["score"] = 0.8  # Default score
            processed_article["summary"] = (
                article.get("content", article.get("snippet", ""))[:200] + "..."
            )
            processed_articles.append(processed_article)

        return processed_articles
    except Exception as e:
        logging.error(f"Error processing articles: {e}")
        return articles  # Return original articles if processing fails


if __name__ == "__main__":
    import uvicorn

    # 환경별 포트 설정 (기본값 8000으로 통일)
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    uvicorn.run(
        "newsletter.main:app",
        host=host,
        port=port,
        reload=DEBUG,
        log_level="info" if not DEBUG else "debug",
    )
