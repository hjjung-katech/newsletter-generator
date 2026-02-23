"""
Newsletter Generator - LangChain Chains
이 모듈은 뉴스레터 생성을 위한 LangChain 체인을 정의합니다.
"""

from langchain_core.runnables import RunnableLambda

from . import chains_prompts
from .chains_categorization import build_categorization_chain
from .chains_compact_flow import build_compact_newsletter_result
from .chains_composition import create_composition_chain
from .chains_llm_utils import get_llm as _get_llm
from .chains_no_articles import handle_no_articles_scenario
from .chains_prompts import CATEGORIZATION_PROMPT, SUMMARIZATION_PROMPT
from .chains_rendering import create_rendering_chain
from .chains_summarization import build_summarization_chain
from .utils.logger import get_logger

# 로거 초기화
logger = get_logger(__name__)

# 하위 호환성 re-export
COMPOSITION_PROMPT = chains_prompts.COMPOSITION_PROMPT
HTML_TEMPLATE = chains_prompts.HTML_TEMPLATE
SYSTEM_PROMPT = chains_prompts.SYSTEM_PROMPT
load_html_template = chains_prompts.load_html_template
get_llm = _get_llm


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
                return build_compact_newsletter_result(data, sections_data)

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
