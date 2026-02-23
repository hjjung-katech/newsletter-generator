"""Categorization chain builder for newsletter generation."""

# mypy: disable-error-code=no-untyped-def

import json

from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

from .chains_llm_utils import format_articles, get_llm
from .utils.logger import get_logger

logger = get_logger(__name__)


def build_categorization_chain(categorization_prompt: str, is_compact: bool = False):
    llm = get_llm(temperature=0.2)

    # compact 버전용 간소화된 프롬프트
    compact_prompt = """당신은 뉴스들을 간결하게 분류하는 전문 편집자입니다.

다음 뉴스 기사들을 분석하여 2-3개의 주요 카테고리로 분류해주세요:
{formatted_articles}

출력 형식은 다음과 같은 JSON 형식으로 작성해주세요:
{{
  "categories": [
    {{
      "title": "카테고리 제목",
      "article_indices": [1, 2, 5]
    }},
    {{
      "title": "카테고리 제목 2",
      "article_indices": [3, 4, 6]
    }}
  ]
}}

각 카테고리 제목은 독자가 어떤 내용인지 한눈에 알 수 있도록 명확하고 구체적으로 작성해주세요."""

    # 메시지 생성 함수
    def create_messages(data):
        try:
            # 문자열 직접 포맷팅 대신 미리 처리된 값으로 포맷팅
            keywords = data.get("keywords", "")
            formatted_articles = format_articles(data)

            # 중첩된 중괄호 이스케이프 처리
            formatted_articles = formatted_articles.replace("{", "{{").replace(
                "}", "}}"
            )

            # compact 버전인지에 따라 프롬프트 선택
            if is_compact:
                prompt = compact_prompt.format(formatted_articles=formatted_articles)
            else:
                # 포맷팅 진행
                prompt = categorization_prompt.format(
                    keywords=keywords,
                    formatted_articles=formatted_articles,
                )

            # 메시지를 HumanMessage로 변환
            # (Gemini는 시스템 메시지 지원이 불안정함)
            return [HumanMessage(content=prompt)]
        except Exception as e:
            logger.error(f"카테고리 메시지 생성 중 오류: {e}")
            import traceback

            traceback.print_exc()
            raise

    # 체인 구성
    chain = RunnableLambda(create_messages) | llm | StrOutputParser()

    # JSON 파싱 함수
    def parse_json_response(text):
        try:
            # JSON 부분만 추출
            import re

            json_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                # compact 버전에서는 중괄호로 감싸진 JSON도 찾기
                if is_compact:
                    json_match = re.search(r"\{.*\}", text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group()
                    else:
                        json_str = text.strip()
                else:
                    json_str = text.strip()

            # JSON 파싱
            result = json.loads(json_str)
            logger.info(
                f"카테고리 분류 결과: " f"{json.dumps(result, ensure_ascii=False, indent=2)}"
            )
            return result
        except Exception as e:
            logger.error(f"JSON 파싱 오류: {e}")
            logger.error(f"원본 텍스트: {text}")
            # 기본 구조 반환
            if is_compact:
                return {
                    "categories": [
                        {"title": "주요 동향", "article_indices": list(range(1, 11))}
                    ]
                }
            else:
                return {
                    "categories": [{"title": "기타", "article_indices": [1, 2, 3, 4, 5]}]
                }

    return chain | RunnableLambda(parse_json_response)
