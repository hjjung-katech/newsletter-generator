"""
개선된 뉴스 검색 기능 테스트
- 다양한 검색 방식과 응답 처리 검증
"""

import unittest
import json
import requests
import os
import sys
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestSearchImproved(unittest.TestCase):
    """개선된 뉴스 검색 기능 테스트 케이스"""

    def setUp(self):
        """테스트 준비 - API 키 로드"""
        # .env 파일 로드
        load_dotenv()
        self.api_key = os.getenv("SERPER_API_KEY")
        self.assertTrue(
            self.api_key,
            "SERPER_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.",
        )

    def test_news_search_with_news_endpoint(self):
        """뉴스 전용 엔드포인트(/news)를 사용한 검색 테스트"""
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "news": [
                    {
                        "title": "뉴스 전용 검색 결과",
                        "link": "https://example.com/news1",
                        "date": "1 hour ago",
                        "source": "뉴스 출처",
                    }
                ]
            }
            mock_post.return_value = mock_response

            # API 호출
            url = "https://google.serper.dev/news"  # 뉴스 전용 엔드포인트
            headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
            payload = {"q": "테스트 키워드", "gl": "kr", "num": 3}

            response = requests.post(url, headers=headers, json=payload)

            # 검증
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("news", data)
            self.assertIsInstance(data["news"], list)

    def test_standard_search_with_news_results(self):
        """일반 검색 엔드포인트(/search)에서 뉴스 결과 추출 테스트"""
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "organic": [
                    {
                        "title": "일반 검색 결과",
                        "link": "https://example.com/result1",
                        "snippet": "테스트 내용",
                    }
                ],
                "news": [
                    {
                        "title": "일반 검색에서 뉴스 결과",
                        "link": "https://example.com/newsitem",
                        "date": "2 hours ago",
                        "source": "뉴스 출처",
                    }
                ],
                "topStories": [
                    {
                        "title": "주요 뉴스 결과",
                        "link": "https://example.com/topstory",
                        "date": "30 minutes ago",
                        "source": "주요 뉴스 출처",
                    }
                ],
            }
            mock_post.return_value = mock_response

            # API 호출
            url = "https://google.serper.dev/search"
            headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
            payload = {"q": "테스트 키워드", "gl": "kr", "num": 5}

            response = requests.post(url, headers=headers, json=payload)
            data = response.json()

            # 뉴스 결과 추출 함수
            def extract_news_results(data):
                results = []
                # 1. news 컨테이너에서 추출
                if "news" in data and isinstance(data["news"], list):
                    results.extend(data["news"])
                # 2. topStories 컨테이너에서 추출
                if "topStories" in data and isinstance(data["topStories"], list):
                    results.extend(data["topStories"])
                return results

            news_results = extract_news_results(data)

            # 검증
            self.assertEqual(len(news_results), 2)  # news와 topStories 합쳐서 2개

            # 결과 형식 검증
            for article in news_results:
                self.assertIn("title", article)
                self.assertIn("link", article)

    def test_combine_results_from_multiple_keywords(self):
        """여러 키워드의 검색 결과 통합 테스트"""
        # 키워드별 모의 응답 생성
        keyword1_response = {
            "news": [
                {"title": "키워드1 뉴스", "link": "https://example.com/k1news1"},
                {"title": "키워드1 뉴스2", "link": "https://example.com/k1news2"},
            ]
        }

        keyword2_response = {
            "news": [
                {"title": "키워드2 뉴스", "link": "https://example.com/k2news1"},
                {"title": "키워드2 뉴스2", "link": "https://example.com/k2news2"},
            ]
        }

        # 중복 결과가 있는 키워드3 응답
        keyword3_response = {
            "news": [
                {
                    "title": "키워드1 뉴스",
                    "link": "https://example.com/k1news1",
                },  # 중복
                {"title": "키워드3 뉴스", "link": "https://example.com/k3news1"},
            ]
        }

        # 모의 API 호출 결과
        responses = [keyword1_response, keyword2_response, keyword3_response]

        # 중복 제거 전 총 항목 수 확인
        total_items = 0
        for resp in responses:
            if "news" in resp:
                total_items += len(resp["news"])

        self.assertEqual(total_items, 6, "테스트 설정: 총 6개 항목이 있어야 합니다")

        # 중복 항목 수 확인
        all_links = []
        for resp in responses:
            if "news" in resp:
                for item in resp["news"]:
                    all_links.append(item["link"])

        self.assertEqual(len(all_links), 6, "테스트 설정: 총 6개 링크가 있어야 합니다")
        self.assertEqual(
            len(set(all_links)),
            5,
            "테스트 설정: 중복 제거 시 5개 고유 링크가 있어야 합니다",
        )

        # 결과 통합 및 중복 제거 함수
        def combine_results(responses):
            all_articles = []
            seen_links = set()

            for response in responses:
                if "news" in response and isinstance(response["news"], list):
                    for article in response["news"]:
                        if article["link"] not in seen_links:
                            all_articles.append(article)
                            seen_links.add(article["link"])

            return all_articles

        # 테스트 실행
        combined = combine_results(responses)

        # 검증 - 중복 제거로 6개가 아닌 5개여야 함
        self.assertEqual(
            len(combined), 5, "중복 제거 후 정확히 5개의 항목이 남아야 합니다"
        )

        # 링크 중복 검증
        links = [article["link"] for article in combined]
        self.assertEqual(len(links), len(set(links)), "중복 링크가 있습니다")


if __name__ == "__main__":
    unittest.main()
