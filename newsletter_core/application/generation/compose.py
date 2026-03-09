# flake8: noqa
# Placeholder for newsletter composition logic
import json
import os
from datetime import datetime
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from newsletter.date_utils import extract_source_and_date, format_date_for_display
from newsletter.utils.logger import get_logger

from .compose_context import build_render_context, load_newsletter_settings
from .compose_inputs import (
    NewsletterConfig,
    normalize_compose_input,
    resolve_style_config,
)
from .compose_sections import (
    add_emoji_to_section_title,
    create_grouped_sections,
    extract_and_prepare_top_articles,
    extract_definitions,
    extract_food_for_thought,
    extract_key_definitions_for_compact,
    extract_top_articles_from_sections,
    format_compact_source_date,
    prepare_grouped_sections_for_compact,
    prepare_top_articles_for_compact,
)

# 로거 초기화
logger = get_logger()


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
    context = build_render_context(
        data=data,
        config=config,
        top_articles=top_articles,
        grouped_sections=grouped_sections,
        definitions=definitions,
        food_for_thought=food_for_thought,
    )
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
        template = env.get_template(template_name)  # 여기서 TemplateNotFound 예외 발생 가능

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
        template = env.get_template(template_name)  # 여기서 TemplateNotFound 예외 발생 가능

        # 간단한 컨텍스트로 렌더링
        context = {
            "newsletter_title": data.get("newsletter_topic", "주간 산업 동향 뉴스 클리핑"),
            "tagline": "이번 주, 주요 산업 동향을 미리 만나보세요.",
            "generation_date": data.get(
                "generation_date", datetime.now().strftime("%Y-%m-%d")
            ),
            "definitions": data.get("definitions", []),
        }
        return template.render(context)

    return compose_newsletter(data, template_dir, "compact")


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
        logger.debug(f"기존 그룹화된 섹션을 사용합니다: {len(newsletter_data['grouped_sections'])}개")
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
