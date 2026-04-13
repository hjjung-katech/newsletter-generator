"""
Fallback generation flow when no articles were collected.
"""

import datetime
from typing import Any

from langchain_core.messages import HumanMessage

from newsletter_core.application.generation.compose import compose_newsletter

from .chains_llm_utils import get_llm
from .template_manager import TemplateManager
from .template_paths import get_newsletter_template_dir
from .utils.logger import get_logger

logger = get_logger(__name__)


def _resolve_newsletter_topic(keywords: list[str], domain: str) -> str:
    if domain:
        return domain
    if len(keywords) == 1:
        return keywords[0]

    from .tools import extract_common_theme_from_keywords

    theme = extract_common_theme_from_keywords(keywords)
    if isinstance(theme, str):
        return theme
    return str(theme)


def _extract_message_content(response: Any) -> str:
    if hasattr(response, "content") and response.content:
        return str(response.content).strip()
    return ""


def handle_no_articles_scenario(
    data: dict[str, Any], is_compact: bool
) -> dict[str, Any]:
    del is_compact  # Signature compatibility for existing callers.

    keywords = data.get("keywords", [])
    domain = data.get("domain", "")
    email_compatible = data.get("email_compatible", False)
    template_style = data.get("template_style", "compact")

    if isinstance(keywords, str):
        keywords = [kw.strip() for kw in keywords.split(",") if kw.strip()]
    elif not isinstance(keywords, list):
        keywords = [str(keywords)]

    keyword_list = [str(kw) for kw in keywords]
    newsletter_topic = _resolve_newsletter_topic(keyword_list, str(domain))

    current_date = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    current_time = datetime.datetime.now().strftime("%H:%M")
    template_manager = TemplateManager()

    intro_fallback = (
        f"이번 주는 {newsletter_topic} 분야의 특별한 뉴스 수집이 어려웠지만, "
        "해당 분야의 지속적인 발전과 전략적 중요성을 고려할 때 "
        "지속적인 관심과 모니터링이 필요합니다."
    )
    thought_fallback = f"{newsletter_topic} 분야의 빠른 변화에 대응하기 위해서는 지속적인 학습과 혁신이 필요합니다."
    thought_extended_fallback = (
        f"{newsletter_topic} 분야의 빠른 변화에 대응하기 위해서는 지속적인 학습과 혁신이 필요합니다. "
        "향후 동향을 예의주시하며 우리 조직의 전략과 방향성을 점검해보시기 바랍니다."
    )

    try:
        llm = get_llm(temperature=0.4)

        intro_prompt = f"""다음 키워드 주제에 대한 뉴스레터 소개 문구를 작성해주세요:

주제: {newsletter_topic}
키워드: {", ".join(keyword_list)}

R&D 전략기획단 전문위원들을 대상으로, 해당 분야의 중요성과 최근 동향에 대한 통찰을 제공하는 소개 문구를 작성해주세요.

요구사항:
- 이번 주 특정 뉴스에 의존하지 않고, 해당 분야의 일반적인 중요성과 트렌드를 강조
- 전략적 관점에서 해당 분야가 왜 중요한지 설명
- 정중한 존댓말 사용
- 1-2문장으로 간결하게

소개 문구만 반환해주세요 (다른 설명 없이):"""

        intro_response = llm.invoke([HumanMessage(content=intro_prompt)])
        introduction_message = _extract_message_content(intro_response)
        if not introduction_message:
            logger.warning(
                "LLM 소개 메시지 응답에서 유효한 content를 찾을 수 없음: %s",
                intro_response,
            )
            introduction_message = intro_fallback

        thought_prompt = f"""다음 주제에 대한 "생각해 볼 거리" 메시지를 생성해주세요:

주제: {newsletter_topic}
키워드: {", ".join(keyword_list)}

R&D 전략기획단 전문위원들을 대상으로, 해당 주제 분야의 전략적 중요성과 미래 방향성에 대한 생각해볼 거리를 제공해주세요.

요구사항:
- 구체적이고 실용적인 내용
- 전략적 사고를 유도하는 질문이나 제안
- 해당 분야의 미래 전망이나 도전 과제 언급
- 정중한 존댓말 사용
- 1-2문장으로 간결하게

메시지만 반환해주세요 (다른 설명 없이):"""

        thought_response = llm.invoke([HumanMessage(content=thought_prompt)])
        food_for_thought_message = _extract_message_content(thought_response)
        if not food_for_thought_message:
            logger.warning(
                "LLM 생각해볼거리 응답에서 유효한 content를 찾을 수 없음: %s",
                thought_response,
            )
            food_for_thought_message = thought_fallback

    except Exception as e:
        logger.warning("LLM 기반 콘텐츠 생성 실패: %s", e)
        introduction_message = intro_fallback
        food_for_thought_message = thought_extended_fallback

    result_data: dict[str, Any] = {
        "top_articles": [],
        "grouped_sections": [],
        "definitions": [
            {
                "term": newsletter_topic,
                "explanation": (
                    f"{newsletter_topic} 분야는 빠르게 발전하고 있는 핵심 기술 영역으로, "
                    "지속적인 연구개발과 전략적 투자가 필요한 분야입니다."
                ),
            }
        ],
        "newsletter_topic": newsletter_topic,
        "generation_date": current_date,
        "generation_time": current_time,
        "search_keywords": ", ".join(keyword_list),
        "food_for_thought": {"message": food_for_thought_message},
        "recipient_greeting": "안녕하세요,",
        "introduction_message": introduction_message,
        "closing_message": "다음 주에 더 유익한 정보로 찾아뵙겠습니다. 감사합니다.",
        "editor_signature": "편집자 드림",
        "company_name": template_manager.get("company.name", "산업통상자원 R&D 전략기획단"),
        "company_logo_url": template_manager.get(
            "company.logo_url", "/static/logo.png"
        ),
        "company_website": template_manager.get(
            "company.website", "https://example.com"
        ),
        "copyright_year": template_manager.get(
            "company.copyright_year",
            datetime.date.today().strftime("%Y"),
        ),
        "company_tagline": template_manager.get("company.tagline", "최신 기술 동향을 한눈에"),
        "footer_contact": template_manager.get(
            "footer.contact_info",
            "문의사항: hjjung2@osp.re.kr",
        ),
        "editor_name": template_manager.get("editor.name", "Google Gemini"),
        "editor_email": template_manager.get("editor.email", "hjjung2@osp.re.kr"),
        "editor_title": template_manager.get("editor.title", "편집자"),
        "footer_disclaimer": template_manager.get(
            "footer.disclaimer",
            "이 뉴스레터는 정보 제공을 목적으로 하며, 내용의 정확성을 보장하지 않습니다.",
        ),
        "email_compatible": email_compatible,
        "template_style": template_style,
    }

    logger.info("키워드 기반 뉴스레터 생성: %s", newsletter_topic)
    template_dir = get_newsletter_template_dir()

    if email_compatible:
        logger.info("Email-compatible 템플릿 사용")
        html_content = compose_newsletter(result_data, template_dir, "email_compatible")
    else:
        logger.info("%s 템플릿 사용", template_style)
        html_content = compose_newsletter(result_data, template_dir, template_style)

    logger.success("키워드 기반 뉴스레터 생성 완료!")

    return {
        "html": html_content,
        "structured_data": result_data,
        "sections": [],
        "mode": template_style,
    }
