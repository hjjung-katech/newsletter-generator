# Placeholder for newsletter composition logic
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple
from .date_utils import (
    format_date_for_display,
    extract_source_and_date,
    standardize_date,
)
import json


# 뉴스레터 스타일 설정
class NewsletterConfig:
    """뉴스레터 설정 클래스"""

    @staticmethod
    def get_config(style: str = "detailed") -> Dict[str, Any]:
        """스타일별 뉴스레터 설정 반환"""
        configs = {
            "compact": {
                "max_articles": 10,  # 총 기사 수
                "top_articles_count": 3,  # 상위 기사 수
                "max_groups": 3,  # 최대 그룹 수
                "max_definitions": 3,  # 최대 용어 정의 수
                "summary_style": "brief",  # 요약 스타일
                "template_name": "newsletter_template_compact.html",
                "title_default": "주간 산업 동향 브리프",
            },
            "detailed": {
                "max_articles": None,  # 모든 필터된 기사
                "top_articles_count": 3,  # 상위 기사 수
                "max_groups": 6,  # 최대 그룹 수
                "max_definitions": None,  # 그룹별 0-2개, 중복 없음
                "summary_style": "detailed",  # 요약 스타일
                "template_name": "newsletter_template.html",
                "title_default": "주간 산업 동향 뉴스 클리핑",
            },
        }
        return configs.get(style, configs["detailed"])


def compose_newsletter(data: Any, template_dir: str, style: str = "detailed") -> str:
    """
    뉴스레터를 생성하는 통합 함수 (compact와 detailed 공용)

    Args:
        data: 뉴스레터 데이터 (딕셔너리 또는 리스트)
        template_dir: 템플릿 디렉토리 경로
        style: 뉴스레터 스타일 ("compact" 또는 "detailed")

    Returns:
        str: 렌더링된 HTML 뉴스레터
    """
    # 테스트 설정 추출
    if isinstance(data, dict):
        data, test_config = extract_test_config(data)

    # 리스트 형태의 데이터를 딕셔너리로 변환 (기존 호환성 유지)
    if isinstance(data, list):
        # 리스트 형태로 제공된 경우 구조화된 데이터로 변환
        newsletter_data = {
            "newsletter_topic": "주간 산업 동향",
            "sections": [
                {
                    "title": "주요 기술 동향",
                    "summary_paragraphs": [
                        "다음은 지난 한 주간의 주요 기술 동향 요약입니다."
                    ],
                    "news_links": [],
                }
            ],
        }

        for article in data:
            article_title = article.get("title", "제목 없음")
            article_url = article.get("url", "#")
            article_source = article.get("source", "출처 미상")
            article_date = article.get("date", "날짜 미상")

            # 링크 정보 추가
            link_info = {
                "title": article_title,
                "url": article_url,
                "source_and_date": f"{article_source}, {article_date}",
            }
            newsletter_data["sections"][0]["news_links"].append(link_info)

            # 첫 번째 기사 내용을 요약 본문으로 사용
            if len(newsletter_data["sections"][0]["summary_paragraphs"]) == 1:
                summary = article.get("summary_text") or article.get("content", "")
                # 간단한 문단 나누기 (실제로는 더 정교한 처리가 필요할 수 있음)
                paragraphs = summary.split("\n\n")
                newsletter_data["sections"][0]["summary_paragraphs"] = paragraphs[
                    :3
                ]  # 최대 3개 문단

        data = newsletter_data

    # 설정 가져오기
    config = NewsletterConfig.get_config(style)

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

    print(
        f"Composing {style} newsletter for topic: {data.get('newsletter_topic', 'N/A')}..."
    )

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


