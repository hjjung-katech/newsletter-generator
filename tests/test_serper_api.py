"""
Serper.dev API 통합 테스트
- 뉴스 검색 API 호출 및 응답 처리 검증
"""
import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# tools 모듈에서 뉴스 검색 함수 import
from newsletter.tools import search_news_articles

class TestSerperApi(unittest.TestCase):
    """Serper.dev 뉴스 API 호출 테스트 케이스"""
    
    def test_search_news_articles_functionality(self):
        """search_news_articles 함수가 올바르게 동작하는지 테스트합니다"""
        # 테스트할 키워드
        test_keywords = "인공지능"
        results_per_keyword = 2
        
        # API 호출
        articles = search_news_articles.invoke({
            "keywords": test_keywords, 
            "num_results": results_per_keyword
        })
        
        # 결과 검증
        self.assertIsNotNone(articles, "검색 결과가 None입니다")
        self.assertIsInstance(articles, list, "검색 결과가 리스트가 아닙니다")
        
        # 결과가 있을 경우 추가 검증
        if articles:
            # 최소한 하나의 결과 확인
            self.assertGreaterEqual(len(articles), 1, "검색 결과가 없습니다")
            
            # 첫 번째 결과의 필요한 속성 확인
            first_article = articles[0]
            self.assertIsInstance(first_article, dict, "기사 항목이 딕셔너리가 아닙니다")
            
            # 필수 속성 확인
            required_fields = ["title", "link"]
            for field in required_fields:
                self.assertIn(field, first_article, f"기사에 필수 필드 {field}가 없습니다")
                self.assertIsNotNone(first_article[field], f"기사의 {field} 필드가 None입니다")
                self.assertNotEqual(first_article[field], "", f"기사의 {field} 필드가 비어 있습니다")
    
    @patch('newsletter.tools.requests.post')
    def test_search_news_articles_api_call(self, mock_post):
        """search_news_articles 함수가 올바른 API 호출을 하는지 테스트합니다"""
        # 모의 응답 생성
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "news": [
                {
                    "title": "테스트 기사 제목",
                    "link": "https://example.com/article1",
                    "date": "1 hour ago",
                    "source": "테스트 출처",
                    "snippet": "테스트 기사 내용 요약"
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # API 호출
        articles = search_news_articles.invoke({
            "keywords": "테스트", 
            "num_results": 1
        })
        
        # 호출 확인
        mock_post.assert_called_once()
        
        # 호출 인자 검증
        call_args = mock_post.call_args
        self.assertIn('json', call_args[1], "API 호출이 JSON 데이터를 포함하지 않습니다")
        
        # 결과 검증
        self.assertEqual(len(articles), 1, "예상된 기사 수와 일치하지 않습니다")
        self.assertEqual(articles[0]["title"], "테스트 기사 제목", "기사 제목이 일치하지 않습니다")
        self.assertEqual(articles[0]["link"], "https://example.com/article1", "기사 링크가 일치하지 않습니다")

if __name__ == '__main__':
    unittest.main()
