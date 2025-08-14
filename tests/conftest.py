#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pytest 설정 및 픽스처 정의
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

# Add project root to sys path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 외부 의존성 임포트 제거 - test_minimal.py에는 필요하지 않음
# from tests.mock_google_generativeai import GenerativeModel, configure, types, caching
# from tests.mock_langchain_google_genai import MockChatGoogleGenerativeAI

# 프로젝트 루트를 Python 경로에 추가
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def pytest_configure(config):
    """pytest 구성 설정"""
    # 테스트 환경 디렉토리 자동 생성
    from pathlib import Path
    
    # test_logs 디렉토리 생성 (로깅 오류 방지)
    test_logs_dir = Path("test_logs")
    test_logs_dir.mkdir(exist_ok=True)
    
    # 기타 테스트용 디렉토리들 생성
    for test_dir in ["temp", "output", "logs"]:
        Path(test_dir).mkdir(exist_ok=True)
    
    # 설정 캐시 클리어 (테스트 격리)
    try:
        from newsletter.centralized_settings import clear_settings_cache
        clear_settings_cache()
    except ImportError:
        pass
    
    # 커스텀 마크 등록
    config.addinivalue_line(
        "markers", "unit: pure unit tests without external dependencies"
    )
    config.addinivalue_line(
        "markers", "mock_api: tests that use mocked API responses (GitHub Actions safe)"
    )
    config.addinivalue_line(
        "markers", "api: legacy API tests (being migrated to real_api or mock_api)"
    )
    config.addinivalue_line("markers", "real_api: tests that require real API calls")
    config.addinivalue_line(
        "markers", "integration: integration tests with external services"
    )
    config.addinivalue_line("markers", "requires_quota: tests that consume API quota")
    config.addinivalue_line("markers", "slow: tests that take a long time to run")
    config.addinivalue_line(
        "markers", "e2e: end-to-end tests that require running web server"
    )
    config.addinivalue_line(
        "markers",
        "deployment: deployment verification tests for production environments",
    )
    config.addinivalue_line(
        "markers", "manual: tests that require manual intervention or special setup"
    )
    config.addinivalue_line(
        "markers", "korean: tests with Korean language content and encoding"
    )


def pytest_collection_modifyitems(config, items):
    """테스트 수집 후 조건부 스킵 처리"""

    # 환경 변수 확인
    run_real_api = os.getenv("RUN_REAL_API_TESTS", "0") == "1"
    run_mock_api = os.getenv("RUN_MOCK_API_TESTS", "1") == "1"
    run_integration = os.getenv("RUN_INTEGRATION_TESTS", "0") == "1"
    run_deployment = os.getenv("RUN_DEPLOYMENT_TESTS", "0") == "1"

    # API 키 존재 여부 확인
    has_gemini_key = bool(os.getenv("GEMINI_API_KEY"))
    has_serper_key = bool(os.getenv("SERPER_API_KEY"))
    has_postmark_key = bool(os.getenv("POSTMARK_SERVER_TOKEN"))

    for item in items:
        # Deployment 테스트 처리
        if "deployment" in item.keywords:
            if not run_deployment:
                item.add_marker(
                    pytest.mark.skip(
                        reason="Deployment tests disabled. Set RUN_DEPLOYMENT_TESTS=1 to enable"
                    )
                )
            elif not os.getenv("TEST_BASE_URL"):
                item.add_marker(
                    pytest.mark.skip(
                        reason="Missing TEST_BASE_URL for deployment tests"
                    )
                )

        # Integration 테스트 처리 (실제 API 호출 포함)
        elif "integration" in item.keywords:
            if not run_integration:
                item.add_marker(
                    pytest.mark.skip(
                        reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=1 to enable"
                    )
                )
            elif "email" in str(item.fspath) and not has_postmark_key:
                item.add_marker(
                    pytest.mark.skip(
                        reason="Missing POSTMARK_SERVER_TOKEN for email integration tests"
                    )
                )
            elif not (has_gemini_key and has_serper_key):
                item.add_marker(
                    pytest.mark.skip(reason="Missing API keys for integration tests")
                )

        # Real API 테스트 처리
        elif "real_api" in item.keywords:
            if not run_real_api:
                item.add_marker(
                    pytest.mark.skip(
                        reason="Real API tests disabled. Set RUN_REAL_API_TESTS=1 to enable"
                    )
                )
            elif not (has_gemini_key and has_serper_key):
                item.add_marker(
                    pytest.mark.skip(reason="Missing API keys for real API tests")
                )

        # Mock API 테스트 처리 (GitHub Actions 안전)
        elif "mock_api" in item.keywords:
            if not run_mock_api:
                item.add_marker(
                    pytest.mark.skip(
                        reason="Mock API tests disabled. Set RUN_MOCK_API_TESTS=1 to enable"
                    )
                )

        # Legacy API 마킹 처리 (기존 @pytest.mark.api)
        elif (
            "api" in item.keywords
            and "mock_api" not in item.keywords
            and "real_api" not in item.keywords
        ):
            # 기존 API 테스트들을 mock_api로 분류 (더 안전한 기본값)
            if not run_mock_api:
                item.add_marker(
                    pytest.mark.skip(
                        reason="Legacy API test. Set RUN_MOCK_API_TESTS=1 to enable or migrate to mock_api"
                    )
                )


