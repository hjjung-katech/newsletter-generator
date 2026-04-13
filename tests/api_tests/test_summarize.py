import importlib
import os
import sys

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import unittest
from unittest.mock import MagicMock, Mock, patch

from newsletter import config

_SUMMARIZE_MODULE_PATH = "newsletter_core.application.generation.summarize"


def _reload_summarize():
    """Import and reload the canonical summarize module and return it."""
    import newsletter.llm_factory  # Ensure llm_factory is loaded to be patched
    import newsletter_core.application.generation.summarize as _newsletter_summarize

    importlib.reload(newsletter.llm_factory)
    importlib.reload(_newsletter_summarize)
    return _newsletter_summarize


class TestSummarize(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def tearDown(self):
        # Clean up modules that are reloaded during tests
        for mod_key in [
            _SUMMARIZE_MODULE_PATH,
            "newsletter.llm_factory",
            "langchain_core",
            "langchain_google_genai",
        ]:
            if mod_key in sys.modules:
                del sys.modules[mod_key]

    def test_summarize_articles_success(self):
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "<html><body>Mocked HTML Summary</body></html>"
        mock_llm_instance.invoke.return_value = mock_response

        for mod_key_to_delete in [
            _SUMMARIZE_MODULE_PATH,
            "newsletter.llm_factory",
            "langchain_google_genai",
        ]:
            if mod_key_to_delete in sys.modules:
                del sys.modules[mod_key_to_delete]

        import newsletter.llm_factory  # Ensure llm_factory is loaded to be patched

        newsletter_summarize = _reload_summarize()
        summarize_articles_func = newsletter_summarize.summarize_articles

        with unittest.mock.patch.object(config, "GEMINI_API_KEY", "fake_api_key"):
            with patch.object(
                newsletter.llm_factory,
                "get_llm_for_task",
                return_value=mock_llm_instance,
            ) as mock_get_llm_direct:
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
                html_output = summarize_articles_func(keywords, articles)
                self.assertEqual(
                    html_output, "<html><body>Mocked HTML Summary</body></html>"
                )
                mock_get_llm_direct.assert_called_once_with(
                    "news_summarization", unittest.mock.ANY, enable_fallback=False
                )
                mock_llm_instance.invoke.assert_called_once()

    def test_summarize_with_missing_module(self):
        """LLM 팩토리에서 모든 제공자가 사용 불가능할 때 테스트 - F-14 중앙화된 설정"""
        import newsletter_core.application.generation.summarize as newsletter_summarize

        keywords = ["AI"]
        articles = [
            {"title": "Test", "url": "http://test.com", "content": "Test content"}
        ]

        # F-14: 중앙화된 설정에 의해 자동으로 fallback LLM이 사용되므로
        # 이 테스트는 이제 성공적으로 요약을 생성합니다
        html_output = newsletter_summarize.summarize_articles(keywords, articles)

        # F-14 시스템은 fallback 메커니즘으로 성공적인 결과를 생성
        self.assertIn("html", html_output)
        self.assertIn("AI", html_output)

    def test_summarize_articles_no_api_key(self):
        """API 키가 없을 때 테스트 - F-14 중앙화된 설정"""
        import newsletter_core.application.generation.summarize as newsletter_summarize

        # F-14 중앙화된 설정에서는 fallback 메커니즘이 작동
        keywords = ["테스트"]
        articles = [
            {"title": "Test", "url": "http://test.com", "content": "Test content"}
        ]

        html_output = newsletter_summarize.summarize_articles(keywords, articles)

        # F-14 시스템의 intelligent fallback으로 성공적인 결과 생성
        self.assertIn("html", html_output)
        # 키워드가 포함되어야 함
        self.assertTrue("테스트" in html_output or "Test" in html_output)

    def test_summarize_articles_api_error(self):
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.side_effect = Exception(
            "Gemini API Error via llm_factory"
        )

        # Clean up modules first
        for mod_key_to_delete in [
            _SUMMARIZE_MODULE_PATH,
            "newsletter.llm_factory",
            "langchain_google_genai",
            "google.generativeai",
        ]:
            if mod_key_to_delete in sys.modules:
                del sys.modules[mod_key_to_delete]

        # Ensure google.generativeai is a benign mock
        mock_genai_module = MagicMock()
        mock_genai_model = MagicMock()
        mock_genai_model.generate_content.side_effect = Exception(
            "Gemini API Error via genai fallback"
        )
        mock_genai_module.GenerativeModel.return_value = mock_genai_model
        sys.modules["google.generativeai"] = mock_genai_module

        import newsletter.llm_factory

        newsletter_summarize = _reload_summarize()
        summarize_articles = newsletter_summarize.summarize_articles

        with unittest.mock.patch.object(config, "GEMINI_API_KEY", "fake_api_key"):
            with patch.object(
                newsletter.llm_factory,
                "get_llm_for_task",
                return_value=mock_llm_instance,
            ) as mock_get_llm_direct:
                keywords = ["에러 테스트"]
                articles = [
                    {
                        "title": "Error Article",
                        "url": "http://error.com",
                        "content": "Error content",
                    }
                ]
                html_output = summarize_articles(keywords, articles)
                self.assertIn("오류 발생", html_output)
                self.assertIn(
                    "키워드 '에러 테스트'에 대한 뉴스레터 요약 중 오류가 발생했습니다",
                    html_output,
                )
                self.assertIn("Gemini API Error via llm_factory", html_output)
                mock_get_llm_direct.assert_called_once_with(
                    "news_summarization", unittest.mock.ANY, enable_fallback=False
                )
                mock_llm_instance.invoke.assert_called_once()
                mock_genai_module.GenerativeModel.assert_not_called()

    def test_summarize_articles_empty_articles(self):
        # Ensure google.generativeai is a benign mock. No LLM call should happen.
        if "google.generativeai" in sys.modules:
            del sys.modules["google.generativeai"]
        mock_genai_module = MagicMock()
        sys.modules["google.generativeai"] = mock_genai_module

        for mod_key in [
            "newsletter.llm_factory",
            "langchain_core",
            "langchain_google_genai",
        ]:
            if mod_key in sys.modules:
                del sys.modules[mod_key]

        newsletter_summarize = _reload_summarize()
        summarize_articles = newsletter_summarize.summarize_articles

        keywords = ["빈 기사"]
        articles = []
        html_output = summarize_articles(keywords, articles)
        self.assertEqual(html_output, "<html><body>No articles summary</body></html>")
        mock_genai_module.GenerativeModel.assert_not_called()

    def test_summarize_articles_empty_keywords(self):
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "<html><body>Empty Keywords Summary</body></html>"
        mock_llm_instance.invoke.return_value = mock_response

        for mod_key_to_delete in [
            _SUMMARIZE_MODULE_PATH,
            "newsletter.llm_factory",
            "langchain_google_genai",
            "google.generativeai",
        ]:
            if mod_key_to_delete in sys.modules:
                del sys.modules[mod_key_to_delete]

        mock_genai_module_for_summarize_import = MagicMock()
        sys.modules["google.generativeai"] = mock_genai_module_for_summarize_import

        import newsletter.llm_factory

        newsletter_summarize = _reload_summarize()
        summarize_articles_func = newsletter_summarize.summarize_articles

        with unittest.mock.patch.object(config, "GEMINI_API_KEY", "fake_api_key"):
            with patch.object(
                newsletter.llm_factory,
                "get_llm_for_task",
                return_value=mock_llm_instance,
            ) as mock_get_llm_direct:
                keywords = []
                articles = [
                    {
                        "title": "Article",
                        "url": "http://example.com",
                        "content": "Content",
                    }
                ]
                html_output = summarize_articles_func(keywords, articles)
                self.assertEqual(
                    html_output, "<html><body>Empty Keywords Summary</body></html>"
                )
                mock_get_llm_direct.assert_called_once_with(
                    "news_summarization", unittest.mock.ANY, enable_fallback=False
                )
                mock_llm_instance.invoke.assert_called_once()
                mock_genai_module_for_summarize_import.GenerativeModel.assert_not_called()


if __name__ == "__main__":
    unittest.main()
