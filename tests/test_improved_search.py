"""
수정된 search_news_articles 함수 테스트
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 테스트할 모듈 임포트
from newsletter.tools import search_news_articles
from newsletter import config


class TestImprovedSearch(unittest.TestCase):
    """개선된 검색 기능 테스트 케이스"""

    def setUp(self):
        """각 테스트 전에 SERPER_API_KEY를 임시로 설정합니다."""
        self.original_serper_key = getattr(config, "SERPER_API_KEY", None)
        config.SERPER_API_KEY = "dummy_test_key_improved_search"

    def tearDown(self):
        """각 테스트 후에 SERPER_API_KEY를 원래대로 복원합니다."""
        if self.original_serper_key is not None:
            config.SERPER_API_KEY = self.original_serper_key
        elif hasattr(config, "SERPER_API_KEY"):
            del config.SERPER_API_KEY  # 원래 키가 없었다면 삭제

    @patch("newsletter.tools.requests.request")
    def test_improved_search_functionality(self, mock_request):
        """수정된 search_news_articles 함수의 기본 기능 테스트"""
        # 모의(mock) API 응답 설정
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "news": [
                {
                    "title": "AI Title 1",
                    "link": "http://example.com/ai1",
                    "snippet": "AI snippet 1",
                    "source": "AI Source 1",
                    "date": "2023-01-01",
                },
                {
                    "title": "AI Title 2",
                    "link": "http://example.com/ai2",
                    "snippet": "AI snippet 2",
                    "source": "AI Source 2",
                    "date": "2023-01-02",
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()  # HTTP 오류가 없도록 설정
        mock_request.return_value = mock_response

        # 테스트할 키워드
        test_keywords = "인공지능"
        results_per_keyword = 2

        # 함수 호출
        articles = search_news_articles.invoke(
            {"keywords": test_keywords, "num_results": results_per_keyword}
        )

        # 기본 검증
        self.assertIsNotNone(articles, "검색 결과가 None입니다")
        self.assertIsInstance(articles, list, "검색 결과가 리스트가 아닙니다")

        # 결과가 있을 경우 추가 검증
        if articles:
            # 최소한 하나의 결과 확인
            self.assertGreaterEqual(len(articles), 1, "검색 결과가 없습니다")

            # 첫 번째 결과의 필요한 속성 확인
            first_article = articles[0]
            self.assertIsInstance(
                first_article, dict, "기사 항목이 딕셔너리가 아닙니다"
            )

            # 필수 속성 확인
            required_fields = ["title", "link"]
            for field in required_fields:
                self.assertIn(
                    field, first_article, f"기사에 필수 필드 {field}가 없습니다"
                )
                self.assertIsNotNone(
                    first_article[field], f"기사의 {field} 필드가 None입니다"
                )
                self.assertNotEqual(
                    first_article[field], "", f"기사의 {field} 필드가 비어 있습니다"
                )

    @patch("newsletter.tools.requests.request")
    def test_multiple_keywords(self, mock_request):
        """여러 키워드로 검색하는 기능 테스트"""
        # 모의(mock) API 응답 설정 (키워드별로 다른 응답을 줄 수 있도록 side_effect 사용 가능)
        mock_response_ai = MagicMock()
        mock_response_ai.json.return_value = {
            "news": [
                {
                    "title": "AI Title 1",
                    "link": "http://example.com/ai1",
                    "snippet": "AI snippet 1",
                    "source": "AI Source 1",
                    "date": "2023-01-01",
                }
            ]
        }
        mock_response_ai.raise_for_status = MagicMock()

        mock_response_autonomous = MagicMock()
        mock_response_autonomous.json.return_value = {
            "news": [
                {
                    "title": "Autonomous Title 1",
                    "link": "http://example.com/auto1",
                    "snippet": "Autonomous snippet 1",
                    "source": "Auto Source 1",
                    "date": "2023-01-03",
                }
            ]
        }
        mock_response_autonomous.raise_for_status = MagicMock()

        # search_news_articles는 키워드별로 requests.request를 호출하므로, side_effect로 순차적 응답 설정
        mock_request.side_effect = [mock_response_ai, mock_response_autonomous]

        # 여러 키워드 테스트
        test_keywords = "인공지능,자율주행"
        results_per_keyword = 1  # 테스트 시 부하 줄이기

        # 함수 호출
        articles = search_news_articles.invoke(
            {"keywords": test_keywords, "num_results": results_per_keyword}
        )

        # 기본 검증
        self.assertIsNotNone(articles, "검색 결과가 None입니다")
        self.assertIsInstance(articles, list, "검색 결과가 리스트가 아닙니다")

        # 키워드가 2개이고 각각 1개의 결과를 요청했으므로 최소 1-2개의 결과가 있어야 함
        # (중복 제거 등으로 정확히 2개는 아닐 수 있음)
        self.assertGreaterEqual(len(articles), 1, "검색 결과가 없습니다")


if __name__ == "__main__":
    unittest.main()
