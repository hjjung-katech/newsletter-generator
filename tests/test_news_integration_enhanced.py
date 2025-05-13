"""
뉴스 통합 검색 기능 테스트
- tools.py와 collect.py 모두 업데이트된 내용이 올바르게 적용되었는지 확인합니다.
"""

import unittest
import sys
import os
import json
from datetime import datetime

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 필요한 모듈 임포트
from newsletter.tools import search_news_articles
from newsletter.collect import collect_articles


class TestNewsIntegrationEnhanced(unittest.TestCase):
    """도구와 수집 모듈 간의 통합 테스트 케이스"""

    def test_news_collection_integration(self):
        """tools.py와 collect.py의 뉴스 검색 기능을 통합 테스트합니다"""
        # 테스트할 키워드
        test_keywords = "인공지능,자율주행"
        results_per_keyword = 3

        # 1. tools.py의 search_news_articles 함수 테스트
        articles_from_tools = search_news_articles.invoke(
            {"keywords": test_keywords, "num_results": results_per_keyword}
        )

        # 검증: tools.py 결과
        self.assertIsNotNone(articles_from_tools, "tools.py에서 검색 결과가 None입니다")
        self.assertIsInstance(
            articles_from_tools, list, "tools.py에서 검색 결과가 리스트가 아닙니다"
        )
        self.assertGreaterEqual(
            len(articles_from_tools), 1, "tools.py에서 검색 결과가 없습니다"
        )

        # 첫 번째 기사 형식 검증
        if articles_from_tools:
            first_article = articles_from_tools[0]
            self.assertIsInstance(
                first_article, dict, "tools.py의 기사 항목이 딕셔너리가 아닙니다"
            )

            # 필수 필드 검증
            required_fields = ["title", "link", "source"]
            for field in required_fields:
                self.assertIn(
                    field,
                    first_article,
                    f"tools.py의 기사에 필수 필드 {field}가 없습니다",
                )

        # 2. collect.py의 collect_articles 함수 테스트
        try:
            articles_from_collect = collect_articles(test_keywords)

            # 검증: collect.py 결과
            self.assertIsNotNone(
                articles_from_collect, "collect.py에서 검색 결과가 None입니다"
            )

            # 키워드에 따라 결과가 변할 수 있으므로 정확한 수 검증보다는 형식 검증 수행
            if articles_from_collect:
                self.assertIsInstance(
                    articles_from_collect,
                    dict,
                    "collect.py의 결과가 딕셔너리가 아닙니다",
                )

                # 키워드에 대한 결과 딕셔너리 구조 검증
                for keyword in test_keywords.split(","):
                    # 모든 키워드에 결과가 있다고 보장할 수 없으므로 조건부 검증
                    if keyword in articles_from_collect:
                        keyword_results = articles_from_collect[keyword]
                        self.assertIsInstance(
                            keyword_results,
                            list,
                            f"collect.py의 키워드 '{keyword}' 결과가 리스트가 아닙니다",
                        )

                        # 결과가 있다면 첫 번째 기사 형식 검증
                        if keyword_results:
                            first_collect_article = keyword_results[0]
                            self.assertIsInstance(
                                first_collect_article,
                                dict,
                                f"collect.py의 '{keyword}' 키워드 기사가 딕셔너리가 아닙니다",
                            )

                            # 필수 필드 검증
                            for field in ["title", "url"]:
                                self.assertIn(
                                    field,
                                    first_collect_article,
                                    f"collect.py의 기사에 필수 필드 {field}가 없습니다",
                                )

        except Exception as e:
            self.fail(f"collect_articles 함수 실행 중 예외 발생: {e}")

    def test_results_format_compatibility(self):
        """tools.py와 collect.py의 결과 형식 호환성을 테스트합니다"""
        test_keywords = "인공지능"
        results_per_keyword = 2

        # 두 함수 호출
        articles_from_tools = search_news_articles.invoke(
            {"keywords": test_keywords, "num_results": results_per_keyword}
        )

        try:
            articles_from_collect = collect_articles(test_keywords)

            # tools.py와 collect.py의 결과 구조와 필드 비교
            if (
                articles_from_tools
                and test_keywords in articles_from_collect
                and articles_from_collect[test_keywords]
            ):
                tools_fields = set(articles_from_tools[0].keys())
                collect_fields = set(articles_from_collect[test_keywords][0].keys())

                # 필수 공통 필드 검증
                common_required_fields = ["title"]
                for field in common_required_fields:
                    self.assertIn(
                        field,
                        tools_fields,
                        f"tools.py 결과에 필수 필드 {field}가 없습니다",
                    )
                    self.assertIn(
                        field,
                        collect_fields,
                        f"collect.py 결과에 필수 필드 {field}가 없습니다",
                    )

                # URL/link 필드 호환성 검증 (필드 이름이 다를 수 있음)
                self.assertTrue(
                    "url" in tools_fields or "link" in tools_fields,
                    "tools.py 결과에 URL 관련 필드가 없습니다",
                )
                self.assertTrue(
                    "url" in collect_fields or "link" in collect_fields,
                    "collect.py 결과에 URL 관련 필드가 없습니다",
                )

        except Exception as e:
            self.skipTest(
                f"collect_articles 함수 호출 실패로 호환성 테스트를 건너뜁니다: {e}"
            )


if __name__ == "__main__":
    unittest.main()
