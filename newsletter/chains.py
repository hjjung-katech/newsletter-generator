"""
Newsletter Generator - LangChain Chains
이 모듈은 뉴스레터 생성을 위한 LangChain 체인을 정의합니다.
"""

import datetime
import os

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableLambda

from . import chains_prompts
from .chains_categorization import build_categorization_chain
from .chains_composition import create_composition_chain
from .chains_llm_utils import get_llm
from .chains_prompts import CATEGORIZATION_PROMPT, SUMMARIZATION_PROMPT
from .chains_rendering import create_rendering_chain
from .chains_summarization import build_summarization_chain
from .compose import NewsletterConfig, compose_newsletter, create_grouped_sections
from .template_manager import TemplateManager
from .utils.logger import get_logger

# 로거 초기화
logger = get_logger(__name__)

# 하위 호환성 re-export
COMPOSITION_PROMPT = chains_prompts.COMPOSITION_PROMPT
HTML_TEMPLATE = chains_prompts.HTML_TEMPLATE
SYSTEM_PROMPT = chains_prompts.SYSTEM_PROMPT
load_html_template = chains_prompts.load_html_template


def create_categorization_chain(is_compact=False):
    return build_categorization_chain(
        categorization_prompt=CATEGORIZATION_PROMPT,
        is_compact=is_compact,
    )


# 2. 카테고리별 요약 체인 생성 함수 (compact 옵션 추가)


# 2. 카테고리별 요약 체인 생성 함수 (compact 옵션 추가)
def create_summarization_chain(is_compact=False):
    return build_summarization_chain(
        summarization_prompt=SUMMARIZATION_PROMPT,
        is_compact=is_compact,
    )


