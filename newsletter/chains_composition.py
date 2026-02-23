"""
Composition chain construction helpers.
"""

import datetime
import json
import re
from typing import Any, Mapping

from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

from .chains_llm_utils import get_llm
from .chains_prompts import COMPOSITION_PROMPT
from .utils.logger import get_logger

logger = get_logger(__name__)


def _create_composition_prompt(data: Mapping[str, Any]) -> list[HumanMessage]:
    current_date = datetime.date.today().strftime("%Y-%m-%d")
    sections_data = json.dumps(data.get("sections", []), ensure_ascii=False, indent=2)

    # JSON 데이터의 중괄호 이스케이프 처리
    sections_data = sections_data.replace("{", "{{").replace("}", "}}")
    keywords = data.get("keywords", "")

    prompt_content = COMPOSITION_PROMPT.format(
        keywords=keywords,
        category_summaries=sections_data,
        current_date=current_date,
    )
    return [HumanMessage(content=prompt_content)]


def _fallback_composition() -> dict[str, Any]:
    return {
        "newsletter_topic": "최신 산업 동향",
        "generation_date": datetime.date.today().strftime("%Y-%m-%d"),
        "recipient_greeting": "안녕하세요, 독자 여러분",
        "introduction_message": "이번 뉴스레터에서는 주요 산업 동향을 살펴봅니다.",
        "food_for_thought": {"message": "산업의 변화에 어떻게 대응해 나갈지 생각해 보시기 바랍니다."},
        "closing_message": "다음 뉴스레터에서 다시 만나뵙겠습니다.",
        "editor_signature": "편집자 드림",
        "company_name": "Tech Insights",
    }


def _parse_composition_json(text: str) -> dict[str, Any]:
    try:
        json_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            json_str = text.strip()
        parsed = json.loads(json_str)
        if isinstance(parsed, dict):
            return parsed
        return _fallback_composition()
    except Exception as e:
        logger.error("종합 구성 JSON 파싱 오류: %s", e)
        logger.error("원본 텍스트: %s", text)
        return _fallback_composition()


def create_composition_chain() -> Any:
    llm = get_llm(temperature=0.4)
    return (
        RunnableLambda(_create_composition_prompt)
        | llm
        | StrOutputParser()
        | RunnableLambda(_parse_composition_json)
    )