@pytest.fixture(autouse=True)
def clear_settings_cache_fixture():
    """각 테스트 실행 전후 설정 캐시 클리어 (자동 적용)"""
    import importlib
    from unittest.mock import _patch
    
    # 테스트 실행 전 클리어
    try:
        from newsletter.centralized_settings import clear_settings_cache
        clear_settings_cache()
    except ImportError:
        pass
    
    # 모든 newsletter 관련 모듈 캐시 정리
    modules_to_clear = [
        name for name in sys.modules.keys() 
        if name.startswith('newsletter.') or name == 'newsletter'
    ]
    
    # Mock 상태 백업
    original_env = dict(os.environ)
    
    yield  # 테스트 실행
    
    # 테스트 실행 후 정리
    try:
        from newsletter.centralized_settings import clear_settings_cache
        clear_settings_cache()
    except ImportError:
        pass
    
    # 환경 변수 복원 (테스트가 변경했을 수 있는 것들)
    os.environ.clear()
    os.environ.update(original_env)
    
    # 활성 Mock 패치 정리
    try:
        # 모든 활성 패치를 정리
        for patcher in _patch.patches:
            if hasattr(patcher, 'stop'):
                try:
                    patcher.stop()
                except RuntimeError:
                    pass  # 이미 stop된 경우 무시
    except:
        pass
    
    # 모듈 상태 정리 (변경된 속성들 복원)
    for module_name in modules_to_clear:
        if module_name in sys.modules:
            try:
                importlib.reload(sys.modules[module_name])
            except:
                pass  # 로드 실패 시 무시


@pytest.fixture
def base_url():
    """Base URL for deployment tests"""
    return os.getenv("TEST_BASE_URL", "http://localhost:5000")


@pytest.fixture
def keyword():
    """Test search keyword fixture"""
    return "인공지능"


@pytest.fixture
def test_articles():
    """Sample test articles fixture"""
    return [
        {
            "title": "Test Article 1",
            "url": "http://example.com/article1",
            "content": "This is a test article about AI technology.",
        },
        {
            "title": "Test Article 2",
            "url": "http://example.com/article2",
            "content": "This is another test article about machine learning.",
        },
    ]


@pytest.fixture
def client():
    """Flask test client fixture"""
    import sys
    from pathlib import Path

    # Add web directory to path temporarily
    web_dir = Path(__file__).parent.parent / "web"
    if str(web_dir) not in sys.path:
        sys.path.insert(0, str(web_dir))

    try:
        from app import app

        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client
    finally:
        # Clean up path
        if str(web_dir) in sys.path:
            sys.path.remove(str(web_dir))


@pytest.fixture
def korean_keywords():
    """Korean test keywords fixture"""
    return ["토요타", "삼성전자", "AI", "반도체"]


@pytest.fixture
def mixed_language_keywords():
    """Mixed language test keywords fixture"""
    return ["반도체,semiconductor", "AI,인공지능", "토요타,Toyota"]


def remove_duplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """중복된 기사 제거"""
    unique_articles = []
    seen_urls = set()
    seen_titles = set()

    for article in articles:
        url = article.get("url", "")
        title = article.get("title", "")

        # URL과 제목이 모두 없는 경우는 스킵
        if not url and not title:
            continue

        # URL 기반 중복 확인
        if url and url in seen_urls:  # 이미 본 URL이면 건너뜀
            continue

        # 제목 기반 중복 확인 (URL이 다르더라도)
        if title and title in seen_titles:  # 이미 본 제목이면 건너뜀
            continue

        # 여기까지 왔다면 중복이 아님
        if url:
            seen_urls.add(url)  # 이 URL을 '본 것'으로 추가
        if title:
            seen_titles.add(title)  # 이 제목을 '본 것'으로 추가

        unique_articles.append(article)  # 고유한 기사 목록에 추가

    # console이 정의되지 않았을 수 있으므로 안전 처리
    try:
        console.print(
            f"[cyan]Removed {len(articles) - len(unique_articles)} duplicate articles[/cyan]"
        )
    except NameError:
        pass

    return unique_articles


@pytest.fixture
def mock_google_ai():
    """Google Generative AI Mock 픽스처"""
    mock = MagicMock()
    mock.generate_content.return_value.text = "Mocked AI response for testing"
    return mock


@pytest.fixture
def mock_serper_api():
    """Serper API Mock 픽스처"""
    mock_response = {
        "organic": [
            {
                "title": "Test Article Title",
                "link": "https://example.com/test",
                "snippet": "Test article snippet for unit testing",
                "date": "2025-05-24",
            }
        ]
    }
    return mock_response


@pytest.fixture
def sample_articles():
    """테스트용 샘플 기사 데이터"""
    return [
        {
            "title": "AI 기술 발전 동향",
            "url": "https://example.com/ai-trends",
            "snippet": "인공지능 기술의 최신 발전 동향을 분석합니다.",
            "source": "TechNews",
            "date": "2025-05-24",
            "content": "AI 기술이 빠르게 발전하고 있으며, 특히 자연어 처리 분야에서 큰 진전이 있었습니다.",
        },
        {
            "title": "반도체 시장 전망",
            "url": "https://example.com/semiconductor",
            "snippet": "글로벌 반도체 시장의 향후 전망을 살펴봅니다.",
            "source": "MarketWatch",
            "date": "2025-05-23",
            "content": "반도체 시장은 AI 칩 수요 증가로 인해 지속적인 성장이 예상됩니다.",
        },
    ]
