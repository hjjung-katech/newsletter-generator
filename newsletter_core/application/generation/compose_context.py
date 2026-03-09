"""Render-context and settings helpers for compose."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List

import yaml


def build_render_context(
    data: Dict[str, Any],
    config: Dict[str, Any],
    top_articles: List[Dict[str, Any]],
    grouped_sections: List[Dict[str, Any]],
    definitions: List[Dict[str, str]],
    food_for_thought: Any,
) -> Dict[str, Any]:
    """Build the final template context for the active compose style."""
    generation_date, generation_timestamp = resolve_generation_metadata(data)
    newsletter_settings = load_newsletter_settings()
    newsletter_topic = data.get("newsletter_topic")
    newsletter_title = resolve_newsletter_title(
        data, newsletter_settings, config["title_default"]
    )
    common_context = build_common_context(
        data=data,
        newsletter_settings=newsletter_settings,
        generation_date=generation_date,
        generation_timestamp=generation_timestamp,
        newsletter_topic=newsletter_topic,
        newsletter_title=newsletter_title,
        top_articles=top_articles,
        definitions=definitions,
        food_for_thought=food_for_thought,
    )

    if config["template_name"] == "newsletter_template_compact.html":
        return {
            **common_context,
            "tagline": data.get(
                "tagline",
                newsletter_settings.get("tagline", "이번 주, 주요 산업 동향을 미리 만나보세요."),
            ),
            "grouped_sections": grouped_sections,
        }

    if config["template_name"] == "newsletter_template_email_compatible.html":
        context = {
            **common_context,
            "recipient_greeting": data.get("recipient_greeting", "안녕하세요,"),
            "introduction_message": data.get(
                "introduction_message",
                "지난 한 주간의 주요 산업 동향을 정리해 드립니다.",
            ),
            "closing_message": data.get(
                "closing_message",
                "다음 주에 더 유익한 정보로 찾아뵙겠습니다. 감사합니다.",
            ),
            "editor_signature": data.get("editor_signature", "편집자 드림"),
            "template_style": data.get("template_style", "detailed"),
            "grouped_sections": grouped_sections,
            "sections": data.get("sections", []),
        }
        return _append_search_keywords(context, data.get("search_keywords"))

    context = {
        **common_context,
        "recipient_greeting": data.get("recipient_greeting", "안녕하세요,"),
        "introduction_message": data.get(
            "introduction_message",
            "지난 한 주간의 주요 산업 동향을 정리해 드립니다.",
        ),
        "sections": data.get("sections", []),
        "closing_message": data.get(
            "closing_message",
            "다음 주에 더 유익한 정보로 찾아뵙겠습니다. 감사합니다.",
        ),
        "editor_signature": data.get("editor_signature", "편집자 드림"),
    }
    return _append_search_keywords(context, data.get("search_keywords"))


def resolve_generation_metadata(data: Dict[str, Any]) -> tuple[str, str]:
    """Resolve generation date/timestamp from payload or environment defaults."""
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")
    generation_date = data.get(
        "generation_date", os.environ.get("GENERATION_DATE", current_date)
    )
    generation_timestamp = data.get(
        "generation_timestamp", os.environ.get("GENERATION_TIMESTAMP", current_time)
    )
    return generation_date, generation_timestamp


def resolve_newsletter_title(
    data: Dict[str, Any], newsletter_settings: Dict[str, Any], title_default: str
) -> str:
    """Resolve the effective newsletter title while preserving legacy rules."""
    newsletter_title = data.get("newsletter_title")
    newsletter_topic = data.get("newsletter_topic")

    if not newsletter_title and newsletter_topic:
        domain = data.get("domain")
        if domain:
            return f"{domain} 주간 산업동향 뉴스 클리핑"
        if newsletter_topic not in ["최신 산업 동향", "General News"]:
            if " 외 " in newsletter_topic and "개 분야" in newsletter_topic:
                main_topic = newsletter_topic.split(" 외 ")[0]
                return f"{main_topic} 주간 산업 동향 뉴스 클리핑"
            return f"{newsletter_topic} 주간 산업 동향 뉴스 클리핑"
        return newsletter_settings.get("newsletter_title", title_default)

    if not newsletter_title:
        return newsletter_settings.get("newsletter_title", title_default)

    return newsletter_title


def build_common_context(
    *,
    data: Dict[str, Any],
    newsletter_settings: Dict[str, Any],
    generation_date: str,
    generation_timestamp: str,
    newsletter_topic: str | None,
    newsletter_title: str,
    top_articles: List[Dict[str, Any]],
    definitions: List[Dict[str, str]],
    food_for_thought: Any,
) -> Dict[str, Any]:
    """Build the common context shared by every compose template."""
    return {
        "generation_date": generation_date,
        "generation_timestamp": generation_timestamp,
        "newsletter_topic": newsletter_topic,
        "newsletter_title": newsletter_title,
        "issue_no": data.get("issue_no"),
        "top_articles": top_articles,
        "definitions": definitions,
        "food_for_thought": food_for_thought,
        "copyright_year": generation_date.split("-")[0],
        "publisher_name": data.get(
            "publisher_name",
            data.get(
                "company_name",
                newsletter_settings.get("publisher_name", "Your Company"),
            ),
        ),
        "company_name": data.get(
            "company_name", newsletter_settings.get("company_name", "Your Company")
        ),
        "company_tagline": data.get(
            "company_tagline", newsletter_settings.get("company_tagline")
        ),
        "footer_disclaimer": data.get(
            "footer_disclaimer", newsletter_settings.get("footer_disclaimer")
        ),
        "footer_contact": data.get(
            "footer_contact", newsletter_settings.get("footer_contact")
        ),
        "editor_name": data.get("editor_name", newsletter_settings.get("editor_name")),
        "editor_email": data.get(
            "editor_email", newsletter_settings.get("editor_email")
        ),
        "editor_title": data.get(
            "editor_title", newsletter_settings.get("editor_title", "편집자")
        ),
    }


def load_newsletter_settings(config_file: str = "config.yml") -> Dict[str, Any]:
    """Load newsletter settings, preserving the legacy public-settings fallback."""
    try:
        from newsletter_core.public.settings import get_newsletter_settings

        return get_newsletter_settings()
    except ImportError:
        default_settings = {
            "newsletter_title": "주간 산업 동향 뉴스 클리핑",
            "tagline": "이번 주, 주요 산업 동향을 미리 만나보세요.",
            "publisher_name": "Your Company",
            "company_name": "Your Company",
            "company_tagline": "",
            "editor_name": "",
            "editor_title": "편집자",
            "editor_email": "",
            "footer_disclaimer": "이 뉴스레터는 정보 제공을 목적으로 하며, 내용의 정확성을 보장하지 않습니다.",
            "footer_contact": "",
        }

        try:
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as file_obj:
                    config_data = yaml.safe_load(file_obj)

                newsletter_settings = config_data.get("newsletter_settings", {})
                default_settings.update(newsletter_settings)
        except Exception as exc:
            print(
                f"Warning: Could not load newsletter settings from {config_file}: {exc}"
            )

        return default_settings


def _append_search_keywords(
    context: Dict[str, Any], search_keywords: Any
) -> Dict[str, Any]:
    if not search_keywords:
        return context

    if isinstance(search_keywords, list):
        context["search_keywords"] = ", ".join(search_keywords)
    else:
        context["search_keywords"] = search_keywords
    return context
