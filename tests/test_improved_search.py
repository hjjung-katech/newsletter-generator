"""
수정된 search_news_articles 함수 테스트
"""

import unittest
import sys
import os

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 테스트할 모듈 임포트
from newsletter.tools import search_news_articles


class TestImprovedSearch(unittest.TestCase):
    """개선된 검색 기능 테스트 케이스"""

    def test_improved_search_functionality(self):
        """수정된 search_news_articles 함수의 기본 기능 테스트"""
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

    def test_multiple_keywords(self):
        """여러 키워드로 검색하는 기능 테스트"""
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
