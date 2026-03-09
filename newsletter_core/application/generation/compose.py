# Placeholder for newsletter composition logic
from typing import Any

from newsletter.date_utils import extract_source_and_date, format_date_for_display
from newsletter.utils.logger import get_logger

from .compose_inputs import (
    NewsletterConfig,
    normalize_compose_input,
    resolve_style_config,
)
from .compose_renderer import (
    render_compact_wrapper,
    render_detailed_wrapper,
    render_newsletter_template,
)
from .compose_sections import (
    create_grouped_sections,
    extract_and_prepare_top_articles,
    extract_definitions,
    extract_food_for_thought,
    extract_key_definitions_for_compact,
)
from .compose_support import (
    process_compact_newsletter_data,
    save_newsletter_with_config,
)

# 로거 초기화
logger = get_logger()

__all__ = [
    "NewsletterConfig",
    "compose_compact_newsletter_html",
    "compose_newsletter",
    "compose_newsletter_html",
    "create_grouped_sections",
    "extract_and_prepare_top_articles",
    "extract_definitions",
    "extract_food_for_thought",
    "extract_key_definitions_for_compact",
    "process_compact_newsletter_data",
    "save_newsletter_with_config",
]


def compose_newsletter(data: Any, template_dir: str, style: str = "detailed") -> str:
    """
    뉴스레터를 생성하는 통합 함수 (compact와 detailed 공용)

    Args:
        data: 뉴스레터 데이터 (딕셔너리 또는 리스트)
        template_dir: 템플릿 디렉토리 경로
        style: 뉴스레터 스타일 ("compact", "detailed", "email_compatible")

    Returns:
        str: 렌더링된 HTML 뉴스레터
    """
    data, test_config = normalize_compose_input(data)

    if style == "email_compatible":
        original_template_style = data.get("template_style", "detailed")
        config = resolve_style_config(data, style)
        print(
            f"Composing email-compatible newsletter with {original_template_style} content style..."
        )
    else:
        config = resolve_style_config(data, style)
        print(
            f"Composing {style} newsletter for topic: {data.get('newsletter_topic', 'N/A')}..."
        )

    # 날짜 형식 포맷팅 처리 (기존 로직 유지)
    if "sections" in data:
        for section in data["sections"]:
            if "news_links" in section:
                for link in section["news_links"]:
                    if "source_and_date" in link:
                        source, date_str = extract_source_and_date(
                            link["source_and_date"]
                        )
                        if date_str:
                            formatted_date = format_date_for_display(date_str=date_str)
                            if formatted_date:
                                link["source_and_date"] = f"{source}, {formatted_date}"

    # Format top_articles if provided
    if "top_articles" in data:
        for art in data["top_articles"]:
            if "source_and_date" in art:
                src, d_str = extract_source_and_date(art["source_and_date"])
                if d_str:
                    fmt = format_date_for_display(date_str=d_str)
                    if fmt:
                        art["source_and_date"] = f"{src}, {fmt}"

    # 1. 뉴스키워드 결정 - 이미 data에 포함됨

    # 2. 뉴스 기사 검색 - 이미 완료됨

    # 3. 뉴스기사 기간에 대한 필터 - process_articles_node에서 완료

    # 4. 뉴스 기사의 점수 채점 - score_articles_node에서 완료

    # 5. 상위 3개를 먼저 선별
    top_articles = extract_and_prepare_top_articles(data, config["top_articles_count"])

    # 6. 나머지 기사들의 주제 그룹핑
    grouped_sections = create_grouped_sections(
        data,
        top_articles,
        max_groups=config["max_groups"],
        max_articles=config["max_articles"],
    )

    # 7. 그룹핑 뉴스내용 간단히 요약
    # (이미 섹션에 요약이 포함되어 있음)

    # 8. 이런 뜻이에요 용어 정의
    definitions = extract_definitions(data, grouped_sections, config)

    # 9. 생각해볼거리
    food_for_thought = extract_food_for_thought(data)

    # 10. 템플릿기반 최종 뉴스레터 생성
    return render_newsletter_template(
        data,
        template_dir,
        config,
        top_articles,
        grouped_sections,
        definitions,
        food_for_thought,
    )


# 기존 함수들을 새로운 통합 함수로 래핑
def compose_newsletter_html(data, template_dir: str, template_name: str) -> str:
    """기존 detailed 뉴스레터 생성 함수 (호환성 유지)"""
    return render_detailed_wrapper(
        data, template_dir, template_name, compose_newsletter
    )


def compose_compact_newsletter_html(
    data, template_dir: str, template_name: str = "newsletter_template_compact.html"
) -> str:
    """기존 compact 뉴스레터 생성 함수 (호환성 유지)"""
    return render_compact_wrapper(data, template_dir, template_name, compose_newsletter)