def extract_and_prepare_top_articles(
    data: Dict[str, Any], count: int = 3
) -> List[Dict[str, Any]]:
    """상위 기사들을 추출하고 템플릿용으로 준비"""

    # 기존 top_articles가 있으면 사용
    if "top_articles" in data:
        top_articles = data["top_articles"][:count]
    elif "sections" in data:
        # sections에서 첫 번째 기사들 추출
        top_articles = extract_top_articles_from_sections(data["sections"])[:count]
    else:
        top_articles = []

    # 템플릿용 포맷팅
    prepared_articles = []
    for article in top_articles:
        # 날짜 형식 포맷팅
        source_and_date = article.get("source_and_date", "")
        if source_and_date:
            source, date_str = extract_source_and_date(source_and_date)
            if date_str:
                formatted_date = format_date_for_display(date_str=date_str)
                if formatted_date:
                    source_and_date = f"{source} · {formatted_date}"

        prepared_article = {
            "title": article.get("title", ""),
            "url": article.get("url", "#"),
            "snippet": article.get("snippet", article.get("summary_text", "")),
            "source_and_date": source_and_date,
        }
        prepared_articles.append(prepared_article)

    return prepared_articles


def create_grouped_sections(
    data: Dict[str, Any],
    top_articles: List[Dict[str, Any]],
    max_groups: int = 6,
    max_articles: int = None,
) -> List[Dict[str, Any]]:
    """그룹화된 섹션들을 생성"""

    # 기존 grouped_sections가 있으면 사용
    if "grouped_sections" in data:
        return data["grouped_sections"][:max_groups]

    # sections에서 grouped_sections 생성
    sections = data.get("sections", [])
    if not sections:
        return []

    # 이미 선택된 상위 기사들의 URL 추출
    excluded_urls = {article.get("url", "") for article in top_articles}

    grouped_sections = []
    article_count = 0

    for section in sections[:max_groups]:
        # 섹션의 기사 목록 가져오기
        news_links = section.get("news_links", [])
        articles = section.get("articles", [])
        article_list = news_links if news_links else articles

        # 상위 기사로 선택된 것들 제외
        remaining_articles = [
            link for link in article_list if link.get("url", "") not in excluded_urls
        ]

        # max_articles 제한 확인 (compact 모드용)
        if max_articles and article_count + len(
            remaining_articles
        ) > max_articles - len(top_articles):
            remaining_articles = remaining_articles[
                : max_articles - len(top_articles) - article_count
            ]

        if remaining_articles:
            # 이모지 추가된 섹션 제목
            section_title = add_emoji_to_section_title(section.get("title", "기타"))

            grouped_section = {
                "heading": section_title,
                "intro": (
                    section.get("summary_paragraphs", [""])[0]
                    if section.get("summary_paragraphs")
                    else ""
                ),
                "articles": remaining_articles,
            }
            grouped_sections.append(grouped_section)
            article_count += len(remaining_articles)

            # max_articles 도달하면 중단
            if max_articles and article_count >= max_articles - len(top_articles):
                break

    return grouped_sections


def extract_definitions(
    data: Dict[str, Any], grouped_sections: List[Dict[str, Any]], config: Dict[str, Any]
) -> List[Dict[str, str]]:
    """용어 정의들을 추출"""

    # 기존 definitions가 있으면 사용
    if "definitions" in data:
        definitions = data["definitions"]
        if config["max_definitions"]:
            return definitions[: config["max_definitions"]]
        return definitions

    # sections에서 정의 추출
    sections = data.get("sections", [])
    return extract_key_definitions_for_compact(sections)[
        : config["max_definitions"] or 999
    ]


def extract_food_for_thought(data: Dict[str, Any]) -> str:
    """생각해볼 거리 추출"""
    food_for_thought = data.get("food_for_thought")

    if not food_for_thought:
        return ""

    if isinstance(food_for_thought, dict):
        # detailed 버전용 딕셔너리 형태
        return food_for_thought
    else:
        # compact 버전용 문자열 형태
        return str(food_for_thought)


