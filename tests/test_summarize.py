import sys
import os

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from unittest.mock import patch, Mock

# newsletter.summarize 모듈의 genai 변수를 패치
genai_patch = patch("newsletter.summarize.genai", new=Mock())
genai_patch.start()

from newsletter.summarize import summarize_articles
from newsletter import config


class TestSummarize(unittest.TestCase):

    def setUp(self):
        # 매 테스트마다 maxDiff를 None으로 설정하여 전체 차이점을 표시
        self.maxDiff = None

    def tearDown(self):
        genai_patch.stop()

    # 실제 Gemini 모델 호출을 피하기 위해 generateContent 메서드를 패치
    @patch("newsletter.summarize.genai")
    def test_summarize_articles_success(self, mock_genai):
        # genai 모듈 설정
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "<html><body>Mocked HTML Summary</body></html>"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        # genai는 None이 아니도록 설정
        mock_genai.__bool__.return_value = True

        # API 키 설정
        with patch.object(config, "GEMINI_API_KEY", "fake_api_key"):
            keywords = ["AI", "머신러닝"]
            articles = [
                {
                    "title": "Article 1",
                    "url": "http://example.com/1",
                    "content": "Content 1 about AI.",
                },
                {
                    "title": "Article 2",
                    "url": "http://example.com/2",
                    "content": "Content 2 about Machine Learning.",
                },
            ]

            # 함수 호출
            html_output = summarize_articles(keywords, articles)

            # 반환값 검증
            self.assertEqual(
                html_output, "<html><body>Mocked HTML Summary</body></html>"
            )

            # generative_model 인스턴스화 및 generate_content 호출 확인
            mock_genai.GenerativeModel.assert_called_once()
            mock_model.generate_content.assert_called_once()

    @patch("newsletter.summarize.genai", None)
    def test_summarize_with_missing_module(self):
        """Test summarize_articles when generativeai module is not available"""
        keywords = ["AI"]
        articles = [
            {"title": "Test", "url": "http://test.com", "content": "Test content"}
        ]

        html_output = summarize_articles(keywords, articles)

        # 모듈이 없을 때 적절한 오류 메시지 반환 검증
        self.assertIn("오류: google.generativeai 모듈을 찾을 수 없습니다", html_output)
        self.assertIn("pip install google-generativeai", html_output)

    def test_summarize_articles_no_api_key(self):
        # API 키가 없는 경우
        with patch.object(config, "GEMINI_API_KEY", None):
            keywords = ["테스트"]
            articles = [
                {"title": "Test", "url": "http://test.com", "content": "Test content"}
            ]

            # 함수 호출
            html_output = summarize_articles(keywords, articles)

            # 오류 메시지에 필요한 정보가 포함되어 있는지 검증
            self.assertIn("오류: GEMINI_API_KEY가 설정되지 않았습니다", html_output)
            self.assertIn("키워드: 테스트", html_output)
            self.assertIn("제공된 기사 수: 1", html_output)

    @patch("newsletter.summarize.genai")
    def test_summarize_articles_api_error(self, mock_genai):
        # 모델 설정
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("Gemini API Error")
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.__bool__.return_value = True

        with patch.object(config, "GEMINI_API_KEY", "fake_api_key"):
            keywords = ["에러 테스트"]
            articles = [
                {
                    "title": "Error Article",
                    "url": "http://error.com",
                    "content": "Error content",
                }
            ]

            # 함수 호출
            html_output = summarize_articles(keywords, articles)

            # 오류 메시지 검증
            self.assertIn("오류 발생", html_output)
            self.assertIn(
                "키워드 '에러 테스트'에 대한 뉴스레터 요약 중 오류가 발생했습니다",
                html_output,
            )
            self.assertIn("Gemini API Error", html_output)

    def test_summarize_articles_empty_articles(self):
        # 빈 기사 목록
        keywords = ["빈 기사"]
        articles = []

        # 함수 호출
        html_output = summarize_articles(keywords, articles)

        # 결과 검증 - 빈 기사 메시지 포함 여부
        self.assertEqual(html_output, "<html><body>No articles summary</body></html>")

    @patch("newsletter.summarize.genai")
    def test_summarize_articles_empty_keywords(self, mock_genai):
        # 모델 설정
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "<html><body>Empty Keywords Summary</body></html>"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.__bool__.return_value = True

        with patch.object(config, "GEMINI_API_KEY", "fake_api_key"):
            keywords = []
            articles = [
                {"title": "Article", "url": "http://example.com", "content": "Content"}
            ]

            # 함수 호출
            html_output = summarize_articles(keywords, articles)

            # 결과 검증
            self.assertEqual(
                html_output, "<html><body>Empty Keywords Summary</body></html>"
            )

            # generate_content 호출 확인
            mock_model.generate_content.assert_called_once()


if __name__ == "__main__":
    unittest.main()
