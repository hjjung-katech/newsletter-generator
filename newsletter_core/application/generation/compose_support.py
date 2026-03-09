"""Support helpers re-exported by the compose orchestrator."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from newsletter.utils.logger import get_logger

from .compose_sections import (
    extract_key_definitions_for_compact,
    extract_top_articles_from_sections,
    prepare_grouped_sections_for_compact,
    prepare_top_articles_for_compact,
)

logger = get_logger()


def save_newsletter_with_config(
    data: Dict[str, Any], config_data: Dict[str, Any], output_path: str
) -> None:
    """Save newsletter data with embedded test configuration."""
    data_to_save = data.copy()
    data_to_save["_test_config"] = config_data
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file_handle:
        json.dump(data_to_save, file_handle, indent=2, ensure_ascii=False)

    print(f"Saved newsletter data with embedded config to {output_path}")


def process_compact_newsletter_data(newsletter_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert newsletter data into the compact template input shape."""
    logger.debug(
        f"process_compact_newsletter_data 입력 키들: {list(newsletter_data.keys())}"
    )

    compact_data = {
        "newsletter_title": newsletter_data.get("newsletter_topic", "주간 산업 동향 브리프"),
        "tagline": "이번 주, 주요 산업 동향을 미리 만나보세요.",
        "company_name": newsletter_data.get("company_name", "Your Company"),
        "generation_date": newsletter_data.get("generation_date"),
        "issue_no": newsletter_data.get("issue_no"),
    }

    top_articles = newsletter_data.get("top_articles", [])
    logger.debug(f"상위 기사를 찾았습니다: {len(top_articles)}개")

    if not top_articles and "sections" in newsletter_data:
        logger.debug("상위 기사가 없어 섹션에서 추출합니다")
        top_articles = extract_top_articles_from_sections(newsletter_data["sections"])

    compact_data["top_articles"] = prepare_top_articles_for_compact(top_articles[:3])

    if "grouped_sections" in newsletter_data:
        logger.debug(f"기존 그룹화된 섹션을 사용합니다: {len(newsletter_data['grouped_sections'])}개")
        compact_data["grouped_sections"] = newsletter_data["grouped_sections"]
    else:
        logger.debug("섹션에서 그룹화된 섹션을 생성합니다")
        compact_data["grouped_sections"] = prepare_grouped_sections_for_compact(
            newsletter_data.get("sections", []),
            top_articles[:3],
        )

    if "definitions" in newsletter_data:
        logger.debug(f"기존 정의를 사용합니다: {len(newsletter_data['definitions'])}개")
        compact_data["definitions"] = newsletter_data["definitions"]
    else:
        logger.debug("섹션에서 정의를 생성합니다")
        compact_data["definitions"] = extract_key_definitions_for_compact(
            newsletter_data.get("sections", [])
        )

    food_for_thought = newsletter_data.get("food_for_thought")
    if food_for_thought:
        if isinstance(food_for_thought, dict):
            compact_data["food_for_thought"] = food_for_thought
        else:
            compact_data["food_for_thought"] = {"message": str(food_for_thought)}

    return compact_data