def render_newsletter_template(
    data: Dict[str, Any],
    template_dir: str,
    config: Dict[str, Any],
    top_articles: List[Dict[str, Any]],
    grouped_sections: List[Dict[str, Any]],
    definitions: List[Dict[str, str]],
    food_for_thought: Any,
) -> str:
    """템플릿을 렌더링하여 최종 HTML 생성"""

    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(config["template_name"])

    # 현재 날짜와 시간 가져오기
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")

    generation_date = data.get(
        "generation_date", os.environ.get("GENERATION_DATE", current_date)
    )
    generation_timestamp = data.get(
        "generation_timestamp", os.environ.get("GENERATION_TIMESTAMP", current_time)
    )

    # 스타일별 컨텍스트 준비
    if config["template_name"] == "newsletter_template_compact.html":
        # Compact 템플릿용 컨텍스트
        context = {
            "newsletter_title": data.get("newsletter_topic", config["title_default"]),
            "tagline": data.get(
                "tagline", "이번 주, 주요 산업 동향을 미리 만나보세요."
            ),
            "generation_date": generation_date,
            "issue_no": data.get("issue_no"),
            "top_articles": top_articles,
            "grouped_sections": grouped_sections,
            "definitions": definitions,
            "food_for_thought": food_for_thought,
            "copyright_year": generation_date.split("-")[0],
            "publisher_name": data.get("company_name", "Your Company"),
            "company_name": data.get("company_name", "Your Company"),
        }
    else:
        # Detailed 템플릿용 컨텍스트
        context = {
            "newsletter_topic": data.get("newsletter_topic", "주간 산업 동향"),
            "generation_date": generation_date,
            "generation_timestamp": generation_timestamp,
            "recipient_greeting": data.get("recipient_greeting", "안녕하세요,"),
            "introduction_message": data.get(
                "introduction_message",
                "지난 한 주간의 주요 산업 동향을 정리해 드립니다.",
            ),
            "sections": data.get("sections", []),
            "food_for_thought": food_for_thought,
            "closing_message": data.get(
                "closing_message",
                "다음 주에 더 유익한 정보로 찾아뵙겠습니다. 감사합니다.",
            ),
            "editor_signature": data.get("editor_signature", "편집자 드림"),
            "company_name": data.get("company_name", "Your Newsletter Co."),
        }

        # 검색 키워드 추가
        if "search_keywords" in data and data["search_keywords"]:
            if isinstance(data["search_keywords"], list):
                context["search_keywords"] = ", ".join(data["search_keywords"])
            else:
                context["search_keywords"] = data["search_keywords"]

        # top_articles 추가 (detailed에서도 표시 가능)
        if "top_articles" in data or top_articles:
            context["top_articles"] = data.get("top_articles", top_articles)

    return template.render(context)


# 기존 함수들을 새로운 통합 함수로 래핑
def compose_newsletter_html(data, template_dir: str, template_name: str) -> str:
    """기존 detailed 뉴스레터 생성 함수 (호환성 유지)"""
    # 템플릿 이름이 지정된 경우 사용, 아닌 경우 기본값 사용
    if template_name and template_name != "newsletter_template.html":
        # 사용자 정의 템플릿 처리
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )
        template = env.get_template(
            template_name
        )  # 여기서 TemplateNotFound 예외 발생 가능

        # 간단한 컨텍스트로 렌더링
        context = {
            "newsletter_topic": data.get("newsletter_topic", "주간 산업 동향"),
            "generation_date": data.get(
                "generation_date", datetime.now().strftime("%Y-%m-%d")
            ),
            "sections": data.get("sections", []),
        }
        return template.render(context)

    return compose_newsletter(data, template_dir, "detailed")


def compose_compact_newsletter_html(
    data, template_dir: str, template_name: str = "newsletter_template_compact.html"
) -> str:
    """기존 compact 뉴스레터 생성 함수 (호환성 유지)"""
    # 템플릿 이름이 지정된 경우 직접 로딩해서 예외 확인
    if template_name != "newsletter_template_compact.html":
        # 사용자 정의 템플릿 처리 - 여기서 예외가 발생할 수 있음
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )
        template = env.get_template(
            template_name
        )  # 여기서 TemplateNotFound 예외 발생 가능

        # 간단한 컨텍스트로 렌더링
        context = {
            "newsletter_title": data.get("newsletter_topic", "주간 산업 동향 브리프"),
            "tagline": "이번 주, 주요 산업 동향을 미리 만나보세요.",
            "generation_date": data.get(
                "generation_date", datetime.now().strftime("%Y-%m-%d")
            ),
            "definitions": data.get("definitions", []),
        }
        return template.render(context)

    return compose_newsletter(data, template_dir, "compact")


