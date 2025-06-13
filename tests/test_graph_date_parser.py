"""
날짜 형식 파서 테스트
minutes ago 형식의 상대적 시간 파싱 기능 검증
"""

import os
import re
import sys
import unittest
from datetime import datetime, timedelta, timezone

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# graph.py에서 날짜 파싱 함수 import
from newsletter.graph import parse_article_date_for_graph


class TestGraphDateParser(unittest.TestCase):
    """그래프 날짜 파싱 기능 테스트 케이스"""

    def setUp(self):
        """각 테스트 전에 실행되는 설정"""
        # F-14: 테스트 격리를 위한 설정 클리어
        from newsletter.centralized_settings import (
            clear_settings_cache,
            disable_test_mode,
        )

        clear_settings_cache()
        disable_test_mode()

    def tearDown(self):
        """각 테스트 후에 실행되는 정리"""
        # F-14: 테스트 격리를 위한 설정 클리어
        from newsletter.centralized_settings import (
            clear_settings_cache,
            disable_test_mode,
        )

        clear_settings_cache()
        disable_test_mode()

    def test_relative_time_parsing_english(self):
        """영어 상대적 시간 형식 파싱 테스트"""
        now = datetime.now(timezone.utc)

        # Minutes ago format
        result = parse_article_date_for_graph("38 minutes ago")
        self.assertIsNotNone(result)
        expected = now - timedelta(minutes=38)
        # Allow small differences due to test execution time
        self.assertLess(abs((result - expected).total_seconds()), 5)

        # Single minute format
        result = parse_article_date_for_graph("1 minute ago")
        self.assertIsNotNone(result)
        expected = now - timedelta(minutes=1)
        self.assertLess(abs((result - expected).total_seconds()), 5)

        # Hour format
        result = parse_article_date_for_graph("1 hour ago")
        self.assertIsNotNone(result)
        expected = now - timedelta(hours=1)
        self.assertLess(abs((result - expected).total_seconds()), 5)

    def test_relative_time_parsing_korean(self):
        """한국어 상대적 시간 형식 파싱 테스트"""
        now = datetime.now(timezone.utc)

        # Minutes format (Korean)
        result = parse_article_date_for_graph("38분 전")
        self.assertIsNotNone(result)
        expected = now - timedelta(minutes=38)
        self.assertLess(abs((result - expected).total_seconds()), 5)

        # Hour format (Korean)
        result = parse_article_date_for_graph("1시간 전")
        self.assertIsNotNone(result)
        expected = now - timedelta(hours=1)
        self.assertLess(abs((result - expected).total_seconds()), 5)

    def test_standard_date_formats(self):
        """표준 날짜 형식 파싱 테스트"""
        # ISO format
        result = parse_article_date_for_graph("2023-10-15T14:30:00Z")
        expected = datetime(2023, 10, 15, 14, 30, 0, tzinfo=timezone.utc)
        self.assertEqual(result, expected)

        # Common format - 더 안정적인 테스트로 변경
        test_date = "Oct 15, 2023"
        result = parse_article_date_for_graph(test_date)

        # F-14: 디버깅을 위한 로그 추가
        if result is None:
            # 직접 date_utils에서 테스트
            from newsletter.date_utils import parse_date_string

            direct_result = parse_date_string(test_date)
            print(f"F-14 Debug: parse_article_date_for_graph('{test_date}') = {result}")
            print(f"F-14 Debug: parse_date_string('{test_date}') = {direct_result}")

        self.assertIsNotNone(result, f"Failed to parse date: {test_date}")

        # 추가 검증: 결과가 유효한 datetime 객체인지 확인
        if result is not None:
            self.assertIsInstance(result, datetime)
            self.assertEqual(result.year, 2023)
            self.assertEqual(result.month, 10)
            self.assertEqual(result.day, 15)


if __name__ == "__main__":
    unittest.main()
