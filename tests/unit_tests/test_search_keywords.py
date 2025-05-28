import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from newsletter.compose import compose_newsletter_html


def test_search_keywords_in_template():
    """Test that search_keywords are correctly displayed in the newsletter template."""
    # Test data with search_keywords
    test_data = {
        "newsletter_topic": "인공지능",
        "generation_date": datetime.now().strftime("%Y-%m-%d"),
        "search_keywords": "챗GPT, 생성형AI, 머신러닝",
        "recipient_greeting": "안녕하세요, 독자 여러분",
        "introduction_message": "이번 뉴스레터에서는 인공지능 관련 주요 동향을 살펴봅니다.",
        "sections": [
            {
                "title": "생성형 AI 발전",
                "summary_paragraphs": [
                    "최근 생성형 AI 기술이 빠르게 발전하고 있습니다."
                ],
                "news_links": [
                    {
                        "title": "ChatGPT 4.0 출시",
                        "url": "https://example.com/chatgpt",
                        "source_and_date": "Tech News, 2023-01-01",
                    }
                ],
            }
        ],
        "closing_message": "다음 뉴스레터에서 다시 만나뵙겠습니다.",
        "editor_signature": "편집자 드림",
        "company_name": "Tech News Co.",
    }

    # Get the template directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(
        os.path.dirname(current_dir)
    )  # Go up two levels to the project root
    template_dir = os.path.join(project_root, "templates")
    template_file = "newsletter_template.html"

    # Create the newsletter HTML
    html_content = compose_newsletter_html(test_data, template_dir, template_file)

    # Check if the search keywords are included in the HTML
    assert "검색 키워드: 챗GPT, 생성형AI, 머신러닝" in html_content

    # Test with empty search_keywords
    test_data_no_keywords = test_data.copy()
    test_data_no_keywords.pop("search_keywords", None)
    html_content_no_keywords = compose_newsletter_html(
        test_data_no_keywords, template_dir, template_file
    )

    # Check that the search keywords section is not present
    assert "검색 키워드:" not in html_content_no_keywords


def test_search_keywords_rendering_with_multiple_formats():
    """Test search_keywords with different input formats."""
    # Test data templates
    test_data_base = {
        "newsletter_topic": "인공지능",
        "generation_date": datetime.now().strftime("%Y-%m-%d"),
        "recipient_greeting": "안녕하세요, 독자 여러분",
        "introduction_message": "이번 뉴스레터에서는 인공지능 관련 주요 동향을 살펴봅니다.",
        "sections": [
            {
                "title": "생성형 AI 발전",
                "summary_paragraphs": [
                    "최근 생성형 AI 기술이 빠르게 발전하고 있습니다."
                ],
            }
        ],
    }

    # Get the template directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(
        os.path.dirname(current_dir)
    )  # Go up two levels to the project root
    template_dir = os.path.join(project_root, "templates")
    template_file = "newsletter_template.html"

    # Test case 1: String keywords
    test_data_string = test_data_base.copy()
    test_data_string["search_keywords"] = "AI, 머신러닝, 딥러닝"
    html_content_string = compose_newsletter_html(
        test_data_string, template_dir, template_file
    )
    assert "검색 키워드: AI, 머신러닝, 딥러닝" in html_content_string

    # Test case 2: List keywords
    test_data_list = test_data_base.copy()
    test_data_list["search_keywords"] = ["AI", "머신러닝", "딥러닝"]
    html_content_list = compose_newsletter_html(
        test_data_list, template_dir, template_file
    )
    assert (
        "검색 키워드: AI, 머신러닝, 딥러닝" in html_content_list
        or "검색 키워드: ['AI', '머신러닝', '딥러닝']" in html_content_list
    )

    # Test case 3: Empty keywords
    test_data_empty = test_data_base.copy()
    test_data_empty["search_keywords"] = ""
    html_content_empty = compose_newsletter_html(
        test_data_empty, template_dir, template_file
    )
    assert "검색 키워드:" not in html_content_empty


if __name__ == "__main__":
    test_search_keywords_in_template()
    test_search_keywords_rendering_with_multiple_formats()
    print("All tests passed!")
