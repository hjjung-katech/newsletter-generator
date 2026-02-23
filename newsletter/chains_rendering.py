"""
Rendering chain construction helpers.
"""

import datetime
import os
from typing import Any

from langchain_core.runnables import RunnableLambda

from newsletter.article_filter import select_top_articles

from .chains_prompts import HTML_TEMPLATE
from .compose import compose_newsletter
from .template_manager import TemplateManager
from .utils.logger import get_logger

logger = get_logger(__name__)


def _get_common_theme_from_keywords(keywords: Any) -> str:
    callbacks: list[Any] = []
    if os.environ.get("ENABLE_COST_TRACKING") or os.environ.get("LANGCHAIN_TRACING_V2"):
        try:
            from .cost_tracking import get_tracking_callbacks, register_recent_callbacks

            callbacks = get_tracking_callbacks()
            register_recent_callbacks(callbacks)
        except Exception as e:
            logger.warning(
                "Cost tracking setup error: %s. Continuing without tracking.",
                e,
            )

    from . import tools

    return tools.extract_common_theme_from_keywords(keywords, callbacks=callbacks)


def _render_with_template(
    data: dict[str, Any],
    template_manager: TemplateManager,
) -> tuple[str, dict[str, Any]]:
    combined_data = {**data["composition"], **data["sections_data"]}

    if "generation_date" not in combined_data:
        combined_data["generation_date"] = datetime.date.today().strftime("%Y-%m-%d")

    if "keywords" in data and data["keywords"]:
        keywords = data["keywords"]
        domain = data.get("domain", "")

        if isinstance(keywords, list):
            combined_data["search_keywords"] = ", ".join(keywords)
        else:
            combined_data["search_keywords"] = keywords

        if domain:
            combined_data["newsletter_topic"] = domain
        elif isinstance(keywords, list) and len(keywords) == 1:
            combined_data["newsletter_topic"] = keywords[0]
        elif isinstance(keywords, list) and len(keywords) > 1:
            combined_data["newsletter_topic"] = _get_common_theme_from_keywords(
                keywords
            )
        elif isinstance(keywords, str) and "," in keywords:
            combined_data["newsletter_topic"] = _get_common_theme_from_keywords(
                keywords
            )
        else:
            combined_data["newsletter_topic"] = keywords

    combined_data["company_name"] = template_manager.get("company.name", "R&D 기획단")
    combined_data["footer_disclaimer"] = template_manager.get(
        "footer.disclaimer",
        "이 뉴스레터는 정보 제공용으로만 사용되며, 투자 권유를 목적으로 하지 않습니다.",
    )
    combined_data["editor_signature"] = template_manager.get(
        "editor.signature",
        "편집자 드림",
    )
    combined_data["copyright_year"] = template_manager.get(
        "company.copyright_year",
        datetime.date.today().strftime("%Y"),
    )
    combined_data["company_tagline"] = template_manager.get("company.tagline", "")
    combined_data["footer_contact"] = template_manager.get("footer.contact_info", "")
    combined_data["editor_name"] = template_manager.get("editor.name", "")
    combined_data["editor_title"] = template_manager.get("editor.title", "")
    combined_data["editor_email"] = template_manager.get("editor.email", "")
    combined_data["title_prefix"] = template_manager.get(
        "header.title_prefix",
        "주간 산업 동향 뉴스 클리핑",
    )
    combined_data["greeting_prefix"] = template_manager.get(
        "header.greeting_prefix",
        "안녕하십니까, ",
    )
    combined_data["audience_organization"] = template_manager.get(
        "audience.organization",
        "",
    )
    combined_data["primary_color"] = template_manager.get(
        "style.primary_color", "#3498db"
    )
    combined_data["secondary_color"] = template_manager.get(
        "style.secondary_color",
        "#2c3e50",
    )
    combined_data["font_family"] = template_manager.get(
        "style.font_family",
        "Malgun Gothic, sans-serif",
    )

    if "recipient_greeting" not in combined_data or not combined_data.get(
        "recipient_greeting"
    ):
        audience_desc = template_manager.get(
            "audience.description",
            "귀하께서 여기 계시다니 영광입니다",
        )
        combined_data["recipient_greeting"] = (
            f"{combined_data.get('greeting_prefix', '안녕하십니까, ')} "
            f"{combined_data.get('company_name')} {audience_desc}."
        )

    if "top_articles" not in combined_data:
        articles_for_top = (
            data.get("ranked_articles") or data.get("processed_articles") or []
        )
        combined_data["top_articles"] = select_top_articles(articles_for_top, top_n=3)

    is_email_compatible = data.get("email_compatible", False)
    template_style = data.get("template_style", "detailed")

    if is_email_compatible:
        combined_data["template_style"] = template_style
        combined_data["email_compatible"] = True
        combined_data["recipient_greeting"] = combined_data.get(
            "recipient_greeting", "안녕하세요,"
        )

        if "introduction_message" not in combined_data:
            newsletter_topic = combined_data.get("newsletter_topic", "")
            if newsletter_topic:
                combined_data[
                    "introduction_message"
                ] = f"이번 주 {newsletter_topic} 분야의 주요 동향과 기술 발전 현황을 정리하여 보내드립니다."
            else:
                combined_data[
                    "introduction_message"
                ] = "이번 주 주요 산업 동향과 기술 발전 현황을 정리하여 보내드립니다."

        combined_data["closing_message"] = combined_data.get(
            "closing_message",
            "다음 주에 더 유익한 정보로 찾아뵙겠습니다. 감사합니다.",
        )
        combined_data["editor_signature"] = combined_data.get(
            "editor_signature",
            "편집자 드림",
        )

        template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
        rendered_html = compose_newsletter(
            combined_data, template_dir, "email_compatible"
        )
    else:
        from jinja2 import Template

        template = Template(HTML_TEMPLATE)
        rendered_html = template.render(**combined_data)

    return rendered_html, combined_data


def create_rendering_chain() -> RunnableLambda:
    template_manager = TemplateManager()

    def render_with_template(data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        return _render_with_template(data, template_manager)

    return RunnableLambda(render_with_template)
