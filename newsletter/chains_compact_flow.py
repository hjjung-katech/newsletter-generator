"""
Compact-mode newsletter flow helpers.
"""

import datetime
from typing import Any

from langchain_core.messages import HumanMessage

from .chains_llm_utils import get_llm
from .compose import NewsletterConfig, compose_newsletter, create_grouped_sections
from .template_manager import TemplateManager
from .template_paths import get_newsletter_template_dir
from .utils.logger import get_logger

logger = get_logger(__name__)


def _normalize_keywords(keywords: Any) -> list[str]:
    if isinstance(keywords, str):
        return [kw.strip() for kw in keywords.split(",") if kw.strip()]
    if isinstance(keywords, list):
        return [str(kw).strip() for kw in keywords if str(kw).strip()]
    if keywords:
        return [str(keywords).strip()]
    return []


def _determine_newsletter_topic(keywords: list[str], domain: str) -> str:
    if domain:
        return domain
    if len(keywords) == 1:
        return keywords[0]
    from .tools import extract_common_theme_from_keywords

    topic = extract_common_theme_from_keywords(keywords)
    if isinstance(topic, str):
        return topic
    return str(topic)


def _create_food_for_thought_compact(topic: str, keywords: list[str]) -> str:
    try:
        llm = get_llm(temperature=0.4)
        keywords_str = ", ".join(keywords) if keywords else topic
        prompt = f"""다음 주제에 대한 "생각해 볼 거리" 메시지를 생성해주세요:

주제: {topic}
키워드: {keywords_str}

R&D 전략기획단 전문위원들을 대상으로, 해당 주제 분야의 빠른 변화에 대응하기 위한 전략적 관점의 생각해볼 거리를 1-2문장으로 작성해주세요.

- 구체적이고 실용적인 내용
- 전략적 사고를 유도하는 질문이나 제안
- 정중한 존댓말 사용

메시지만 반환해주세요 (다른 설명 없이):"""
        response = llm.invoke([HumanMessage(content=prompt)])
        if hasattr(response, "content") and response.content:
            message = str(response.content).strip()
            if message:
                return message
        logger.warning("LLM 응답에서 유효한 content를 찾을 수 없음: %s", response)
        return f"{topic} 분야의 빠른 변화에 대응하기 위해서는 지속적인 학습과 혁신이 필요합니다."
    except Exception as e:
        logger.warning("LLM 기반 생각해 볼 거리 생성 실패: %s", e)
        return (
            f"{topic} 분야의 빠른 변화에 대응하기 위해서는 지속적인 학습과 혁신이 필요합니다. "
            "이번 주 뉴스들을 통해 업계 동향을 파악하고, "
            "우리 조직의 전략과 방향성을 점검해보시기 바랍니다."
        )


