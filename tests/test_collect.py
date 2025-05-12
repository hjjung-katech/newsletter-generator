import sys
import os

# 프로젝트 루트 디렉토리를 sys.path에 추가
# 현재 파일의 디렉토리(tests)의 부모 디렉토리(프로젝트 루트)를 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from unittest.mock import patch
import requests  # requests 모듈 임포트 추가
from newsletter.collect import collect_articles  # collect_data -> collect_articles


class TestCollect(unittest.TestCase):

    @patch("newsletter.collect.requests.request")
    @patch(
        "newsletter.config.SERPER_API_KEY", "fake_api_key"
    )  # SERPER_API_KEY 모의 처리
    def test_collect_articles_success(self, mock_request):
        mock_response = mock_request.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "organic": [
                {
                    "title": "Test Article 1",
                    "link": "http://example.com/article1",
                    "snippet": "This is a test snippet for article 1.",
                },
                {
                    "title": "Test Article 2",
                    "link": "http://example.com/article2",
                    "snippet": "This is a test snippet for article 2.",
                },
            ]
        }

        keywords_string = (
            "test keyword1 OR test keyword2"  # collect_articles는 문자열을 받음
        )
        result = collect_articles(keywords_string)

        mock_request.assert_called_once()
        # 실제 호출 인자 검증 추가 가능:
        # called_args, called_kwargs = mock_request.call_args
        # self.assertEqual(called_kwargs['url'], "https://google.serper.dev/search")
        # self.assertIn(keywords_string, called_kwargs['data'])

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        for item in result:
            self.assertIsInstance(item, dict)
            self.assertIn("title", item)
            self.assertIn(
                "url", item
            )  # 'link'에서 'url'로 변경 (collect_articles 반환 형식)
            self.assertIn("content", item)  # 'snippet'에서 'content'로 변경

        self.assertEqual(result[0]["title"], "Test Article 1")
        self.assertEqual(result[0]["url"], "http://example.com/article1")
        self.assertEqual(result[0]["content"], "This is a test snippet for article 1.")

    @patch("newsletter.collect.requests.request")
    @patch("newsletter.config.SERPER_API_KEY", "fake_api_key")
    def test_collect_articles_empty_keywords_string(self, mock_request):
        # Serper API가 빈 문자열에 대해 어떻게 반응하는지에 따라 mock_response 설정 필요
        mock_response = mock_request.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {"organic": []}  # 예: 빈 결과 반환

        result = collect_articles("")
        mock_request.assert_called_once()
        self.assertEqual(result, [])

    @patch("newsletter.collect.requests.request")
    @patch("newsletter.config.SERPER_API_KEY", "fake_api_key")
    def test_collect_articles_search_error(self, mock_request):
        mock_request.side_effect = requests.exceptions.RequestException(
            "Search API Error"
        )

        keywords_string = "test keyword"
        # collect_articles는 내부적으로 예외를 처리하고 빈 리스트를 반환
        result = collect_articles(keywords_string)
        self.assertEqual(result, [])
        mock_request.assert_called_once()  # 예외가 발생해도 호출은 시도됨

    @patch("newsletter.collect.requests.request")
    @patch("newsletter.config.SERPER_API_KEY", None)  # API 키가 없는 경우
    def test_collect_articles_no_api_key(self, mock_request):
        keywords_string = "test keyword"
        result = collect_articles(keywords_string)
        self.assertEqual(result, [])
        mock_request.assert_not_called()  # API 키가 없으면 requests.request가 호출되지 않아야 함


if __name__ == "__main__":
    unittest.main()
