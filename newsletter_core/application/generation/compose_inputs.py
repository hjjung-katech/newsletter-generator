"""Input normalization and style resolution helpers for compose."""

from __future__ import annotations

from typing import Any, Dict, Tuple


class NewsletterConfig:
    """Newsletter style configuration lookup."""

    @staticmethod
    def get_config(style: str = "detailed") -> Dict[str, Any]:
        configs = {
            "compact": {
                "max_articles": 10,
                "top_articles_count": 3,
                "max_groups": 3,
                "max_definitions": 3,
                "summary_style": "brief",
                "template_name": "newsletter_template_compact.html",
                "title_default": "주간 산업 동향 뉴스 클리핑",
            },
            "detailed": {
                "max_articles": None,
                "top_articles_count": 3,
                "max_groups": 6,
                "max_definitions": None,
                "summary_style": "detailed",
                "template_name": "newsletter_template.html",
                "title_default": "주간 산업 동향 뉴스 클리핑",
            },
            "email_compatible": {
                "max_articles": None,
                "top_articles_count": 3,
                "max_groups": 6,
                "max_definitions": None,
                "summary_style": "detailed",
                "template_name": "newsletter_template_email_compatible.html",
                "title_default": "주간 산업 동향 뉴스 클리핑",
            },
        }
        return configs.get(style, configs["detailed"])


def extract_test_config(data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Extract embedded test configuration without mutating caller input."""
    newsletter_data = data.copy()
    test_config = {}

    if "_test_config" in newsletter_data:
        test_config = newsletter_data.pop("_test_config")

    return newsletter_data, test_config


def _normalize_legacy_article_list(data: list[dict[str, Any]]) -> Dict[str, Any]:
    newsletter_data: Dict[str, Any] = {
        "newsletter_topic": "주간 산업 동향",
        "sections": [
            {
                "title": "주요 기술 동향",
                "summary_paragraphs": ["다음은 지난 한 주간의 주요 기술 동향 요약입니다."],
                "news_links": [],
            }
        ],
    }

    for article in data:
        article_title = article.get("title", "제목 없음")
        article_url = article.get("url", "#")
        article_source = article.get("source", "출처 미상")
        article_date = article.get("date", "날짜 미상")

        newsletter_data["sections"][0]["news_links"].append(
            {
                "title": article_title,
                "url": article_url,
                "source_and_date": f"{article_source}, {article_date}",
            }
        )

        if len(newsletter_data["sections"][0]["summary_paragraphs"]) == 1:
            summary = article.get("summary_text") or article.get("content", "")
            newsletter_data["sections"][0]["summary_paragraphs"] = summary.split(
                "\n\n"
            )[:3]

    return newsletter_data


def normalize_compose_input(data: Any) -> Tuple[Any, Dict[str, Any]]:
    """Normalize legacy compose inputs while preserving compatibility."""
    test_config: Dict[str, Any] = {}

    if isinstance(data, dict):
        data, test_config = extract_test_config(data)

    if isinstance(data, list):
        data = _normalize_legacy_article_list(data)

    return data, test_config


def resolve_style_config(data: Dict[str, Any], style: str) -> Dict[str, Any]:
    """Resolve effective style configuration, including email-compatible overrides."""
    if style != "email_compatible":
        return NewsletterConfig.get_config(style)

    original_template_style = data.get("template_style", "detailed")
    config = NewsletterConfig.get_config(style).copy()
    base_config = NewsletterConfig.get_config(original_template_style).copy()

    config["max_articles"] = base_config["max_articles"]
    config["max_groups"] = base_config["max_groups"]
    config["max_definitions"] = base_config["max_definitions"]
    config["summary_style"] = base_config["summary_style"]

    return config
