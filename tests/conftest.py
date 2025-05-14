import sys
import os
import pytest
from typing import List, Dict, Any

# Add project root to sys path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 외부 의존성 임포트 제거 - test_minimal.py에는 필요하지 않음
# from tests.mock_google_generativeai import GenerativeModel, configure, types, caching
# from tests.mock_langchain_google_genai import MockChatGoogleGenerativeAI


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
