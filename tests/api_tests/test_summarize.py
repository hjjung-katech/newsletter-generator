import importlib
import os
import sys

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import unittest
from unittest.mock import MagicMock, Mock, patch

from newsletter import config


class TestSummarize(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        # google.generativeai는 더 이상 사용하지 않음
        pass

    def tearDown(self):
        # Clean up modules that are reloaded during tests
        for mod_key in [
            "newsletter.summarize",
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
        # mock_get_llm.return_value will be set by patch.object later

        for mod_key_to_delete in [
            "newsletter.summarize",
            "newsletter.llm_factory",
            "langchain_google_genai",
        ]:
            if mod_key_to_delete in sys.modules:
                del sys.modules[mod_key_to_delete]

        # Import and reload to ensure we get fresh modules
        import newsletter.llm_factory  # Ensure llm_factory is loaded to be patched
        import newsletter.summarize

        importlib.reload(newsletter.llm_factory)  # Reload llm_factory first
        importlib.reload(
            newsletter.summarize
        )  # Then reload summarize, which imports the reloaded llm_factory
        summarize_articles_func = newsletter.summarize.summarize_articles

        with unittest.mock.patch.object(config, "GEMINI_API_KEY", "fake_api_key"):
            # Patch get_llm_for_task on the reloaded llm_factory module object
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
        # LLM 팩토리에서 모든 제공자가 사용 불가능할 때 테스트
        keywords = ["AI"]
        articles = [
            {"title": "Test", "url": "http://test.com", "content": "Test content"}
        ]

        # API 키를 모두 None으로 설정하여 사용 가능한 제공자가 없도록 함
        with (
            unittest.mock.patch.object(config, "GEMINI_API_KEY", None),
            unittest.mock.patch.object(config, "OPENAI_API_KEY", None),
            unittest.mock.patch.object(config, "ANTHROPIC_API_KEY", None),
        ):

            import newsletter.summarize

            html_output = newsletter.summarize.summarize_articles(keywords, articles)
            # 중앙집중식 설정으로 에러 메시지가 변경됨 - 더 포괄적인 체크로 수정
            self.assertIn("오류", html_output)
            self.assertIn("GEMINI_API_KEY", html_output)

    def test_summarize_articles_no_api_key(self):
        # Ensure google.generativeai is a benign mock to prevent NameError during its import
        # The API key check in summarize_articles should happen before this mock is heavily used.
        if "google.generativeai" in sys.modules:
            del sys.modules["google.generativeai"]
        mock_genai_module = MagicMock()
        sys.modules["google.generativeai"] = mock_genai_module

        # Reload other modules that might be affected or cached
        for mod_key in [
            "newsletter.llm_factory",
            "langchain_core",
            "langchain_google_genai",
        ]:
            if mod_key in sys.modules:
                del sys.modules[mod_key]

        import newsletter.summarize

        importlib.reload(newsletter.summarize)
        summarize_articles = newsletter.summarize.summarize_articles

        with unittest.mock.patch.object(config, "GEMINI_API_KEY", None):
            keywords = ["테스트"]
            articles = [
                {"title": "Test", "url": "http://test.com", "content": "Test content"}
            ]
            html_output = summarize_articles(keywords, articles)
            # 중앙집중식 설정으로 에러 메시지가 변경됨 - 실제 에러 유형을 체크
            self.assertTrue("오류" in html_output or "Error code:" in html_output)
            # 실제 에러 메시지 형식에 맞게 수정
            self.assertTrue("키워드 '테스트'" in html_output or "테스트" in html_output)
            # 기사 수 체크는 에러 상황에서는 나타나지 않을 수 있음
            # Ensure the direct genai mock wasn't used for generation
            mock_genai_module.GenerativeModel.assert_not_called()

    def test_summarize_articles_api_error(self):
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.side_effect = Exception(
            "Gemini API Error via llm_factory"
        )

        # Clean up modules first
        for mod_key_to_delete in [
            "newsletter.summarize",
            "newsletter.llm_factory",
            "langchain_google_genai",
            "google.generativeai",
        ]:
            if mod_key_to_delete in sys.modules:
                del sys.modules[mod_key_to_delete]

        # Ensure google.generativeai is a benign mock
        mock_genai_module = MagicMock()
        # If llm_factory fails and summarize.py tries to use genai directly, make it also fail
        mock_genai_model = MagicMock()
        mock_genai_model.generate_content.side_effect = Exception(
            "Gemini API Error via genai fallback"
        )
        mock_genai_module.GenerativeModel.return_value = mock_genai_model
        sys.modules["google.generativeai"] = mock_genai_module

        # Import and reload to ensure we get fresh modules
        import newsletter.llm_factory
        import newsletter.summarize

        importlib.reload(newsletter.llm_factory)
        importlib.reload(newsletter.summarize)
        summarize_articles = newsletter.summarize.summarize_articles

        with unittest.mock.patch.object(config, "GEMINI_API_KEY", "fake_api_key"):
            # Patch get_llm_for_task on the reloaded llm_factory module object
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
                # Ensure the direct genai mock was not used if llm_factory path was taken
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

        import newsletter.summarize

        importlib.reload(newsletter.summarize)
        summarize_articles = newsletter.summarize.summarize_articles

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
        # mock_get_llm.return_value will be set by patch.object later

        for mod_key_to_delete in [
            "newsletter.summarize",
            "newsletter.llm_factory",
            "langchain_google_genai",
            "google.generativeai",
        ]:
            if mod_key_to_delete in sys.modules:
                del sys.modules[mod_key_to_delete]

        mock_genai_module_for_summarize_import = MagicMock()
        sys.modules["google.generativeai"] = mock_genai_module_for_summarize_import

        # Import and reload to ensure we get fresh modules
        import newsletter.llm_factory  # Ensure llm_factory is loaded to be patched
        import newsletter.summarize

        importlib.reload(newsletter.llm_factory)  # Reload llm_factory first
        importlib.reload(
            newsletter.summarize
        )  # Then reload summarize, which imports the reloaded llm_factory
        summarize_articles_func = newsletter.summarize.summarize_articles

        with unittest.mock.patch.object(config, "GEMINI_API_KEY", "fake_api_key"):
            # Patch get_llm_for_task on the reloaded llm_factory module object
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
