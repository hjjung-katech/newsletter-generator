"""
뉴스 통합 검색 기능 테스트
- tools.py와 collect.py 모듈의 통합 테스트
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from newsletter.collect import collect_articles
from newsletter.sources import NewsSourceManager, SerperAPISource

# 테스트할 모듈 임포트
from newsletter.tools import search_news_articles


class TestNewsIntegration(unittest.TestCase):
    """뉴스 수집 통합 테스트 케이스"""

    def test_tools_and_collect_integration(self):
        """tools.py와 collect.py의 통합 테스트"""
        # 테스트할 키워드
        test_keywords = "인공지능"
        results_per_keyword = 2

        # 1. tools.py의 search_news_articles 함수로 기사 수집
        articles_from_tools = search_news_articles.invoke(
            {"keywords": test_keywords, "num_results": results_per_keyword}
        )

        # 기본 검증
        self.assertIsNotNone(articles_from_tools, "tools.py의 검색 결과가 None입니다")
        self.assertIsInstance(
            articles_from_tools, list, "tools.py의 검색 결과가 리스트가 아닙니다"
        )

        # collect_articles 함수에 전달할 데이터 준비
        # collect.py의 collect_articles 함수는 키워드 목록과 결과 수를 받습니다
        keywords = test_keywords.split(",")

        # 2. collect.py의 collect_articles 함수 호출
        # group_by_keywords=False로 설정하여 리스트 형태로 반환받음
        articles_from_collect = collect_articles(
            keywords, results_per_keyword, group_by_keywords=False
        )

        # 기본 검증
        self.assertIsNotNone(
            articles_from_collect, "collect.py의 검색 결과가 None입니다"
        )
        self.assertIsInstance(
            articles_from_collect, list, "collect.py의 검색 결과가 리스트가 아닙니다"
        )

    @patch("newsletter.collect.requests.request")
    @patch("newsletter.collect.configure_default_sources")
    def test_mocked_integration(self, mock_configure_sources, mock_request):
        """모의 응답을 사용한 통합 테스트"""
        # 모의 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "news": [
                {
                    "title": "테스트 기사 제목",
                    "link": "https://example.com/article1",
                    "date": "1 hour ago",
                    "source": "테스트 출처",
                    "snippet": "테스트 기사 내용 요약",
                }
            ]
        }
        mock_request.return_value = mock_response

        # 실제 SerperAPISource 인스턴스 사용, fetch_news만 mock
        serper_source = SerperAPISource()
        serper_source.fetch_news = MagicMock(
            return_value=[
                {
                    "title": "테스트 기사 제목",
                    "url": "https://example.com/article1",
                    "link": "https://example.com/article1",
                    "snippet": "테스트 기사 내용 요약",
                    "source": "테스트 출처",
                    "date": "1 hour ago",
                }
            ]
        )
        real_source_manager = NewsSourceManager()
        real_source_manager.sources = [serper_source]
        mock_configure_sources.return_value = real_source_manager

        # collect_articles 호출 - group_by_keywords=False로 설정
        articles = collect_articles(["테스트"], 1, group_by_keywords=False)

        # 검증
        self.assertEqual(len(articles), 1, "예상된 기사 수와 일치하지 않습니다")
        self.assertEqual(
            articles[0]["title"], "테스트 기사 제목", "기사 제목이 일치하지 않습니다"
        )
        self.assertEqual(
            articles[0]["url"],
            "https://example.com/article1",
            "기사 URL이 일치하지 않습니다",
        )


if __name__ == "__main__":
    unittest.main()