# 뉴스가 없을 때의 특별 처리 함수
def handle_no_articles_scenario(data, is_compact):
    """
    뉴스 기사가 수집되지 않았을 때 키워드 기반으로 유용한 뉴스레터를 생성합니다.
    """
    from datetime import datetime

    keywords = data.get("keywords", [])
    domain = data.get("domain", "")
    email_compatible = data.get("email_compatible", False)
    template_style = data.get("template_style", "compact")

    # 키워드 및 주제 처리
    if isinstance(keywords, str):
        keywords = [kw.strip() for kw in keywords.split(",") if kw.strip()]

    # 주제 결정
    if domain:
        newsletter_topic = domain
    elif len(keywords) == 1:
        newsletter_topic = keywords[0]
    else:
        from .tools import extract_common_theme_from_keywords

        newsletter_topic = extract_common_theme_from_keywords(keywords)

    # 현재 날짜 및 시간 정보
    current_date = datetime.now().strftime("%Y년 %m월 %d일")
    current_time = datetime.now().strftime("%H:%M")

    # 템플릿 매니저로부터 메타데이터 가져오기
    template_manager = TemplateManager()

    # LLM을 사용하여 키워드 기반 유용한 내용 생성
    try:
        llm = get_llm(temperature=0.4)

        # 키워드 기반 소개 메시지 생성
        intro_prompt = f"""다음 키워드 주제에 대한 뉴스레터 소개 문구를 작성해주세요:

주제: {newsletter_topic}
키워드: {", ".join(keywords) if isinstance(keywords, list) else keywords}

R&D 전략기획단 전문위원들을 대상으로, 해당 분야의 중요성과 최근 동향에 대한 통찰을 제공하는 소개 문구를 작성해주세요.

요구사항:
- 이번 주 특정 뉴스에 의존하지 않고, 해당 분야의 일반적인 중요성과 트렌드를 강조
- 전략적 관점에서 해당 분야가 왜 중요한지 설명
- 정중한 존댓말 사용
- 1-2문장으로 간결하게

소개 문구만 반환해주세요 (다른 설명 없이):"""

        messages = [HumanMessage(content=intro_prompt)]
        intro_response = llm.invoke(messages)

        # 안전한 응답 처리
        if hasattr(intro_response, "content") and intro_response.content:
            introduction_message = str(intro_response.content).strip()
        else:
            logger.warning(f"LLM 소개 메시지 응답에서 유효한 content를 찾을 수 없음: {intro_response}")
            introduction_message = f"이번 주는 {newsletter_topic} 분야의 특별한 뉴스 수집이 어려웠지만, 해당 분야의 지속적인 발전과 전략적 중요성을 고려할 때 지속적인 관심과 모니터링이 필요합니다."

        # 키워드 기반 생각해 볼 거리 생성
        thought_prompt = f"""다음 주제에 대한 "생각해 볼 거리" 메시지를 생성해주세요:

주제: {newsletter_topic}
키워드: {", ".join(keywords) if isinstance(keywords, list) else keywords}

R&D 전략기획단 전문위원들을 대상으로, 해당 주제 분야의 전략적 중요성과 미래 방향성에 대한 생각해볼 거리를 제공해주세요.

요구사항:
- 구체적이고 실용적인 내용
- 전략적 사고를 유도하는 질문이나 제안
- 해당 분야의 미래 전망이나 도전 과제 언급
- 정중한 존댓말 사용
- 1-2문장으로 간결하게

메시지만 반환해주세요 (다른 설명 없이):"""

        messages = [HumanMessage(content=thought_prompt)]
        thought_response = llm.invoke(messages)

        # 안전한 응답 처리
        if hasattr(thought_response, "content") and thought_response.content:
            food_for_thought_message = str(thought_response.content).strip()
        else:
            logger.warning(f"LLM 생각해볼거리 응답에서 유효한 content를 찾을 수 없음: {thought_response}")
            food_for_thought_message = (
                f"{newsletter_topic} 분야의 빠른 변화에 대응하기 위해서는 지속적인 학습과 혁신이 필요합니다."
            )

    except Exception as e:
        logger.warning(f"LLM 기반 콘텐츠 생성 실패: {e}")
        # 실패 시 기본 메시지 사용
        introduction_message = f"이번 주는 {newsletter_topic} 분야의 특별한 뉴스 수집이 어려웠지만, 해당 분야의 지속적인 발전과 전략적 중요성을 고려할 때 지속적인 관심과 모니터링이 필요합니다."
        food_for_thought_message = f"{newsletter_topic} 분야의 빠른 변화에 대응하기 위해서는 지속적인 학습과 혁신이 필요합니다. 향후 동향을 예의주시하며 우리 조직의 전략과 방향성을 점검해보시기 바랍니다."

    # 최종 데이터 구조 생성
    result_data = {
        "top_articles": [],  # 뉴스가 없으므로 빈 배열
        "grouped_sections": [],  # 뉴스가 없으므로 빈 배열
        "definitions": [
            {
                "term": newsletter_topic,
                "explanation": f"{newsletter_topic} 분야는 빠르게 발전하고 있는 핵심 기술 영역으로, 지속적인 연구개발과 전략적 투자가 필요한 분야입니다.",
            }
        ],
        "newsletter_topic": newsletter_topic,
        "generation_date": current_date,
        "generation_time": current_time,
        "search_keywords": (
            ", ".join(keywords) if isinstance(keywords, list) else str(keywords)
        ),
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
        "email_compatible": email_compatible,
        "template_style": template_style,
    }

    # 템플릿 렌더링
    logger.info(f"키워드 기반 뉴스레터 생성: {newsletter_topic}")
    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")

    if email_compatible:
        logger.info("Email-compatible 템플릿 사용")
        html_content = compose_newsletter(result_data, template_dir, "email_compatible")
    else:
        logger.info(f"{template_style} 템플릿 사용")
        html_content = compose_newsletter(result_data, template_dir, template_style)

    logger.success("키워드 기반 뉴스레터 생성 완료!")

    return {
        "html": html_content,
        "structured_data": result_data,
        "sections": [],  # 뉴스가 없으므로 빈 배열
        "mode": template_style,
    }


