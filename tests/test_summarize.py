import sys
import os

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from unittest.mock import patch
from newsletter.summarize import summarize_articles
from newsletter import config


class TestSummarize(unittest.TestCase):

    def setUp(self):
        # 매 테스트마다 maxDiff를 None으로 설정하여 전체 차이점을 표시
        self.maxDiff = None

    # 실제 Gemini 모델 호출을 피하기 위해 generateContent 메서드를 패치
    @patch("google.generativeai.GenerativeModel.generate_content")
    def test_summarize_articles_success(self, mock_generate_content):
        # 모의 응답 설정
        mock_response = unittest.mock.MagicMock()
        mock_response.text = "<html><body>Mocked HTML Summary</body></html>"
        mock_generate_content.return_value = mock_response

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

            # generate_content 함수 호출 확인
            mock_generate_content.assert_called_once()

            # 첫 번째 인자(리스트)의 첫 번째 항목(문자열)에 필요한 키워드가 포함되어 있는지 검증
            prompt = mock_generate_content.call_args[0][0][0]
            self.assertIn("AI, 머신러닝", prompt)
            self.assertIn("Article 1", prompt)
            self.assertIn("Article 2", prompt)

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

    @patch("google.generativeai.GenerativeModel.generate_content")
    def test_summarize_articles_api_error(self, mock_generate_content):
        # Gemini API 호출 오류
        mock_generate_content.side_effect = Exception("Gemini API Error")

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

    @patch("google.generativeai.GenerativeModel.generate_content")
    def test_summarize_articles_empty_keywords(self, mock_generate_content):
        # 모의 응답 설정
        mock_response = unittest.mock.MagicMock()
        mock_response.text = "<html><body>Empty Keywords Summary</body></html>"
        mock_generate_content.return_value = mock_response

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
            mock_generate_content.assert_called_once()

            # 프롬프트에 '지정된 주제 없음' 문구가 포함되어 있는지 확인
            prompt = mock_generate_content.call_args[0][0][0]
            self.assertIn("지정된 주제 없음", prompt)


if __name__ == "__main__":
    unittest.main()