def _build_top_articles(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not articles:
        return []

    sorted_articles = sorted(articles, key=lambda x: x.get("score", 0), reverse=True)
    top_3_articles = sorted_articles[:3]

    top_articles: list[dict[str, Any]] = []
    for article in top_3_articles:
        snippet = article.get("snippet", article.get("content", ""))
        if len(snippet) > 200:
            snippet = snippet[:200] + "..."
        top_articles.append(
            {
                "title": article.get("title", ""),
                "url": article.get("url", "#"),
                "snippet": snippet,
                "source_and_date": (
                    f"{article.get('source', 'Unknown')} · "
                    f"{article.get('date', 'Unknown date')}"
                ),
            }
        )
    return top_articles


def _extract_email_definitions(
    grouped_sections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    definitions: list[dict[str, Any]] = []
    for group in grouped_sections:
        for definition in group.get("definitions", []):
            if definition not in definitions:
                definitions.append(definition)
    return definitions[:3]


def _apply_intro_message(
    result_data: dict[str, Any],
    newsletter_topic: str,
    keywords: list[str],
    grouped_sections: list[dict[str, Any]],
) -> None:
    try:
        llm = get_llm(temperature=0.3)
        intro_prompt = f"""다음 정보를 바탕으로 뉴스레터 소개 문구를 작성해주세요:

주제: {newsletter_topic}
키워드: {", ".join(keywords)}
그룹 수: {len(grouped_sections)}

R&D 전략기획단 전문위원들을 대상으로, 이번 주 뉴스레터의 내용을 간략히 소개하는 문구를 1-2문장으로 작성해주세요.

- 실제 주제와 내용을 반영할 것
- 정중한 존댓말 사용
- 구체적이고 유익한 느낌

소개 문구만 반환해주세요 (다른 설명 없이):"""

        response = llm.invoke([HumanMessage(content=intro_prompt)])
        if hasattr(response, "content") and response.content:
            intro_message = str(response.content).strip()
            if intro_message:
                result_data["introduction_message"] = intro_message
                logger.info(
                    "[green]LLM이 생성한 introduction_message: %s[/green]",
                    intro_message,
                )
                return
        logger.warning("LLM 소개문구 응답에서 유효한 content를 찾을 수 없음: %s", response)
    except Exception as e:
        logger.warning("LLM 기반 introduction_message 생성 실패: %s", e)

    result_data[
        "introduction_message"
    ] = f"이번 주 {newsletter_topic} 분야의 주요 동향과 기술 발전 현황을 정리하여 보내드립니다."


def build_compact_newsletter_result(
    data: dict[str, Any], sections_data: dict[str, Any]
) -> dict[str, Any]:
    config = NewsletterConfig.get_config("compact")
    raw_articles = data.get("articles", [])
    articles = raw_articles if isinstance(raw_articles, list) else []
    top_articles = _build_top_articles(articles)

    grouped_sections = create_grouped_sections(
        sections_data,
        top_articles,
        max_groups=config["max_groups"],
        max_articles=config["max_articles"],
    )

    is_email_compatible = data.get("email_compatible", False)
    definitions = (
        _extract_email_definitions(grouped_sections) if is_email_compatible else []
    )
    if is_email_compatible:
        logger.debug(
            "이메일 호환 모드: grouped_sections에서 %s개의 정의를 추출했습니다",
            len(definitions),
        )

    template_manager = TemplateManager()
    keywords = _normalize_keywords(data.get("keywords", []))
    domain = str(data.get("domain", ""))
    newsletter_topic = _determine_newsletter_topic(keywords, domain)
    current_date = datetime.date.today().strftime("%Y년 %m월 %d일")
    current_time = datetime.datetime.now().strftime("%H:%M")

    result_data: dict[str, Any] = {
        "top_articles": top_articles[:3],
        "grouped_sections": grouped_sections,
        "definitions": definitions,
        "newsletter_topic": newsletter_topic,
        "generation_date": current_date,
        "generation_time": current_time,
        "search_keywords": ", ".join(keywords),
        "food_for_thought": {
            "message": _create_food_for_thought_compact(newsletter_topic, keywords)
        },
        "recipient_greeting": "안녕하세요,",
        "closing_message": "다음 주에 더 유익한 정보로 찾아뵙겠습니다.",
        "editor_signature": "편집자 드림",
        "company_name": template_manager.get("company.name", "산업통상자원 R&D 전략기획단"),
        "company_logo_url": template_manager.get(
            "company.logo_url", "/static/logo.png"
        ),
        "company_website": template_manager.get(
            "company.website", "https://example.com"
        ),
        "copyright_year": template_manager.get(
            "company.copyright_year", datetime.date.today().strftime("%Y")
        ),
        "company_tagline": template_manager.get("company.tagline", "최신 기술 동향을 한눈에"),
        "footer_contact": template_manager.get(
            "footer.contact_info", "문의사항: hjjung2@osp.re.kr"
        ),
        "editor_name": template_manager.get("editor.name", "Google Gemini"),
        "editor_email": template_manager.get("editor.email", "hjjung2@osp.re.kr"),
        "editor_title": template_manager.get("editor.title", "편집자"),
        "footer_disclaimer": template_manager.get(
            "footer.disclaimer",
            "이 뉴스레터는 정보 제공을 목적으로 하며, 내용의 정확성을 보장하지 않습니다.",
        ),
    }

    _apply_intro_message(result_data, newsletter_topic, keywords, grouped_sections)

    logger.debug("Compact 최종 데이터 구조:")
    logger.debug("  - top_articles: %s개", len(result_data["top_articles"]))
    logger.debug("  - grouped_sections: %s개", len(result_data["grouped_sections"]))
    logger.debug("  - definitions: %s개", len(result_data["definitions"]))

    logger.step("HTML 템플릿 렌더링", "rendering")
    logger.info("Composing compact newsletter for topic: %s", newsletter_topic)

    template_dir = get_newsletter_template_dir()
    result_data["email_compatible"] = data.get("email_compatible", False)
    result_data["template_style"] = data.get("template_style", "compact")

    if result_data.get("email_compatible", False):
        logger.debug("이메일 호환 템플릿을 사용합니다")
        html_content = compose_newsletter(result_data, template_dir, "email_compatible")
    else:
        logger.debug("간결한 템플릿을 사용합니다")
        html_content = compose_newsletter(result_data, template_dir, "compact")

    logger.success("Compact 뉴스레터 생성 완료!")
    return {
        "html": html_content,
        "structured_data": result_data,
        "sections": sections_data.get("sections", []),
        "mode": "compact",
    }
