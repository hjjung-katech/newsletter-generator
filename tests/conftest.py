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


def pytest_collection_modifyitems(config, items):
    """테스트 수집 후 조건부 스킵 처리"""

    # 환경 변수 확인
    run_real_api = os.getenv("RUN_REAL_API_TESTS", "0") == "1"
    run_mock_api = os.getenv("RUN_MOCK_API_TESTS", "1") == "1"
    run_integration = os.getenv("RUN_INTEGRATION_TESTS", "0") == "1"

    # API 키 존재 여부 확인
    has_gemini_key = bool(os.getenv("GEMINI_API_KEY"))
    has_serper_key = bool(os.getenv("SERPER_API_KEY"))
    has_postmark_key = bool(os.getenv("POSTMARK_SERVER_TOKEN"))

    for item in items:
        # Integration 테스트 처리 (실제 API 호출 포함)
        if "integration" in item.keywords:
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
        elif "api" in item.keywords and "mock_api" not in item.keywords:
            # 기존 API 테스트들을 real_api로 분류
            if not run_real_api:
                item.add_marker(
                    pytest.mark.skip(
                        reason="Legacy API test. Set RUN_REAL_API_TESTS=1 to enable or migrate to mock_api"
                    )
                )


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
