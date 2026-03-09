"""Template rendering helpers for compose."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Callable, Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from newsletter.utils.logger import get_logger

from .compose_context import build_render_context

logger = get_logger()


def render_newsletter_template(
    data: Dict[str, Any],
    template_dir: str,
    config: Dict[str, Any],
    top_articles: List[Dict[str, Any]],
    grouped_sections: List[Dict[str, Any]],
    definitions: List[Dict[str, str]],
    food_for_thought: Any,
) -> str:
    """Render the configured newsletter template."""
    env = _build_environment(template_dir)
    template_name = config["template_name"]
    logger.debug(f"템플릿 로딩 중: {template_name}")
    template = env.get_template(template_name)
    logger.debug(f"템플릿 로딩 완료: {template_name}")
    context = build_render_context(
        data=data,
        config=config,
        top_articles=top_articles,
        grouped_sections=grouped_sections,
        definitions=definitions,
        food_for_thought=food_for_thought,
    )
    return template.render(context)


def render_detailed_wrapper(
    data: Any,
    template_dir: str,
    template_name: str,
    compose_newsletter_fn: Callable[[Any, str, str], str],
) -> str:
    """Render the legacy detailed wrapper while preserving custom-template behavior."""
    if template_name and template_name != "newsletter_template.html":
        template = _build_environment(template_dir).get_template(template_name)
        return template.render(_build_custom_detailed_context(data))

    return compose_newsletter_fn(data, template_dir, "detailed")


def render_compact_wrapper(
    data: Any,
    template_dir: str,
    template_name: str,
    compose_newsletter_fn: Callable[[Any, str, str], str],
) -> str:
    """Render the legacy compact wrapper while preserving custom-template behavior."""
    if template_name != "newsletter_template_compact.html":
        template = _build_environment(template_dir).get_template(template_name)
        return template.render(
            {
                "newsletter_title": data.get("newsletter_topic", "주간 산업 동향 뉴스 클리핑"),
                "tagline": "이번 주, 주요 산업 동향을 미리 만나보세요.",
                "generation_date": data.get(
                    "generation_date", datetime.now().strftime("%Y-%m-%d")
                ),
                "definitions": data.get("definitions", []),
            }
        )

    return compose_newsletter_fn(data, template_dir, "compact")


def _build_environment(template_dir: str) -> Environment:
    return Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )


def _build_custom_detailed_context(data: Dict[str, Any]) -> Dict[str, Any]:
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")
    context = {
        "newsletter_topic": data.get("newsletter_topic", "주간 산업 동향"),
        "newsletter_title": data.get(
            "newsletter_title",
            data.get("newsletter_topic", "주간 산업 동향 뉴스 클리핑"),
        ),
        "generation_date": data.get(
            "generation_date", os.environ.get("GENERATION_DATE", current_date)
        ),
        "generation_timestamp": data.get(
            "generation_timestamp", os.environ.get("GENERATION_TIMESTAMP", current_time)
        ),
        "sections": data.get("sections", []),
        "recipient_greeting": data.get("recipient_greeting"),
        "introduction_message": data.get("introduction_message"),
        "closing_message": data.get("closing_message"),
        "editor_signature": data.get("editor_signature"),
        "company_name": data.get("company_name"),
        "top_articles": data.get("top_articles", []),
        "food_for_thought": data.get("food_for_thought"),
        "search_keywords": data.get("search_keywords"),
    }

    if context["search_keywords"] and isinstance(context["search_keywords"], list):
        context["search_keywords"] = ", ".join(context["search_keywords"])

    return context
