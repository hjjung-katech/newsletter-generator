import unittest
from unittest.mock import patch

import pytest

from newsletter.llm_factory import get_llm_for_task
from newsletter.tools import (
    extract_common_theme_fallback,
    extract_common_theme_from_keywords,
    get_filename_safe_theme,
)


class TestThemeExtraction(unittest.TestCase):
    def test_extract_common_theme_fallback_single_keyword(self):
        """Test that fallback returns single keyword unchanged"""
        result = extract_common_theme_fallback(["AI 기술"])
        self.assertEqual(result, "AI 기술")

    def test_extract_common_theme_fallback_empty_list(self):
        """Test that fallback handles empty list"""
        result = extract_common_theme_fallback([])
        self.assertEqual(result, "")

    def test_extract_common_theme_fallback_multiple_keywords(self):
        """Test that fallback combines multiple keywords correctly"""
        result = extract_common_theme_fallback(["AI", "머신러닝", "딥러닝"])
        self.assertEqual(result, "AI, 머신러닝, 딥러닝")

    def test_extract_common_theme_fallback_more_than_three_keywords(self):
        """Test that fallback formats more than three keywords correctly"""
        result = extract_common_theme_fallback(["AI", "머신러닝", "딥러닝", "자연어처리"])
        self.assertEqual(result, "AI 외 3개 분야")

    def test_extract_common_theme_from_string(self):
        """Test that extract_common_theme handles comma-separated string"""
        result = extract_common_theme_fallback("AI, 머신러닝, 딥러닝")
        self.assertEqual(result, "AI, 머신러닝, 딥러닝")

    @patch(
        "newsletter.tools.extract_common_theme_from_keywords",
        side_effect=lambda x, y=None: "인공지능 기술",
    )
    def test_get_filename_safe_theme_with_domain(self, mock_extract):
        """Test get_filename_safe_theme with domain parameter"""
        result = get_filename_safe_theme(["AI", "머신러닝"], domain="인공지능")
        self.assertEqual(result, "인공지능")
        # Ensure extract_common_theme was not called
        mock_extract.assert_not_called()

    @patch(
        "newsletter.tools.extract_common_theme_from_keywords",
        side_effect=lambda x, y=None: "인공지능 기술",
    )
    def test_get_filename_safe_theme_single_keyword(self, mock_extract):
        """Test get_filename_safe_theme with single keyword"""
        result = get_filename_safe_theme(["AI 기술"])
        self.assertEqual(result, "AI_기술")
        # Ensure extract_common_theme was not called
        mock_extract.assert_not_called()

    @patch(
        "newsletter.tools.extract_common_theme_from_keywords",
        side_effect=lambda x, y=None: "인공지능 기술",
    )
    def test_get_filename_safe_theme_with_string(self, mock_extract):
        """Test get_filename_safe_theme with comma-separated string"""
        result = get_filename_safe_theme("AI, 머신러닝, 딥러닝")
        self.assertEqual(result, "인공지능_기술")
        # Ensure extract_common_theme was called
        mock_extract.assert_called_once()


@patch("newsletter.llm_factory.get_llm_for_task")
def test_extract_common_theme_with_mock(mock_get_llm):
    """Test theme extraction with a mocked LLM"""
    # Mock the LLM response
    mock_llm = mock_get_llm.return_value
    mock_llm.invoke.return_value.content = "기술"

    # Test cases
    result_single = extract_common_theme_from_keywords(["블록체인"])
    result_multiple = extract_common_theme_from_keywords(["AI", "머신러닝"])

    # Assertions
    assert result_single == "기술"  # The mock will return '기술' regardless of input
    assert result_multiple == "기술"

    # Verify that the mock was called
    assert mock_get_llm.called
    assert mock_llm.invoke.called


if __name__ == "__main__":
    unittest.main()
