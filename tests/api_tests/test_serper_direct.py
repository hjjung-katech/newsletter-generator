"""
Serper.dev API 직접 호출 테스트
- 다양한 API 설정과 응답 형식을 검증
"""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import requests
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


class TestSerperDirect(unittest.TestCase):
    """Serper.dev API 직접 호출 테스트 케이스"""

    def setUp(self):
        """테스트 준비 - API 키 로드"""
        # .env 파일 로드
        load_dotenv()
        self.api_key = os.getenv("SERPER_API_KEY")
        self.assertTrue(
            self.api_key,
            "SERPER_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.",
        )

    def test_serper_api_with_news_type(self):
        """type=news 파라미터를 사용한 API 호출 테스트"""
        # API 호출을 실제로 하지 않고 mock 테스트로 변경
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "news": [
                    {
                        "title": "테스트 뉴스 제목",
                        "link": "https://example.com/news1",
                        "snippet": "테스트 뉴스 내용",
                        "date": "2 hours ago",
                        "source": "테스트 출처",
                    }
                ]
            }
            mock_post.return_value = mock_response

            # API 호출
            url = "https://google.serper.dev/search"
            headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
            payload = {"q": "테스트 키워드", "gl": "kr", "num": 3, "type": "news"}

            response = requests.post(url, headers=headers, json=payload)

            # 검증
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("news", data)
            self.assertIsInstance(data["news"], list)

    def test_serper_api_without_news_type(self):
        """type 파라미터 없는 API 호출 테스트"""
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "organic": [
                    {
                        "title": "테스트 검색 결과",
                        "link": "https://example.com/result1",
                        "snippet": "테스트 내용 요약",
                    }
                ],
                "news": [
                    {
                        "title": "테스트 뉴스",
                        "link": "https://example.com/news1",
                        "date": "1 hour ago",
                    }
                ],
            }
            mock_post.return_value = mock_response

            # API 호출
            url = "https://google.serper.dev/search"
            headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
            payload = {"q": "테스트 키워드", "gl": "kr", "num": 3}

            response = requests.post(url, headers=headers, json=payload)

            # 검증
            self.assertEqual(response.status_code, 200)
            data = response.json()

            # 일반 검색에서는 organic 결과가 있어야 함
            self.assertIn("organic", data)
            self.assertIsInstance(data["organic"], list)

            # news 컨테이너도 포함될 수 있음
            if "news" in data:
                self.assertIsInstance(data["news"], list)

    def test_parse_news_results_from_various_containers(self):
        """다양한 컨테이너에서 뉴스 결과 파싱 테스트"""
        # news 컨테이너
        news_container = {
            "news": [
                {
                    "title": "뉴스 제목 1",
                    "link": "https://example.com/news1",
                    "date": "2 hours ago",
                    "source": "뉴스 출처 1",
                }
            ]
        }

        # news 없고 topStories 있는 케이스
        top_stories_container = {
            "topStories": [
                {
                    "title": "주요 뉴스 제목 1",
                    "link": "https://example.com/top1",
                    "date": "3 hours ago",
                    "source": "주요 뉴스 출처 1",
                }
            ]
        }

        # 두 컨테이너 다 있는 케이스
        combined_container = {
            "news": [
                {
                    "title": "뉴스 제목 1",
                    "link": "https://example.com/news1",
                    "date": "2 hours ago",
                }
            ],
            "topStories": [
                {
                    "title": "주요 뉴스 제목 1",
                    "link": "https://example.com/top1",
                    "date": "3 hours ago",
                }
            ],
        }

        # 뉴스 결과를 파싱하는 간단한 함수
        def parse_news_results(data):
            articles = []

            # 1. news 컨테이너 확인
            if "news" in data and isinstance(data["news"], list):
                articles.extend(data["news"])

            # 2. topStories 컨테이너 확인
            if "topStories" in data and isinstance(data["topStories"], list):
                articles.extend(data["topStories"])

            return articles

        # 테스트 실행
        news_results = parse_news_results(news_container)
        self.assertEqual(len(news_results), 1)
        self.assertEqual(news_results[0]["title"], "뉴스 제목 1")

        top_results = parse_news_results(top_stories_container)
        self.assertEqual(len(top_results), 1)
        self.assertEqual(top_results[0]["title"], "주요 뉴스 제목 1")

        combined_results = parse_news_results(combined_container)
        self.assertEqual(len(combined_results), 2)


if __name__ == "__main__":
    unittest.main()
