# Placeholder for newsletter composition logic
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .date_utils import (
    extract_source_and_date,
    format_date_for_display,
    standardize_date,
)
from .utils.logger import get_logger

# 로거 초기화
logger = get_logger()


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
                "title_default": "주간 산업 동향 뉴스 클리핑",
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
            "email_compatible": {
                "max_articles": None,  # 모든 필터된 기사 (detailed 스타일 기본값)
                "top_articles_count": 3,  # 상위 기사 수
                "max_groups": 6,  # 최대 그룹 수
                "max_definitions": None,  # 그룹별 0-2개, 중복 없음
                "summary_style": "detailed",  # 요약 스타일 (detailed 스타일 기본값)
                "template_name": "newsletter_template_email_compatible.html",
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
        style: 뉴스레터 스타일 ("compact", "detailed", "email_compatible")

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
            "top_articles": [],  # 상위 기사용
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

        # 상위 3개 기사를 top_articles로 설정
        top_count = min(3, len(data))
        for i, article in enumerate(data[:top_count]):
            article_content = article.get("content") or article.get("snippet", "")
            top_article = {
                "title": article.get("title", "제목 없음"),
                "url": article.get("url", "#"),
                "snippet": (
                    article_content[:200] + "..."
                    if len(article_content) > 200
                    else article_content
                ),
                "summary_text": article_content,
                "source_and_date": f"{article.get('source', '출처 미상')}, {article.get('date', '날짜 미상')}",
            }
            newsletter_data["top_articles"].append(top_article)

        # 나머지 기사들을 sections에 추가
        for article in data[top_count:]:
            article_title = article.get("title", "제목 없음")
            article_url = article.get("url", "#")
            article_source = article.get("source", "출처 미상")
            article_date = article.get("date", "날짜 미상")
            article_content = article.get("content") or article.get("snippet", "")

            # 링크 정보 추가 (content 필드를 snippet으로 매핑)
            link_info = {
                "title": article_title,
                "url": article_url,
                "snippet": article_content,
                "summary_text": article_content,
                "source_and_date": f"{article_source}, {article_date}",
            }
            newsletter_data["sections"][0]["news_links"].append(link_info)

            # 첫 번째 기사 내용을 요약 본문으로 사용
            if len(newsletter_data["sections"][0]["summary_paragraphs"]) == 1:
                # 간단한 문단 나누기 (실제로는 더 정교한 처리가 필요할 수 있음)
                paragraphs = article_content.split("\n\n") if article_content else [""]
                newsletter_data["sections"][0]["summary_paragraphs"] = paragraphs[
                    :3
                ]  # 최대 3개 문단

        data = newsletter_data

    # email_compatible인 경우 template_style 정보를 확인하여 적절한 설정 적용
    if style == "email_compatible":
        # 데이터에서 원래 template_style 확인 (graph.py에서 전달됨)
        original_template_style = data.get("template_style", "detailed")

        # 원래 template_style의 설정을 가져옴 (CLI 기존 기능 유지)
        config = NewsletterConfig.get_config(original_template_style)

        # email_compatible 템플릿 사용을 위해 template_name만 변경
        config["template_name"] = "newsletter_template_email_compatible.html"

        logger.info(
            f"Composing email-compatible newsletter with {original_template_style} content style..."
        )
    else:
        # 설정 가져오기
        config = NewsletterConfig.get_config(style)
        logger.info(
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


def extract_and_prepare_top_articles(
    data: Dict[str, Any], count: int = 3
) -> List[Dict[str, Any]]:
    """
    상위 기사(top_articles)를 sections/grouped_sections와 분리하여 추출 및 템플릿용으로 준비합니다.
    - data["top_articles"]가 있으면 우선 사용
    - 없으면 data["sections"]에서 추출
    - 항상 top_articles는 grouped_sections와 별도 관리
    """
    # 기존 top_articles가 있으면 사용
    if "top_articles" in data and data["top_articles"]:
        top_articles = data["top_articles"][:count]
    elif "sections" in data:
        # sections에서 첫 번째 기사들 추출
        top_articles = extract_top_articles_from_sections(data["sections"])[:count]
    else:
        # sections도 없고 top_articles도 없는 경우 빈 리스트 반환
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
    """
    grouped_sections(주제별 기사 그룹)은 top_articles와 분리하여 생성합니다.
    - top_articles에 포함된 기사 URL은 제외
    - 항상 top_articles와 별도 관리
    - 각 그룹에 해당하는 definitions 포함
    """
    # 기존 grouped_sections가 있으면 사용
    if "grouped_sections" in data:
        existing_sections = data["grouped_sections"][:max_groups]
        # 기존 grouped_sections에 definitions가 없으면 추가
        for section in existing_sections:
            if "definitions" not in section or not section["definitions"]:
                # 원본 sections에서 해당하는 정의 찾기
                section_title = (
                    section.get("heading", "")
                    .replace("🚀 ", "")
                    .replace("🏛️ ", "")
                    .replace("📊 ", "")
                    .replace("🌐 ", "")
                    .replace("📈 ", "")
                )
                original_section = next(
                    (
                        s
                        for s in data.get("sections", [])
                        if s.get("title") == section_title
                    ),
                    None,
                )
                if original_section and "definitions" in original_section:
                    section["definitions"] = original_section["definitions"]
                else:
                    section["definitions"] = []
        return existing_sections

    # sections에서 grouped_sections 생성
    sections = data.get("sections", [])
    if not sections:
        return []

    # 이미 선택된 상위 기사들의 URL 추출
    excluded_urls = {article.get("url", "") for article in top_articles}

    grouped_sections = []
    article_count = 0

    # compact 모드 여부 확인 (max_articles가 설정되어 있으면 compact 모드)
    is_compact = max_articles is not None

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

        if remaining_articles:  # 남은 기사가 있을 때만 섹션 추가
            # 이모지 추가된 섹션 제목
            section_title = add_emoji_to_section_title(section.get("title", "기타"))

            # intro 생성 - compact 모드에서는 간결하게
            intro = ""
            if is_compact:
                # compact 모드: section.intro를 직접 사용 (요약 체인에서 이미 생성됨)
                intro = section.get("intro", "")
                # intro가 없으면 기본 메시지 생성
                if not intro:
                    intro = f"{section.get('title', '기타')}에 대한 주요 동향입니다."
            else:
                # detailed 모드: 기존 방식 유지
                intro = (
                    section.get("summary_paragraphs", [""])[0]
                    if section.get("summary_paragraphs")
                    else ""
                )

            grouped_section = {
                "heading": section_title,
                "intro": intro,
                "articles": remaining_articles,
                "definitions": section.get("definitions", []),  # 섹션의 정의 포함
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


def extract_food_for_thought(data: Dict[str, Any]) -> Any:
    """생각해볼 거리 추출"""
    food_for_thought = data.get("food_for_thought")

    if not food_for_thought:
        return {"message": ""}

    if isinstance(food_for_thought, dict):
        # 딕셔너리 형태 그대로 반환
        return food_for_thought
    else:
        # 문자열인 경우 딕셔너리로 변환하여 반환
        return {"message": str(food_for_thought)}


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

    template_name = config["template_name"]
    logger.debug(f"템플릿 로딩 중: {template_name}")
    template = env.get_template(template_name)
    logger.debug(f"템플릿 로딩 완료: {template_name}")

    # 현재 날짜와 시간 가져오기
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")

    generation_date = data.get(
        "generation_date", os.environ.get("GENERATION_DATE", current_date)
    )
    generation_timestamp = data.get(
        "generation_timestamp", os.environ.get("GENERATION_TIMESTAMP", current_time)
    )

    # 설정 파일에서 뉴스레터 설정 로드
    newsletter_settings = load_newsletter_settings()

    # 뉴스레터 제목 생성 로직 개선
    newsletter_topic = data.get("newsletter_topic")
    newsletter_title = data.get("newsletter_title")

    # 제목이 명시적으로 설정되지 않은 경우 도메인 기반 제목 생성
    if not newsletter_title and newsletter_topic:
        # 도메인이 있거나 의미 있는 주제가 있는 경우 "도메인명 주간 산업 동향 뉴스 클리핑" 형식 사용
        domain = data.get("domain")
        if domain:
            # 명시적 도메인이 있는 경우
            newsletter_title = f"{domain} 주간 산업동향 뉴스 클리핑"
        elif newsletter_topic and newsletter_topic not in [
            "최신 산업 동향",
            "General News",
        ]:
            # 의미 있는 주제가 추출된 경우
            # "외 N개 분야" 형식이면 첫 번째 키워드만 사용
            if " 외 " in newsletter_topic and "개 분야" in newsletter_topic:
                main_topic = newsletter_topic.split(" 외 ")[0]
                newsletter_title = f"{main_topic} 주간 산업 동향 뉴스 클리핑"
            else:
                newsletter_title = f"{newsletter_topic} 주간 산업 동향 뉴스 클리핑"
        else:
            newsletter_title = newsletter_settings.get(
                "newsletter_title", config["title_default"]
            )
    elif not newsletter_title:
        newsletter_title = newsletter_settings.get(
            "newsletter_title", config["title_default"]
        )

    # 공통 컨텍스트 변수들 (설정 파일 값을 기본값으로 사용)
    common_context = {
        "generation_date": generation_date,
        "generation_timestamp": generation_timestamp,
        "newsletter_topic": newsletter_topic,
        "newsletter_title": newsletter_title,
        "issue_no": data.get("issue_no"),
        "top_articles": top_articles,
        "definitions": definitions,
        "food_for_thought": food_for_thought,
        "copyright_year": generation_date.split("-")[0],
        "publisher_name": data.get(
            "publisher_name",
            data.get(
                "company_name",
                newsletter_settings.get("publisher_name", "Your Company"),
            ),
        ),
        "company_name": data.get(
            "company_name", newsletter_settings.get("company_name", "Your Company")
        ),
        "company_tagline": data.get(
            "company_tagline", newsletter_settings.get("company_tagline")
        ),
        "footer_disclaimer": data.get(
            "footer_disclaimer", newsletter_settings.get("footer_disclaimer")
        ),
        "footer_contact": data.get(
            "footer_contact", newsletter_settings.get("footer_contact")
        ),
        "editor_name": data.get("editor_name", newsletter_settings.get("editor_name")),
        "editor_email": data.get(
            "editor_email", newsletter_settings.get("editor_email")
        ),
        "editor_title": data.get(
            "editor_title", newsletter_settings.get("editor_title", "편집자")
        ),
    }

    # 스타일별 컨텍스트 준비
    if config["template_name"] == "newsletter_template_compact.html":
        # Compact 템플릿용 컨텍스트
        context = {
            **common_context,
            "tagline": data.get(
                "tagline",
                newsletter_settings.get(
                    "tagline", "이번 주, 주요 산업 동향을 미리 만나보세요."
                ),
            ),
            "grouped_sections": grouped_sections,
        }
    elif config["template_name"] == "newsletter_template_email_compatible.html":
        # Email-compatible 템플릿용 컨텍스트 (template_style에 따라 다른 데이터 사용)
        context = {
            **common_context,
            "recipient_greeting": data.get("recipient_greeting", "안녕하세요,"),
            "introduction_message": data.get(
                "introduction_message",
                "지난 한 주간의 주요 산업 동향을 정리해 드립니다.",
            ),
            "closing_message": data.get(
                "closing_message",
                "다음 주에 더 유익한 정보로 찾아뵙겠습니다. 감사합니다.",
            ),
            "editor_signature": data.get("editor_signature", "편집자 드림"),
            # Email-compatible 템플릿은 template_style에 따라 다른 데이터를 사용
            "template_style": data.get("template_style", "detailed"),
            "grouped_sections": grouped_sections,  # compact style용
            "sections": data.get("sections", []),  # detailed style용
        }

        # 검색 키워드 추가
        if "search_keywords" in data and data["search_keywords"]:
            if isinstance(data["search_keywords"], list):
                context["search_keywords"] = ", ".join(data["search_keywords"])
            else:
                context["search_keywords"] = data["search_keywords"]
    else:
        # Detailed 템플릿용 컨텍스트
        context = {
            **common_context,
            "recipient_greeting": data.get("recipient_greeting", "안녕하세요,"),
            "introduction_message": data.get(
                "introduction_message",
                "지난 한 주간의 주요 산업 동향을 정리해 드립니다.",
            ),
            "sections": data.get("sections", []),
            "closing_message": data.get(
                "closing_message",
                "다음 주에 더 유익한 정보로 찾아뵙겠습니다. 감사합니다.",
            ),
            "editor_signature": data.get("editor_signature", "편집자 드림"),
        }

        # 검색 키워드 추가
        if "search_keywords" in data and data["search_keywords"]:
            if isinstance(data["search_keywords"], list):
                context["search_keywords"] = ", ".join(data["search_keywords"])
            else:
                context["search_keywords"] = data["search_keywords"]

    return template.render(context)


# 기존 함수들을 새로운 통합 함수로 래핑
def compose_newsletter_html(data, template_dir: str, template_name: str) -> str:
    """기존 detailed 뉴스레터 생성 함수 (호환성 유지)"""
    # 데이터 형태 확인 및 변환
    if isinstance(data, list):
        # 리스트인 경우 딕셔너리로 변환 (템플릿이 기대하는 구조로)
        top_articles = []
        sections = [
            {
                "title": "주요 기술 동향",
                "summary_paragraphs": [
                    "다음은 지난 한 주간의 주요 기술 동향 요약입니다."
                ],
                "news_links": [],
            }
        ]

        # 상위 3개 기사를 top_articles로 설정
        top_count = min(3, len(data))
        for article in data[:top_count]:
            # summary_text 필드를 우선으로 하고, 없으면 content나 snippet 사용
            article_content = (
                article.get("summary_text") or 
                article.get("content") or 
                article.get("snippet", "")
            )
            top_article = {
                "title": article.get("title", "제목 없음"),
                "url": article.get("url", "#"),
                "snippet": (
                    article_content[:200] + "..."
                    if len(article_content) > 200
                    else article_content
                ),
                "summary_text": article_content,
                "source_and_date": f"{article.get('source', '출처 미상')}, {article.get('date', '날짜 미상')}",
            }
            top_articles.append(top_article)

        # 나머지 기사들을 sections에 추가
        for article in data[top_count:]:
            # summary_text 필드를 우선으로 하고, 없으면 content나 snippet 사용
            article_content = (
                article.get("summary_text") or 
                article.get("content") or 
                article.get("snippet", "")
            )
            link_info = {
                "title": article.get("title", "제목 없음"),
                "url": article.get("url", "#"),
                "snippet": article_content,
                "summary_text": article_content,
                "source_and_date": f"{article.get('source', '출처 미상')}, {article.get('date', '날짜 미상')}",
            }
            sections[0]["news_links"].append(link_info)

        data = {
            "top_articles": top_articles,
            "sections": sections,
            "newsletter_topic": "주간 산업 동향",
            "newsletter_title": "주간 산업 동향 뉴스 클리핑",
        }
    elif not isinstance(data, dict):
        # 딕셔너리도 리스트도 아닌 경우 기본값으로 설정
        data = {
            "top_articles": [],
            "sections": [],
            "newsletter_topic": "주간 산업 동향",
            "newsletter_title": "주간 산업 동향 뉴스 클리핑",
        }

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

        # 현재 날짜와 시간 가져오기
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M:%S")

        generation_date = data.get(
            "generation_date", os.environ.get("GENERATION_DATE", current_date)
        )
        generation_timestamp = data.get(
            "generation_timestamp", os.environ.get("GENERATION_TIMESTAMP", current_time)
        )

        # 간단한 컨텍스트로 렌더링
        context = {
            "newsletter_topic": data.get("newsletter_topic", "주간 산업 동향"),
            "newsletter_title": data.get(
                "newsletter_title",
                data.get("newsletter_topic", "주간 산업 동향 뉴스 클리핑"),
            ),
            "generation_date": generation_date,
            "generation_timestamp": generation_timestamp,
            "sections": data.get("sections", []),
            "recipient_greeting": data.get("recipient_greeting"),
            "introduction_message": data.get("introduction_message"),
            "closing_message": data.get("closing_message"),
            "editor_signature": data.get("editor_signature"),
            "company_name": data.get("company_name"),
            "top_articles": data.get("top_articles", []),
            "food_for_thought": data.get("food_for_thought"),
            "search_keywords": data.get("search_keywords"),
        }

        # 검색 키워드 처리 (리스트를 문자열로 변환)
        if context["search_keywords"] and isinstance(context["search_keywords"], list):
            context["search_keywords"] = ", ".join(context["search_keywords"])

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
            "newsletter_title": data.get(
                "newsletter_topic", "주간 산업 동향 뉴스 클리핑"
            ),
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

    logger.info(f"Saved newsletter data with embedded config to {output_path}")


def process_compact_newsletter_data(newsletter_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    기존 뉴스레터 데이터를 간결한 버전으로 변환합니다.

    Args:
        newsletter_data: 원본 뉴스레터 데이터

    Returns:
        Dict: 간결한 버전용으로 변환된 데이터
    """
    logger.debug(
        f"process_compact_newsletter_data 입력 키들: {list(newsletter_data.keys())}"
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
    logger.debug(f"상위 기사를 찾았습니다: {len(top_articles)}개")

    if not top_articles and "sections" in newsletter_data:
        # top_articles가 없으면 각 섹션에서 첫 번째 기사들을 선택
        logger.debug("상위 기사가 없어 섹션에서 추출합니다")
        top_articles = extract_top_articles_from_sections(newsletter_data["sections"])

    # 상위 3개로 제한하고 요약 추가
    compact_data["top_articles"] = prepare_top_articles_for_compact(top_articles[:3])

    # Check if grouped_sections already exist in the input data
    if "grouped_sections" in newsletter_data:
        logger.debug(
            f"기존 그룹화된 섹션을 사용합니다: {len(newsletter_data['grouped_sections'])}개"
        )
        compact_data["grouped_sections"] = newsletter_data["grouped_sections"]
    else:
        logger.debug("섹션에서 그룹화된 섹션을 생성합니다")
        # 나머지 기사들을 그룹별로 정리
        compact_data["grouped_sections"] = prepare_grouped_sections_for_compact(
            newsletter_data.get("sections", []),
            top_articles[:3],  # 이미 선택된 상위 기사들 제외
        )

    # 용어 설명 처리 (최대 3개까지만)
    if "definitions" in newsletter_data:
        logger.debug(f"기존 정의를 사용합니다: {len(newsletter_data['definitions'])}개")
        compact_data["definitions"] = newsletter_data["definitions"]
    else:
        logger.debug("섹션에서 정의를 생성합니다")
        compact_data["definitions"] = extract_key_definitions_for_compact(
            newsletter_data.get("sections", [])
        )

    # 생각해볼 거리 처리
    food_for_thought = newsletter_data.get("food_for_thought")
    if food_for_thought:
        if isinstance(food_for_thought, dict):
            # 딕셔너리 형태 그대로 유지 (템플릿에서 .message로 접근)
            compact_data["food_for_thought"] = food_for_thought
        else:
            # 문자열인 경우 딕셔너리로 변환
            compact_data["food_for_thought"] = {"message": str(food_for_thought)}

    return compact_data


def extract_top_articles_from_sections(
    sections: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    각 섹션에서 첫 번째 뉴스 링크를 추출하여 상위 기사로 만듭니다.
    중복 URL 제거 로직 포함.
    """
    top_articles = []
    seen_urls = set()  # 중복 URL 추적

    for section in sections[:3]:  # 최대 3개 섹션에서
        news_links = section.get("news_links", [])
        if news_links:
            # 섹션의 모든 기사를 확인하여 중복되지 않은 첫 번째 기사 선택
            for article in news_links:
                article_url = article.get("url", "#")

                # URL이 이미 선택되었거나 유효하지 않으면 건너뛰기
                if article_url in seen_urls or article_url == "#" or not article_url:
                    continue

                # 요약 텍스트 생성 (섹션의 첫 번째 요약 문단 사용)
                summary_paragraphs = section.get("summary_paragraphs", [])
                snippet = summary_paragraphs[0] if summary_paragraphs else ""

                top_article = {
                    "title": article.get("title", ""),
                    "url": article_url,
                    "snippet": snippet[:150] + "..." if len(snippet) > 150 else snippet,
                    "source_and_date": article.get("source_and_date", ""),
                }

                top_articles.append(top_article)
                seen_urls.add(article_url)
                break  # 해당 섹션에서 하나만 선택하고 다음 섹션으로

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


def load_newsletter_settings(config_file: str = "config.yml") -> Dict[str, Any]:
    """
    설정 파일에서 뉴스레터 설정을 로드합니다.

    Args:
        config_file: 설정 파일 경로 (호환성을 위해 유지)

    Returns:
        Dict[str, Any]: 뉴스레터 설정 딕셔너리
    """
    from .centralized_settings import get_settings
    
    settings = get_settings()
    
    # 기본 설정 (CentralizedSettings 기반)
    default_settings = {
        "newsletter_title": "주간 산업 동향 뉴스 클리핑",
        "tagline": "이번 주, 주요 산업 동향을 미리 만나보세요.",
        "publisher_name": "Your Company",
        "company_name": "Your Company",
        "company_tagline": "",
        "editor_name": "",
        "editor_title": "편집자",
        "editor_email": settings.email_sender or "",
        "footer_disclaimer": "이 뉴스레터는 정보 제공을 목적으로 하며, 내용의 정확성을 보장하지 않습니다.",
        "footer_contact": "",
    }

    try:
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            newsletter_settings = config_data.get("newsletter_settings", {})
            # 기본 설정과 병합
            default_settings.update(newsletter_settings)
    except Exception as e:
        logger.warning(
            f"Could not load newsletter settings from {config_file}: {e}"
        )

    return default_settings


# Example usage (for testing purposes):
if __name__ == "__main__":
    # This is a simplified example. In a real scenario,
    # 'data' would be populated by other parts of your application (e.g., data collection, summarization).
    example_data = {
        "newsletter_topic": "AI 신약 개발, 디지털 치료제, 세포 유전자 치료제, 마이크로바이옴, 합성생물학",
        "generation_date": datetime.now().strftime("%Y-%m-%d"),
        "generation_timestamp": datetime.now().strftime("%H:%M:%S"),
        "recipient_greeting": "안녕하세요, 전략프로젝트팀의 젊은 팀원과 수석전문위원 여러분.",
        "introduction_message": "이번 주 주요 산업 동향과 기술 발전 현황을 정리하여 보내드립니다. 함께 살펴보시고 R&D 전략 수립에 참고하시면 좋겠습니다.",
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
        logger.error(f"Template directory not found at {template_directory}")
    elif not os.path.exists(os.path.join(template_directory, template_file)):
        logger.error(
            f"Template file not found at {os.path.join(template_directory, template_file)}"
        )
    else:
        logger.info(f"Template directory: {template_directory}")
        logger.info(f"Template file: {template_file}")
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
            logger.info(f"Test newsletter saved to {output_filename}")

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
            logger.error(f"An error occurred during test composition: {e}")