# 전체 파이프라인 구성 (compact 옵션 추가)
def get_newsletter_chain(is_compact=False):
    # 1. 분류 체인
    categorization_chain = create_categorization_chain(is_compact=is_compact)

    # 2. 요약 체인
    summarization_chain = create_summarization_chain(is_compact=is_compact)

    # 3. 종합 구성 체인 (detailed만 사용, compact는 건너뜀)
    composition_chain = create_composition_chain() if not is_compact else None

    # 4. 렌더링 체인 (detailed만 사용, compact는 건너뜀)
    rendering_chain = create_rendering_chain() if not is_compact else None

    # 데이터 흐름 관리 함수
    def manage_data_flow(data):
        logger.debug(f"manage_data_flow 호출됨. is_compact={is_compact}")
        try:
            # 데이터 유효성 검증
            if "articles" not in data:
                raise ValueError("입력 데이터에 'articles' 필드가 없습니다.")

            articles = data.get("articles", [])
            keywords = data.get("keywords", [])

            # 빈 기사 배열 처리 - 유용한 뉴스레터를 생성하도록 개선
            if not articles or len(articles) == 0:
                logger.info("뉴스 기사가 수집되지 않았지만, 키워드 기반 유용한 뉴스레터를 생성합니다.")
                return handle_no_articles_scenario(data, is_compact)

            # 1. 분류 단계 실행
            if is_compact:
                logger.step("뉴스 카테고리 분류", "categorization")
            else:
                logger.step("뉴스 카테고리 분류", "categorization")
            categories_data = categorization_chain.invoke(data)

            # 2. 요약 단계 실행
            if is_compact:
                logger.step("카테고리별 요약 생성", "summarization")
            else:
                logger.step("카테고리별 요약 생성", "summarization")
            sections_data = summarization_chain.invoke(
                {"categories_data": categories_data, "articles_data": data}
            )

            if is_compact:
                # Compact 모드 처리
                # compose.py의 extract_and_prepare_top_articles를 사용해 top_articles 추출
                config = NewsletterConfig.get_config("compact")

                # 원본 기사 데이터에서 직접 상위 3개 추출 (점수순 정렬 후)
                articles = data.get("articles", [])
                if articles:
                    # 점수가 있으면 점수순으로 정렬, 없으면 그대로 사용
                    sorted_articles = sorted(
                        articles, key=lambda x: x.get("score", 0), reverse=True
                    )
                    top_3_articles = sorted_articles[:3]

                    # 템플릿용 포맷팅
                    top_articles = []
                    for article in top_3_articles:
                        top_article = {
                            "title": article.get("title", ""),
                            "url": article.get("url", "#"),
                            "snippet": (
                                article.get("snippet", article.get("content", ""))[:200]
                                + "..."
                                if len(
                                    article.get("snippet", article.get("content", ""))
                                )
                                > 200
                                else article.get("snippet", article.get("content", ""))
                            ),
                            "source_and_date": (
                                f"{article.get('source', 'Unknown')} · "
                                f"{article.get('date', 'Unknown date')}"
                            ),
                        }
                        top_articles.append(top_article)
                else:
                    top_articles = []

                grouped_sections = create_grouped_sections(
                    sections_data,
                    top_articles,
                    max_groups=config["max_groups"],
                    max_articles=config["max_articles"],
                )

                # email_compatible 모드인지 확인
                is_email_compatible = data.get("email_compatible", False)

                if is_email_compatible:
                    # email_compatible 모드에서는 grouped_sections에서 definitions 추출
                    definitions = []
                    for group in grouped_sections:
                        group_definitions = group.get("definitions", [])
                        for definition in group_definitions:
                            # 중복 제거
                            if definition not in definitions:
                                definitions.append(definition)
                    # 최대 3개로 제한
                    definitions = definitions[:3]
                    logger.debug(
                        f"이메일 호환 모드: grouped_sections에서 {len(definitions)}개의 정의를 추출했습니다"
                    )
                else:
                    # 일반 compact 모드에서는 전체 definitions를 빈 배열로 설정 (그룹별 definitions만 사용)
                    definitions = []

                # 템플릿 매니저로부터 메타데이터 가져오기
                template_manager = TemplateManager()

                # 키워드 및 주제 처리
                keywords = data.get("keywords", [])
                domain = data.get("domain", "")

                if isinstance(keywords, str):
                    keywords = [kw.strip() for kw in keywords.split(",") if kw.strip()]

                # 주제 결정
                if domain:
                    newsletter_topic = domain
                elif len(keywords) == 1:
                    newsletter_topic = keywords[0]
                else:
                    from .tools import extract_common_theme_from_keywords

                    newsletter_topic = extract_common_theme_from_keywords(keywords)

                # 현재 날짜 및 시간 정보
                current_date = datetime.date.today().strftime("%Y년 %m월 %d일")
                current_time = datetime.datetime.now().strftime("%H:%M")

                # 주제별 동적 "생각해 볼 거리" 생성 (compact용 - LLM 기반)
                def create_food_for_thought_compact(topic, keywords=None):
                    """주제에 따른 동적 생각해 볼 거리 생성 (LLM 기반)"""
                    try:
                        # LLM을 사용하여 동적으로 생성
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

                        messages = [HumanMessage(content=prompt)]
                        response = llm.invoke(messages)

                        # 안전한 응답 처리
                        if hasattr(response, "content") and response.content:
                            message = str(response.content).strip()
                            if message:
                                return message

                        # content가 없거나 빈 경우 기본값 사용
                        logger.warning(f"LLM 응답에서 유효한 content를 찾을 수 없음: {response}")
                        return f"{topic} 분야의 빠른 변화에 대응하기 위해서는 지속적인 학습과 혁신이 필요합니다."

                    except Exception as e:
                        logger.warning(f"LLM 기반 생각해 볼 거리 생성 실패: {e}")
                        # 실패 시에만 기본 메시지 사용
                        return f"{topic} 분야의 빠른 변화에 대응하기 위해서는 지속적인 학습과 혁신이 필요합니다. 이번 주 뉴스들을 통해 업계 동향을 파악하고, 우리 조직의 전략과 방향성을 점검해보시기 바랍니다."

                # 최종 데이터 구조 생성
                result_data = {
                    "top_articles": top_articles[:3],
                    "grouped_sections": grouped_sections,
                    "definitions": definitions,
                    "newsletter_topic": newsletter_topic,
                    "generation_date": current_date,
                    "generation_time": current_time,
                    "search_keywords": (
                        ", ".join(keywords)
                        if isinstance(keywords, list)
                        else str(keywords)
                    ),
                    "food_for_thought": {
                        "message": create_food_for_thought_compact(
                            newsletter_topic, keywords
                        )
                    },
                    # 이메일 템플릿용 기본 메시지들 - 기본값만 설정, LLM 생성 시 덮어쓰기 가능
                    "recipient_greeting": "안녕하세요,",
                    # introduction_message는 LLM이 생성하도록 함
                    "closing_message": "다음 주에 더 유익한 정보로 찾아뵙겠습니다.",
                    "editor_signature": "편집자 드림",
                    "company_name": template_manager.get(
                        "company.name", "산업통상자원 R&D 전략기획단"
                    ),
                    "company_logo_url": template_manager.get(
                        "company.logo_url", "/static/logo.png"
                    ),
                    "company_website": template_manager.get(
                        "company.website", "https://example.com"
                    ),
                    "copyright_year": template_manager.get(
                        "company.copyright_year", datetime.date.today().strftime("%Y")
                    ),
                    "company_tagline": template_manager.get(
                        "company.tagline", "최신 기술 동향을 한눈에"
                    ),
                    "footer_contact": template_manager.get(
                        "footer.contact_info", "문의사항: hjjung2@osp.re.kr"
                    ),
                    "editor_name": template_manager.get("editor.name", "Google Gemini"),
                    "editor_email": template_manager.get(
                        "editor.email", "hjjung2@osp.re.kr"
                    ),
                    "editor_title": template_manager.get("editor.title", "편집자"),
                    "footer_disclaimer": template_manager.get(
                        "footer.disclaimer",
                        "이 뉴스레터는 정보 제공을 목적으로 하며, 내용의 정확성을 보장하지 않습니다.",
                    ),
                }

                # LLM을 사용하여 introduction_message 생성 (compact 모드에서도)
                try:
                    llm = get_llm(temperature=0.3)
                    intro_prompt = f"""다음 정보를 바탕으로 뉴스레터 소개 문구를 작성해주세요:

주제: {newsletter_topic}
키워드: {", ".join(keywords) if isinstance(keywords, list) else keywords}
그룹 수: {len(grouped_sections)}

R&D 전략기획단 전문위원들을 대상으로, 이번 주 뉴스레터의 내용을 간략히 소개하는 문구를 1-2문장으로 작성해주세요.

- 실제 주제와 내용을 반영할 것
- 정중한 존댓말 사용
- 구체적이고 유익한 느낌

소개 문구만 반환해주세요 (다른 설명 없이):"""

                    messages = [HumanMessage(content=intro_prompt)]
                    response = llm.invoke(messages)

                    # 안전한 응답 처리
                    if hasattr(response, "content") and response.content:
                        intro_message = str(response.content).strip()
                        if intro_message:
                            result_data["introduction_message"] = intro_message
                            logger.info(
                                f"[green]LLM이 생성한 introduction_message: {intro_message}[/green]"
                            )
                        else:
                            # 빈 응답인 경우 기본값 사용
                            result_data[
                                "introduction_message"
                            ] = f"이번 주 {newsletter_topic} 분야의 주요 동향과 기술 발전 현황을 정리하여 보내드립니다."
                    else:
                        logger.warning(
                            f"LLM 소개문구 응답에서 유효한 content를 찾을 수 없음: {response}"
                        )
                        result_data[
                            "introduction_message"
                        ] = f"이번 주 {newsletter_topic} 분야의 주요 동향과 기술 발전 현황을 정리하여 보내드립니다."

                except Exception as e:
                    logger.warning(f"LLM 기반 introduction_message 생성 실패: {e}")
                    result_data[
                        "introduction_message"
                    ] = f"이번 주 {newsletter_topic} 분야의 주요 동향과 기술 발전 현황을 정리하여 보내드립니다."

                logger.debug("Compact 최종 데이터 구조:")
                logger.debug(f"  - top_articles: {len(result_data['top_articles'])}개")
                logger.debug(
                    f"  - grouped_sections: {len(result_data['grouped_sections'])}개"
                )
                logger.debug(f"  - definitions: {len(result_data['definitions'])}개")

                # 템플릿 렌더링
                logger.step("HTML 템플릿 렌더링", "rendering")

                # 템플릿 렌더링
                logger.info(
                    f"Composing compact newsletter for topic: {newsletter_topic}"
                )
                template_dir = os.path.join(
                    os.path.dirname(__file__), "..", "templates"
                )

                # email_compatible 정보를 데이터에 추가
                logger.debug(
                    f"원본 데이터 email_compatible: {data.get('email_compatible', 'NOT_FOUND')}"
                )
                result_data["email_compatible"] = data.get("email_compatible", False)
                result_data["template_style"] = data.get("template_style", "compact")
                logger.debug(
                    f"결과 데이터 email_compatible 설정: {result_data['email_compatible']}"
                )

                # email_compatible 처리를 위해 통합된 compose_newsletter 함수 사용
                is_email_compatible = result_data.get("email_compatible", False)
                logger.debug(f"최종 email_compatible: {is_email_compatible}")

                if is_email_compatible:
                    logger.debug("이메일 호환 템플릿을 사용합니다")
                    html_content = compose_newsletter(
                        result_data, template_dir, "email_compatible"
                    )
                else:
                    logger.debug("간결한 템플릿을 사용합니다")
                    html_content = compose_newsletter(
                        result_data, template_dir, "compact"
                    )

                logger.success("Compact 뉴스레터 생성 완료!")

                # Compact 모드에서 HTML과 구조화된 데이터를 함께 반환
                return {
                    "html": html_content,
                    "structured_data": result_data,
                    "sections": sections_data.get("sections", []),
                    "mode": "compact",
                }

            else:
                # Detailed 모드 처리
                # 3. 종합 구성 단계 실행
                logger.step("종합 구성", "composition")
                composition_data = composition_chain.invoke(
                    {"sections_data": sections_data, "articles_data": data}
                )

                # 4. 렌더링 단계 실행
                logger.step("HTML 템플릿 렌더링", "rendering")

                # 템플릿 렌더링을 위한 데이터 준비
                rendering_data = {
                    "composition": composition_data,
                    "sections_data": sections_data,
                    "keywords": data.get("keywords", ""),
                    "domain": data.get("domain", ""),
                    "ranked_articles": data.get("ranked_articles", []),
                    "processed_articles": data.get("processed_articles", []),
                    "email_compatible": data.get("email_compatible", False),
                    "template_style": data.get("template_style", "detailed"),
                }

                # 렌더링 체인 호출
                html_content, structured_data = rendering_chain.invoke(rendering_data)

                logger.success("Detailed 뉴스레터 생성 완료!")

                # Detailed 모드에서 HTML과 구조화된 데이터를 함께 반환
                return {
                    "html": html_content,
                    "structured_data": structured_data,
                    "sections": sections_data.get("sections", []),
                    "mode": "detailed",
                }

        except Exception as e:
            logger.error(f"데이터 흐름 처리 중 오류 발생: {e}")
            import traceback

            traceback.print_exc()
            raise

    # 최종 체인 반환
    return RunnableLambda(manage_data_flow)


# 기존 summarization_chain 유지 (하위 호환성)
def get_summarization_chain(callbacks=None):
    """callbacks 매개변수를 지원하는 요약 체인 반환 함수"""

    # get_newsletter_chain()은 RunnableLambda(manage_data_flow)를 반환하고,
    # manage_data_flow는 이제 final_html만 반환합니다.
    newsletter_chain_runnable = get_newsletter_chain(is_compact=False)

    # 따라서 get_summarization_chain도 HTML 문자열을 직접 반환하게 됩니다.
    print("이 함수는 곧 사라질 예정입니다. get_newsletter_chain()을 사용하세요.")
    return newsletter_chain_runnable
