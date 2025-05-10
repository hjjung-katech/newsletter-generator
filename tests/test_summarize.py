import sys
import os
# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import patch, MagicMock
from newsletter.summarize import summarize_articles
from newsletter import config # config를 직접 임포트

class TestSummarize(unittest.TestCase):

    @patch('newsletter.summarize.genai.GenerativeModel')
    def test_summarize_articles_success(self, MockGenerativeModel):
        # Mock a successful API call
        mock_model_instance = MockGenerativeModel.return_value
        mock_model_instance.generate_content.return_value.text = "<html><body>Mocked HTML Summary</body></html>"

        # Mock config.GEMINI_API_KEY to ensure the main logic is tested
        with patch.object(config, 'GEMINI_API_KEY', 'fake_gemini_api_key'):
            keywords = ["AI", "머신러닝"]
            articles = [
                {'title': 'Article 1', 'url': 'http://example.com/1', 'content': 'Content 1 about AI.'},
                {'title': 'Article 2', 'url': 'http://example.com/2', 'content': 'Content 2 about Machine Learning.'}
            ]
            html_output = summarize_articles(keywords, articles)

        self.assertEqual(html_output, "<html><body>Mocked HTML Summary</body></html>")
        MockGenerativeModel.assert_called_once_with(
            model_name='gemini-1.5-pro-latest',
            system_instruction=unittest.mock.ANY # SYSTEM_PROMPT는 길어서 ANY로 대체 가능
        )
        mock_model_instance.generate_content.assert_called_once()
        # content_to_summarize가 올바르게 생성되었는지 확인 (일부 키워드 포함 여부 등)
        args, _ = mock_model_instance.generate_content.call_args
        self.assertIn("AI, 머신러닝", args[0])
        self.assertIn("Article 1", args[0])
        self.assertIn("Content 2 about Machine Learning.", args[0])

    def test_summarize_articles_no_api_key(self):
        # Ensure GEMINI_API_KEY is None for this test
        with patch.object(config, 'GEMINI_API_KEY', None):
            keywords = ["테스트"]
            articles = [{'title': 'Test', 'url': 'http://test.com', 'content': 'Test content'}]
            html_output = summarize_articles(keywords, articles)

        self.assertIn("오류: GEMINI_API_KEY가 설정되지 않았습니다.", html_output)
        self.assertIn("테스트", html_output) # 키워드가 포함되었는지 확인
        self.assertIn("제공된 기사 수: 1", html_output)

    @patch('newsletter.summarize.genai.GenerativeModel')
    def test_summarize_articles_api_error(self, MockGenerativeModel):
        # Mock an API error
        mock_model_instance = MockGenerativeModel.return_value
        mock_model_instance.generate_content.side_effect = Exception("Gemini API Error")

        with patch.object(config, 'GEMINI_API_KEY', 'fake_gemini_api_key'):
            keywords = ["에러 테스트"]
            articles = [{'title': 'Error Article', 'url': 'http://error.com', 'content': 'Error content'}]
            html_output = summarize_articles(keywords, articles)

        self.assertIn("오류 발생", html_output)
        self.assertIn("키워드 '에러 테스트'에 대한 뉴스레터 요약 중 오류가 발생했습니다: Gemini API Error", html_output)

    @patch('newsletter.summarize.genai.GenerativeModel')
    def test_summarize_articles_empty_articles(self, MockGenerativeModel):
        mock_model_instance = MockGenerativeModel.return_value
        mock_model_instance.generate_content.return_value.text = "<html><body>No articles summary</body></html>"

        with patch.object(config, 'GEMINI_API_KEY', 'fake_gemini_api_key'):
            keywords = ["빈 기사"]
            articles = []
            html_output = summarize_articles(keywords, articles)
        
        self.assertEqual(html_output, "<html><body>No articles summary</body></html>")
        mock_model_instance.generate_content.assert_called_once()
        args, _ = mock_model_instance.generate_content.call_args
        self.assertIn("빈 기사", args[0])
        self.assertNotIn("기사 제목:", args[0]) # 기사 내용이 없어야 함

    @patch('newsletter.summarize.genai.GenerativeModel')
    def test_summarize_articles_empty_keywords(self, MockGenerativeModel):
        mock_model_instance = MockGenerativeModel.return_value
        mock_model_instance.generate_content.return_value.text = "<html><body>No keywords summary</body></html>"

        with patch.object(config, 'GEMINI_API_KEY', 'fake_gemini_api_key'):
            keywords = []
            articles = [{'title': 'Article', 'url': 'http://example.com', 'content': 'Content'}]
            html_output = summarize_articles(keywords, articles)

        self.assertEqual(html_output, "<html><body>No keywords summary</body></html>")
        mock_model_instance.generate_content.assert_called_once()
        args, _ = mock_model_instance.generate_content.call_args
        self.assertIn("지정된 주제 없음", args[0]) # 키워드가 없을 때의 기본 문자열 확인
        self.assertIn("Article", args[0])

if __name__ == '__main__':
    unittest.main()
