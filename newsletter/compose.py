# Placeholder for newsletter composition logic
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
from datetime import datetime
from typing import Any, Dict, List
from .date_utils import (
    format_date_for_display,
    extract_source_and_date,
    standardize_date,
)


def compose_newsletter_html(data, template_dir: str, template_name: str) -> str:
    """
    Generates HTML newsletter content from structured data using a Jinja2 template.

    Args:
        data: Either a dictionary containing all newsletter data, or a list of article summaries.
             If a dict is provided, expected keys include:
             - 'newsletter_topic': The main topic of the newsletter.
             - 'generation_date': The date the newsletter is generated.
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
    # 리스트로 제공된 경우, 딕셔너리 형태로 변환
    if isinstance(data, list):
        # 기사 목록을 sections 형태로 변환
        article_sections = []
        for article in data:
            title = article.get("title", "No Title")
            url = article.get("url", "#")
            # summary_text 또는 content 필드에서 내용 가져오기
            content = article.get("summary_text", article.get("content", "No Content"))
            source = article.get("source", "Unknown Source")
            date = article.get("date", "")

            # 소스에 날짜 정보가 포함되어 있는지 확인하고 분리
            if not date and "," in source:
                extracted_source, extracted_date = extract_source_and_date(source)
                if extracted_date:
                    source = extracted_source
                    date = extracted_date

            # 날짜 형식 포맷팅 (표시용)
            formatted_date = format_date_for_display(date_str=date)
            source_and_date = source
            if formatted_date:
                source_and_date = f"{source}, {formatted_date}"

            article_sections.append(
                {
                    "title": title,
                    "summary_paragraphs": [content],
                    "news_links": [
                        {
                            "title": title,
                            "url": url,
                            "source_and_date": source_and_date,
                        }
                    ],
                }
            )

        # 데이터 재구성
        newsletter_data = {
            "newsletter_topic": "뉴스 요약",
            "sections": article_sections,
        }
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

    # 환경 변수 GENERATION_DATE 확인 또는 현재 날짜 사용
    if isinstance(data, list):
        generation_date = os.environ.get(
            "GENERATION_DATE", datetime.now().strftime("%Y-%m-%d")
        )
    else:
        # 원래 딕셔너리인 경우 원래 로직 유지
        generation_date = data.get(
            "generation_date", datetime.now().strftime("%Y-%m-%d")
        )

    # Prepare a comprehensive context for rendering
    context = {
        "newsletter_topic": newsletter_data.get("newsletter_topic", "주간 산업 동향"),
        "generation_date": generation_date,
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

    html_content = template.render(context)
    return html_content


# Example usage (for testing purposes):
if __name__ == "__main__":
    # This is a simplified example. In a real scenario,
    # 'data' would be populated by other parts of your application (e.g., data collection, summarization).
    example_data = {
        "newsletter_topic": "AI 신약 개발, 디지털 치료제, 세포 유전자 치료제, 마이크로바이옴, 합성생물학",
        "generation_date": datetime.now().strftime("%Y-%m-%d"),
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
            html_output = compose_newsletter_html(
                example_data, template_directory, template_file
            )
            output_filename = os.path.join(
                project_root,
                "output",
                f"composed_newsletter_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            )
            os.makedirs(os.path.join(project_root, "output"), exist_ok=True)
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(html_output)
            print(f"Test newsletter saved to {output_filename}")
        except Exception as e:
            print(f"An error occurred during test composition: {e}")
