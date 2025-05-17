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


def compose_newsletter_html(data, template_dir: str, template_name: str) -> str:
    """
    Generates HTML newsletter content from structured data using a Jinja2 template.

    Args:
        data: Either a dictionary containing all newsletter data, or a list of article summaries.
             If a dict is provided, expected keys include:
             - 'newsletter_topic': The main topic of the newsletter.
             - 'generation_date': The date the newsletter is generated.
             - 'generation_timestamp': The timestamp when the newsletter is generated.
             - 'recipient_greeting': A greeting message for the recipient.
             - 'introduction_message': An introductory message for the newsletter.
             - 'sections': A list of sections, where each section is a dict with:
                 - 'title': The title of the section.
                 - 'summary_paragraphs': A list of paragraphs for the summary.
                 - 'definitions': (Optional) A list of term-definition pairs.
                 - 'news_links': (Optional) A list of news links with title, url, and source.
             - 'food_for_thought': (Optional) A dict with 'quote', 'author', and 'message'.
             - 'closing_message': (Optional) A closing message.
             - 'editor_signature': (Optional) The editor's signature.
             - 'company_name': (Optional) The name of the company.
             If a list is provided, it should contain article summary dictionaries, each with:
             - 'title': Article title
             - 'url': Article URL
             - 'summary_text' or 'content': Article summary content
        template_dir (str): The directory where the template file is located.
        template_name (str): The name of the template file.

    Returns:
        str: The rendered HTML content of the newsletter.
    """
    # First extract any test configuration if present
    if isinstance(data, dict):
        data, test_config = extract_test_config(data)

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
    else:
        # 이미 딕셔너리 형태로 제공된 경우
        newsletter_data = data

        # 뉴스 링크의 날짜 형식 포맷팅
        if "sections" in newsletter_data:
            for section in newsletter_data["sections"]:
                if "news_links" in section:
                    for link in section["news_links"]:
                        if "source_and_date" in link:
                            source, date_str = extract_source_and_date(
                                link["source_and_date"]
                            )
                            if date_str:
                                formatted_date = format_date_for_display(
                                    date_str=date_str
                                )
                                if formatted_date:
                                    link["source_and_date"] = (
                                        f"{source}, {formatted_date}"
                                    )

    print(
        f"Composing newsletter for topic: {newsletter_data.get('newsletter_topic', 'N/A')}..."
    )

    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(template_name)

    # 현재 날짜와 시간 가져오기
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")

    # 환경 변수 확인 또는 현재 날짜와 시간 사용
    generation_date = os.environ.get("GENERATION_DATE", current_date)
    generation_timestamp = os.environ.get("GENERATION_TIMESTAMP", current_time)

    # 기존 로직을 아래 코드로 대체
    if isinstance(data, dict):
        # 딕셔너리 형태로 제공된 경우 해당 값 사용, 없으면 환경 변수나 현재 값 사용
        generation_date = data.get("generation_date", generation_date)
        generation_timestamp = data.get("generation_timestamp", generation_timestamp)

    # Prepare a comprehensive context for rendering
    context = {
        "newsletter_topic": newsletter_data.get("newsletter_topic", "주간 산업 동향"),
        "generation_date": generation_date,
        "generation_timestamp": generation_timestamp,  # Now always included
        "recipient_greeting": newsletter_data.get("recipient_greeting", "안녕하세요,"),
        "introduction_message": newsletter_data.get(
            "introduction_message", "지난 한 주간의 주요 산업 동향을 정리해 드립니다."
        ),
        "sections": newsletter_data.get("sections", []),
        "food_for_thought": newsletter_data.get("food_for_thought"),  # Can be None
        "closing_message": newsletter_data.get(
            "closing_message", "다음 주에 더 유익한 정보로 찾아뵙겠습니다. 감사합니다."
        ),
        "editor_signature": newsletter_data.get("editor_signature", "편집자 드림"),
        "company_name": newsletter_data.get("company_name", "Your Newsletter Co."),
    }

    # 검색 키워드 추가
    if "search_keywords" in newsletter_data and newsletter_data["search_keywords"]:
        # search_keywords가 리스트인 경우 문자열로 변환
        if isinstance(newsletter_data["search_keywords"], list):
            context["search_keywords"] = ", ".join(newsletter_data["search_keywords"])
        else:
            context["search_keywords"] = newsletter_data["search_keywords"]

    html_content = template.render(context)
    return html_content


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
