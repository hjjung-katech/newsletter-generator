import os
import unittest
from unittest.mock import patch, Mock

from newsletter import config
from newsletter.chains import get_llm
from newsletter.tools import generate_keywords_with_gemini
from newsletter.summarize import summarize_articles


class TestCostTracking(unittest.TestCase):
    @patch("newsletter.cost_tracking.LangSmithCallbackHandler")
    @patch("newsletter.chains.ChatGoogleGenerativeAI")
    def test_get_llm_tracking_enabled(self, mock_llm, mock_cb):
        with patch.object(config, "GEMINI_API_KEY", "key"):
            os.environ["ENABLE_COST_TRACKING"] = "1"
            get_llm()
            mock_llm.assert_called_once()
            self.assertIn(mock_cb.return_value, mock_llm.call_args.kwargs["callbacks"])
            os.environ.pop("ENABLE_COST_TRACKING", None)

    @patch("newsletter.cost_tracking.LangSmithCallbackHandler")
    @patch("newsletter.tools.ChatGoogleGenerativeAI")
    def test_generate_keywords_with_tracking(self, mock_llm, mock_cb):
        with patch.object(config, "GEMINI_API_KEY", "key"):
            os.environ["ENABLE_COST_TRACKING"] = "1"
            generate_keywords_with_gemini("AI", count=1)
            mock_llm.assert_called_once()
            self.assertIn(mock_cb.return_value, mock_llm.call_args.kwargs["callbacks"])
            os.environ.pop("ENABLE_COST_TRACKING", None)

    @patch("newsletter.cost_tracking.LangSmithCallbackHandler")
    @patch("newsletter.summarize.genai")
    def test_summarize_articles_with_tracking(self, mock_genai, mock_cb):
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.__bool__.return_value = True
        with patch.object(config, "GEMINI_API_KEY", "key"):
            os.environ["ENABLE_COST_TRACKING"] = "1"
            summarize_articles(["AI"], [{"title": "t", "url": "u", "content": "c"}])
            mock_cb.return_value.on_llm_end.assert_called_once_with(mock_response)
            os.environ.pop("ENABLE_COST_TRACKING", None)


if __name__ == "__main__":
    unittest.main()
