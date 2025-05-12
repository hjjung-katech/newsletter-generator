"""
날짜 형식 파서 테스트
minutes ago 형식의 상대적 시간 파싱 기능 검증
"""
import unittest
import sys
import os
from datetime import datetime, timedelta, timezone
import re

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# graph.py에서 날짜 파싱 함수 import
from newsletter.graph import parse_article_date_for_graph

class TestGraphDateParser(unittest.TestCase):
    """그래프 날짜 파싱 기능 테스트 케이스"""
    
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
        
        # Common format
        result = parse_article_date_for_graph("Oct 15, 2023")
        self.assertIsNotNone(result)

if __name__ == '__main__':
    unittest.main()
