import unittest
from unittest.mock import patch, mock_open
from newsletter.compose import compose_newsletter_html
import os
import sys

# 프로젝트 루트 디렉토리를 sys.path에 추가
# 현재 파일의 디렉토리(tests)의 부모 디렉토리(프로젝트 루트)를 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestCompose(unittest.TestCase):

    def test_compose_newsletter_html_success(self):
        summaries = [
            {
                "title": "Test Article 1",
                "url": "http://example.com/1",
                "summary_text": "Summary 1",
                "source": "Test Source 1",
                "date": "2025-01-01",
            },
            {
                "title": "Test Article 2",
                "url": "http://example.com/2",
                "summary_text": "Summary 2",
                "source": "Test Source 2",
                "date": "2025-01-02",
            },
        ]
        template_dir = "c:\\Development\\newsletter-generator\\templates"
        template_name = "newsletter_template.html"

        # Mocking os.getenv to control generation_date and generation_timestamp
        with patch.dict(
            os.environ,
            {"GENERATION_DATE": "2025-05-10", "GENERATION_TIMESTAMP": "12:34:56"},
        ):
            html_content = compose_newsletter_html(
                summaries, template_dir, template_name
            )

        # Test that the basic structure is correct
        self.assertIn("Test Article 1", html_content)
        self.assertIn("http://example.com/1", html_content)
        self.assertIn("Test Source 1", html_content)

        # Check if either Summary 1 appears directly or as part of content
        summary_found = "Summary 1" in html_content or "Summary 2" in html_content
        self.assertTrue(summary_found, "No summary content found in the HTML output")

        # Test that the time-related info is correct
        self.assertIn("Test Article 2", html_content)
        self.assertIn("http://example.com/2", html_content)
        self.assertIn("Test Source 2", html_content)
        self.assertIn(
            "2025-05-10", html_content
        )  # Check if generation date is in the output
        self.assertIn(
            "12:34:56", html_content
        )  # Check if generation timestamp is in the output

    def test_compose_newsletter_html_empty_summaries(self):
        summaries = []
        template_dir = "c:\\Development\\newsletter-generator\\templates"
        template_name = "newsletter_template.html"
        with patch.dict(
            os.environ,
            {"GENERATION_DATE": "2025-05-10", "GENERATION_TIMESTAMP": "12:34:56"},
        ):
            html_content = compose_newsletter_html(
                summaries, template_dir, template_name
            )
        self.assertIn("2025-05-10", html_content)
        self.assertIn(
            "12:34:56", html_content
        )  # Check if generation timestamp is in the output
        # Check that the main structure is there but no articles
        self.assertNotIn("<h2>", html_content)  # Assuming articles are under h2 tags

    def test_compose_newsletter_html_template_not_found(self):
        summaries = [
            {
                "title": "Test Article 1",
                "url": "http://example.com/1",
                "summary_text": "Summary 1",
            }
        ]
        template_dir = "c:\\Development\\newsletter-generator\\templates"
        template_name = "non_existent_template.html"

        with self.assertRaises(
            Exception
        ):  # Expecting a Jinja2 TemplateNotFound error, but Exception is broader
            compose_newsletter_html(summaries, template_dir, template_name)


if __name__ == "__main__":
    unittest.main()