def extract_test_config(data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Extract test configuration from data if present.

    Args:
        data: Dictionary possibly containing embedded test configuration

    Returns:
        Tuple of (newsletter_data, test_config)
    """
    # Create a copy to avoid modifying the original
    newsletter_data = data.copy()
    test_config = {}

    # Extract test config if present
    if "_test_config" in newsletter_data:
        test_config = newsletter_data.pop("_test_config")

    return newsletter_data, test_config


def save_newsletter_with_config(
    data: Dict[str, Any], config_data: Dict[str, Any], output_path: str
) -> None:
    """
    Save the newsletter data with embedded test configuration.

    Args:
        data: Newsletter content data
        config_data: Configuration data to embed
        output_path: Path where to save the data
    """
    # Create a copy to avoid modifying the original
    data_to_save = data.copy()

    # Embed the configuration
    data_to_save["_test_config"] = config_data

    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Save the file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=2, ensure_ascii=False)

    print(f"Saved newsletter data with embedded config to {output_path}")


def process_compact_newsletter_data(newsletter_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    기존 뉴스레터 데이터를 간결한 버전으로 변환합니다.

    Args:
        newsletter_data: 원본 뉴스레터 데이터

    Returns:
        Dict: 간결한 버전용으로 변환된 데이터
    """
    print(
        f"[DEBUG] process_compact_newsletter_data input keys: {list(newsletter_data.keys())}"
    )

    compact_data = {
        "newsletter_title": newsletter_data.get(
            "newsletter_topic", "주간 산업 동향 브리프"
        ),
        "tagline": "이번 주, 주요 산업 동향을 미리 만나보세요.",
        "company_name": newsletter_data.get("company_name", "Your Company"),
        "generation_date": newsletter_data.get("generation_date"),
        "issue_no": newsletter_data.get("issue_no"),
    }

    # 상위 중요 기사 처리 (최대 3개)
    top_articles = newsletter_data.get("top_articles", [])
    print(f"[DEBUG] Found top_articles: {len(top_articles)}")

    if not top_articles and "sections" in newsletter_data:
        # top_articles가 없으면 각 섹션에서 첫 번째 기사들을 선택
        print(f"[DEBUG] No top_articles, extracting from sections")
        top_articles = extract_top_articles_from_sections(newsletter_data["sections"])

    # 상위 3개로 제한하고 요약 추가
    compact_data["top_articles"] = prepare_top_articles_for_compact(top_articles[:3])

    # Check if grouped_sections already exist in the input data
    if "grouped_sections" in newsletter_data:
        print(
            f"[DEBUG] Using existing grouped_sections: {len(newsletter_data['grouped_sections'])}"
        )
        compact_data["grouped_sections"] = newsletter_data["grouped_sections"]
    else:
        print(f"[DEBUG] Creating grouped_sections from sections")
        # 나머지 기사들을 그룹별로 정리
        compact_data["grouped_sections"] = prepare_grouped_sections_for_compact(
            newsletter_data.get("sections", []),
            top_articles[:3],  # 이미 선택된 상위 기사들 제외
        )

    # 용어 설명 처리 (최대 3개까지만)
    if "definitions" in newsletter_data:
        print(
            f"[DEBUG] Using existing definitions: {len(newsletter_data['definitions'])}"
        )
        compact_data["definitions"] = newsletter_data["definitions"]
    else:
        print(f"[DEBUG] Creating definitions from sections")
        compact_data["definitions"] = extract_key_definitions_for_compact(
            newsletter_data.get("sections", [])
        )

    # 생각해볼 거리 처리
    food_for_thought = newsletter_data.get("food_for_thought")
    if food_for_thought:
        if isinstance(food_for_thought, dict):
            # 간결하게 메시지만 사용
            compact_data["food_for_thought"] = food_for_thought.get(
                "message", food_for_thought.get("quote", "")
            )
        else:
            compact_data["food_for_thought"] = str(food_for_thought)

    return compact_data


def extract_top_articles_from_sections(
    sections: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    각 섹션에서 첫 번째 뉴스 링크를 추출하여 상위 기사로 만듭니다.
    """
    top_articles = []

    for section in sections[:3]:  # 최대 3개 섹션에서
        news_links = section.get("news_links", [])
        if news_links:
            first_article = news_links[0]
            # 요약 텍스트 생성 (섹션의 첫 번째 요약 문단 사용)
            summary_paragraphs = section.get("summary_paragraphs", [])
            snippet = summary_paragraphs[0] if summary_paragraphs else ""

            top_article = {
                "title": first_article.get("title", ""),
                "url": first_article.get("url", "#"),
                "snippet": snippet[:150] + "..." if len(snippet) > 150 else snippet,
                "source_and_date": first_article.get("source_and_date", ""),
            }
            top_articles.append(top_article)

    return top_articles


def prepare_top_articles_for_compact(
    top_articles: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    상위 기사들을 간결한 템플릿용으로 포맷팅합니다.
    """
    prepared_articles = []

    for article in top_articles:
        # 날짜 형식 포맷팅
        source_and_date = article.get("source_and_date", "")
        if source_and_date:
            source, date_str = extract_source_and_date(source_and_date)
            if date_str:
                formatted_date = format_date_for_display(date_str=date_str)
                if formatted_date:
                    source_and_date = f"{source} · {formatted_date}"

        prepared_article = {
            "title": article.get("title", ""),
            "url": article.get("url", "#"),
            "snippet": article.get("snippet", article.get("summary_text", "")),
            "source_and_date": source_and_date,
        }
        prepared_articles.append(prepared_article)

    return prepared_articles


def prepare_grouped_sections_for_compact(
    sections: List[Dict[str, Any]], exclude_articles: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    섹션들을 간결한 템플릿용 그룹으로 변환합니다.
    """
    grouped_sections = []

    # 이미 상위 기사로 선택된 기사들의 URL 추출
    excluded_urls = {article.get("url", "") for article in exclude_articles}

    for section in sections:
        # compact 모드에서는 news_links 대신 articles를 사용
        news_links = section.get("news_links", [])
        articles = section.get("articles", [])

        # news_links가 있으면 사용하고, 없으면 articles 사용
        article_list = news_links if news_links else articles

        remaining_articles = [
            link for link in article_list if link.get("url", "") not in excluded_urls
        ]

        if remaining_articles:  # 남은 기사가 있을 때만 섹션 추가
            # 그룹 제목에 이모지 추가
            section_title = section.get("title", "")
            group_heading = add_emoji_to_section_title(section_title)

            # 간단한 소개 문구 생성 (첫 번째 요약 문단의 첫 문장 사용)
            # compact 모드에서는 intro 필드 사용
            intro = section.get("intro", "")
            if not intro:
                summary_paragraphs = section.get("summary_paragraphs", [])
                if summary_paragraphs:
                    first_paragraph = summary_paragraphs[0]
                    sentences = first_paragraph.split(". ")
                    intro = (
                        sentences[0] + "."
                        if sentences
                        else first_paragraph[:100] + "..."
                    )

            grouped_section = {
                "heading": group_heading,
                "intro": intro,
                "articles": [
                    {
                        "title": article.get("title", ""),
                        "url": article.get("url", "#"),
                        "source_and_date": format_compact_source_date(
                            article.get("source_and_date", "")
                        ),
                    }
                    for article in remaining_articles[:4]  # 최대 4개까지만
                ],
            }
            grouped_sections.append(grouped_section)

    return grouped_sections


def add_emoji_to_section_title(title: str) -> str:
    """
    섹션 제목에 적절한 이모지를 추가합니다.
    """
    title_lower = title.lower()

    if any(word in title_lower for word in ["투자", "펀딩", "자금", "ipo", "상장"]):
        return f"🚀 {title}"
    elif any(word in title_lower for word in ["정책", "규제", "법", "윤리"]):
        return f"🏛️ {title}"
    elif any(word in title_lower for word in ["연구", "기술", "개발", "특허"]):
        return f"📊 {title}"
    elif any(word in title_lower for word in ["시장", "수요", "트렌드", "소비"]):
        return f"🌐 {title}"
    else:
        return f"📈 {title}"


def format_compact_source_date(source_and_date: str) -> str:
    """
    간결한 템플릿용으로 출처와 날짜를 포맷팅합니다.
    """
    if not source_and_date:
        return ""

    source, date_str = extract_source_and_date(source_and_date)
    if date_str:
        formatted_date = format_date_for_display(date_str=date_str)
        if formatted_date:
            return f"{source} · {formatted_date}"

    return source_and_date


def extract_key_definitions_for_compact(
    sections: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """
    각 섹션에서 핵심 용어 정의를 추출합니다. 최대 3개까지만 반환합니다.

    Args:
        sections: 뉴스레터 섹션 리스트

    Returns:
        List[Dict]: 용어와 설명을 포함한 딕셔너리 리스트
    """
    all_definitions = []

    for section in sections:
        definitions = section.get("definitions", [])
        if definitions:
            # 각 섹션에서 첫 번째 정의만 가져옴 (가장 중요한 용어로 간주)
            if len(definitions) > 0:
                all_definitions.append(definitions[0])

    # 최대 3개까지만 반환 (가독성을 위해)
    return all_definitions[:3]


# Example usage (for testing purposes):
if __name__ == "__main__":
    # This is a simplified example. In a real scenario,
    # 'data' would be populated by other parts of your application (e.g., data collection, summarization).
    example_data = {
        "newsletter_topic": "AI 신약 개발, 디지털 치료제, 세포 유전자 치료제, 마이크로바이옴, 합성생물학",
        "generation_date": datetime.now().strftime("%Y-%m-%d"),
        "generation_timestamp": datetime.now().strftime("%H:%M:%S"),
        "recipient_greeting": "안녕하세요, 전략프로젝트팀의 젊은 팀원과 수석전문위원 여러분.",
        "introduction_message": "지난 한 주간의 AI 신약 개발, 디지털 치료제, 세포 유전자 치료제, 마이크로바이옴, 합성생물학 산업 관련 주요 기술 동향 및 뉴스를 정리하여 보내드립니다. 함께 살펴보시고 R&D 전략 수립에 참고하시면 좋겠습니다.",
        "sections": [
            {
                "title": "AI 신약 개발",
                "summary_paragraphs": [
                    "AI를 활용한 신약 개발은 업계의 큰 관심을 받고 있으며, 개발 시간 단축 및 성공률 증가에 기여할 것으로 기대됩니다. 다만, 아직 극복해야 할 과제들이 존재하며, 관련 교육 플랫폼 및 생태계 조성이 중요합니다."
                ],
                "definitions": [
                    {
                        "term": "AI 신약 개발",
                        "explanation": "인공지능 기술을 활용하여 신약 후보물질 발굴, 약물 설계, 임상시험 최적화 등의 과정을 개선하는 연구 분야입니다.",
                    }
                ],
                "news_links": [
                    {
                        "title": "[PDF] AI를 활용한 혁신 신약개발의 동향 및 정책 시사점",
                        "url": "https://www.kistep.re.kr/boardDownload.es?bid=0031&list_no=94091&seq=1",
                        "source_and_date": "KISTEP",
                    },
                    {
                        "title": '제약바이오, AI 신약개발 박차…"패러다임 바뀐다"',
                        "url": "https://www.kpanews.co.kr/article/show.asp?idx=256331&category=D",
                        "source_and_date": "KPA News",
                    },
                ],
            },
            {
                "title": "디지털 치료제",
                "summary_paragraphs": [
                    "디지털 치료제는 약물이 아닌 소프트웨어를 기반으로 질병을 예방, 관리, 치료하는 새로운 형태의 치료제입니다. 불면증, 우울증 등 다양한 질환에 적용 가능성을 보이며, 관련 규제 및 법적 기준 마련이 필요한 시점입니다."
                ],
                "definitions": [
                    {
                        "term": "디지털 치료제",
                        "explanation": "소프트웨어 형태의 의료기기로, 질병의 예방, 관리, 치료를 목적으로 합니다. 주로 앱, 게임, 웨어러블 기기 등을 통해 제공됩니다.",
                    }
                ],
                "news_links": [
                    {
                        "title": "디지털 치료제 - 나무위키",
                        "url": "https://namu.wiki/w/%EB%94%94%EC%A7%80%ED%84%B8%20%EC%B9%98%EB%A3%8C%EC%A0%9C",
                        "source_and_date": "Namuwiki",
                    }
                ],
            },
            # ... more sections ...
        ],
        "food_for_thought": {
            "quote": "미래는 예측하는 것이 아니라 만들어가는 것이다.",
            "author": "피터 드러커",
            "message": "위에 언급된 다섯 가지 기술은 모두 미래 의료 패러다임을 변화시킬 잠재력을 가지고 있습니다. 각 기술의 발전 동향을 꾸준히 주시하고, 상호 연관성을 고려하여 R&D 전략을 수립한다면, 혁신적인 성과 창출과 국민 건강 증진에 기여할 수 있을 것입니다. 각 기술의 발전 속도, 시장 경쟁 환경, 규제 동향 등을 종합적으로 분석하여 우리나라가 글로벌 바이오헬스 시장을 선도할 수 있는 전략을 모색해야 할 시점입니다.",
        },
        "closing_message": "다음 주에 더 유익한 정보로 찾아뵙겠습니다. 감사합니다.",
        "editor_signature": "편집자 드림",
        "company_name": "전략프로젝트팀",
    }

    # Sample test config
    example_config = {
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "keywords": ["AI", "신약", "디지털치료제", "마이크로바이옴", "합성생물학"],
        "topic": "바이오 기술 동향",
        "language": "ko",
        "date_range": 7,
    }

    # Define template directory and name (assuming this script is in newsletter/ and templates/ is a sibling)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(
        current_dir
    )  # Moves up one level to the project root
    template_directory = os.path.join(project_root, "templates")
    template_file = "newsletter_template.html"

    # Check if template directory and file exist
    if not os.path.isdir(template_directory):
        print(f"Error: Template directory not found at {template_directory}")
    elif not os.path.exists(os.path.join(template_directory, template_file)):
        print(
            f"Error: Template file not found at {os.path.join(template_directory, template_file)}"
        )
    else:
        print(f"Template directory: {template_directory}")
        print(f"Template file: {template_file}")
        try:
            # Combine data and config
            example_data_with_config = example_data.copy()
            example_data_with_config["_test_config"] = example_config

            # Generate HTML
            html_output = compose_newsletter_html(
                example_data_with_config, template_directory, template_file
            )

            # Save HTML
            timestamp = example_config["timestamp"]
            output_filename = os.path.join(
                project_root,
                "output",
                f"composed_newsletter_test_{timestamp}.html",
            )
            os.makedirs(os.path.join(project_root, "output"), exist_ok=True)
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(html_output)
            print(f"Test newsletter saved to {output_filename}")

            # Save data with config for testing
            json_filename = os.path.join(
                project_root,
                "output/intermediate_processing",
                f"render_data_{timestamp}_test.json",
            )
            os.makedirs(
                os.path.join(project_root, "output/intermediate_processing"),
                exist_ok=True,
            )
            save_newsletter_with_config(example_data, example_config, json_filename)

        except Exception as e:
            print(f"An error occurred during test composition: {e}")
