"""
Newsletter Generator - LangChain Chains
이 모듈은 뉴스레터 생성을 위한 LangChain 체인을 정의합니다.
"""

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain, SequentialChain
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from . import config
from langchain_core.messages import SystemMessage, HumanMessage
import os
import datetime
import json
from jinja2 import Template
from newsletter.sources import NewsSourceManager
from . import tools  # 추가: tools 모듈 가져오기
from .template_manager import TemplateManager
from jinja2 import Environment, FileSystemLoader
from .compose import (
    prepare_grouped_sections_for_compact,
    extract_key_definitions_for_compact,
    compose_compact_newsletter_html,
    compose_newsletter,
)


# HTML 템플릿 파일 로딩
def load_html_template():
    """HTML 템플릿 파일을 로드합니다."""
    template_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "templates",
        "newsletter_template.html",
    )
    try:
        with open(template_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"템플릿 파일 로딩 중 오류 발생: {e}")
        # 기본 템플릿 반환
        return """
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <title>오늘의 뉴스레터</title>
        </head>
        <body>
            <h1>오늘의 뉴스레터</h1>
            <!-- 뉴스레터 내용이 여기에 들어갑니다 -->
        </body>
        </html>
        """


# HTML 템플릿 로드
HTML_TEMPLATE = load_html_template()

# 디버깅을 위해 템플릿을 파일에 저장
try:
    with open(
        f"template_debug_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(HTML_TEMPLATE)
except Exception as e:
    print(f"디버그 파일 작성 중 오류: {e}")

# 분류 시스템 프롬프트
CATEGORIZATION_PROMPT = """
당신은 뉴스들을 분석하고 분류하는 전문 편집자입니다.

독자 배경: 독자들은 한국 첨단산업의 R&D 전략기획단 소속 분야별 전문위원들입니다. 이들은 매주 특정 산업 주제에 대한 기술 동향과 주요 뉴스를 받아보기를 원합니다.

다음 키워드에 관련된 뉴스 기사들을 분석하여, 의미있는 카테고리로 분류해주세요:
{keywords}

뉴스 기사 목록:
{formatted_articles}

뉴스 기사들을 분석하여 내용에 따라 여러 카테고리로 분류하세요. 예를 들어, "전기차 시장 동향", "하이브리드차 동향", "배터리 기술 발전" 등처럼 의미 있는 카테고리로 나누어야 합니다. 각 카테고리는 적절한 제목을 가져야 합니다.

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

하나의 기사는 여러 카테고리에 포함될 수 있지만, 모든 기사가 최소 하나의 카테고리에는 포함되어야 합니다.
각 카테고리 제목은, 독자가 어떤 내용인지 한눈에 알 수 있도록 명확하고 구체적으로 작성해주세요.
"""

# 요약 시스템 프롬프트
SUMMARIZATION_PROMPT = """
당신은 뉴스들을 분석하고 요약하여 "주간 산업 동향 뉴스 클리핑"을 작성하는 전문 편집자입니다.

독자 배경: 독자들은 한국 첨단산업의 R&D 전략기획단 소속 분야별 전문위원들입니다. 이들은 매주 특정 산업 주제에 대한 기술 동향과 주요 뉴스를 받아보기를 원합니다.

다음은 "{category_title}" 카테고리에 해당하는 뉴스 기사들입니다:
{category_articles}

위 기사들을 종합적으로 분석하여 다음 정보를 포함한 요약을 JSON 형식으로 만들어주세요:

1. summary_paragraphs: 해당 카테고리의 주요 내용을 1개의 단락으로 요약 (각 단락은 배열의 항목)
   - 요약문은 객관적이고 분석적이며, 전체 기사들의 맥락을 포괄해야 합니다.
   - 정중한 존댓말을 사용합니다.

2. definitions: 해당 카테고리에서 등장하는 중요 용어나 개념 설명 (0-2개)
   - 신입직원이 이해하기 어려울 수 있는 전문 용어나 개념 중 가장 핵심적인 것만 선정
   - 다른 카테고리에서 이미 설명된 용어는 피하고, 해당 카테고리 특유의 용어를 우선 선정
   - 꼭 필요한 경우가 아니면 1-2개로 제한하며, 명확한 용어가 없다면 0개도 가능

3. news_links: 원본 기사 링크 정보
   - 각 카테고리별로 관련 뉴스 기사들의 원문 링크를 제목, 출처, 시간 정보와 함께 제공합니다.

출력 형식:
```json
{{
  "summary_paragraphs": ["첫 번째 단락", "두 번째 단락", "..."],
  "definitions": [
    {{"term": "용어1", "explanation": "용어1에 대한 설명"}},
    {{"term": "용어2", "explanation": "용어2에 대한 설명"}}
  ],
  "news_links": [
    {{"title": "기사 제목", "url": "기사 URL", "source_and_date": "출처 및 날짜"}}
  ]
}}
```
"""

# 종합 구성 프롬프트
COMPOSITION_PROMPT = """
당신은 뉴스들을 분석하고 요약하여, HTML 형식으로 "주간 산업 동향 뉴스 클리핑"을 작성하는 전문 편집자입니다.

독자 배경: 독자들은 한국 첨단산업의 R&D 전략기획단 소속 분야별 전문위원들입니다. 이들은 매주 특정 산업 주제에 대한 기술 동향과 주요 뉴스를 받아보기를 원합니다.

이미 각 카테고리별로 상세 요약이 완료되었습니다. 이제 뉴스레터의 전체 구성을 완성해야 합니다.

주제 키워드: {keywords}
카테고리 요약:
{category_summaries}

다음 정보를 포함한 뉴스레터 구성 정보를 JSON 형식으로 반환해주세요:

```json
{{
  "newsletter_topic": "뉴스레터 주제",
  "generation_date": "{current_date}",
  "recipient_greeting": "독자들을 위한 인사말",
  "introduction_message": "뉴스레터 소개 문구",
  "food_for_thought": {{
    "quote": "관련 명언 (선택사항)",
    "author": "명언 출처 (선택사항)",
    "message": "독자들에게 생각해볼 만한 질문이나 제안"
  }},
  "closing_message": "마무리 문구",
  "editor_signature": "편집자 서명",
  "company_name": "회사명"
}}
```

참고:
- generation_date는 {current_date} 형식으로 유지해주세요.
- newsletter_topic은 입력된 '키워드'를 뉴스레터의 전체 주제로 설정하고, 제목과 도입부에 반영합니다.
- 각 항목은 한국어로 작성하며, 정중한 존댓말을 사용합니다.
- introduction_message는 전체 뉴스레터의 주제와 주요 내용을 간략히 소개합니다.
- food_for_thought는 전체 뉴스 내용을 바탕으로 독자들에게 생각해볼 만한 질문이나 영감을 줄 수 있는 메시지입니다.
- closing_message는 뉴스레터를 마무리하는 문구입니다.
"""

# 하위 호환성을 위한 SYSTEM_PROMPT
# 이전 버전의 코드에서 참조하던 SYSTEM_PROMPT 변수를 제공합니다.
SYSTEM_PROMPT = f"""
Role: 당신은 뉴스들을 분석하고 요약하여, HTML 형식으로 "주간 산업 동향 뉴스 클리핑"을 작성하는 전문 편집자입니다.

Context: 독자들은 한국 첨단산업의 R&D 전략기획단 소속으로, 분야별 전문위원으로 구성되어 있습니다. 이들은 매주 특정 산업 주제에 대한 기술 동향과 주요 뉴스를 받아보기를 원합니다.

Input:
1.  하나 이상의 '키워드' (예: "친환경 자동차", "AI 반도체"). 이 키워드는 뉴스레터의 주된 주제가 됩니다.
2.  여러 '뉴스 기사' 목록. 각 기사는 제목, URL, 본문 내용을 포함합니다.

Output Requirements:
-   **HTML 형식**: 최종 결과물은 다른 설명 없이 순수한 HTML 코드여야 합니다. API로 직접 전달될 예정입니다. 반드시 아래 제공된 HTML 템플릿을 사용해야 합니다.
-   **언어**: 한국어, 정중한 존댓말을 사용합니다.
-   **구조**: 뉴스레터는 아래 제공된 HTML 템플릿을 기반으로 생성해야 합니다.

### 제공되는 HTML 템플릿:
```html
{HTML_TEMPLATE}
```

주의: SYSTEM_PROMPT는 하위 호환성을 위해 유지되었습니다. 새로운 코드에서는 CATEGORIZATION_PROMPT, SUMMARIZATION_PROMPT, COMPOSITION_PROMPT를 사용하세요.
"""


def get_llm(temperature=0.3, callbacks=None):
    """구글 Gemini Pro 모델 인스턴스를 생성합니다."""
    if callbacks is None:
        callbacks = []
    if os.environ.get("ENABLE_COST_TRACKING"):
        try:
            from .cost_tracking import get_tracking_callbacks

            callbacks += get_tracking_callbacks()
        except Exception:
            pass
    if not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")

    # gRPC 메타데이터 관련 옵션 설정
    transport = "rest"  # 기본적으로 REST API 사용 (gRPC 대신)

    return ChatGoogleGenerativeAI(
        model="gemini-2.5-pro-preview-03-25",  # 최신 Gemini 2.5 Pro 모델 사용
        google_api_key=config.GEMINI_API_KEY,
        temperature=temperature,
        transport=transport,
        callbacks=callbacks,
        convert_system_message_to_human=False,
        timeout=60,  # 타임아웃 60초
        max_retries=2,  # 최대 2회 재시도
        disable_streaming=False,  # 스트리밍 활성화 (streaming=True와 같음)
    )


# 기사 목록을 텍스트로 변환하는 함수
def format_articles(data):
    """
    기사 목록을 텍스트 형식으로 변환합니다.

    Args:
        data: 기사 데이터를 포함하는 딕셔너리

    Returns:
        str: 포맷팅된 기사 텍스트
    """
    articles = data.get("articles", [])
    if not articles:
        return "기사 데이터를 찾을 수 없습니다."

    formatted_articles = []
    for i, article in enumerate(articles):
        title = article.get("title", "제목 없음")
        url = article.get("url", "#")
        content = article.get("content", "내용 없음")
        source = article.get("source", "출처 없음")
        date = article.get("date", "날짜 없음")

        formatted_articles.append(
            f"기사 #{i+1}:\n제목: {title}\nURL: {url}\n출처: {source}\n날짜: {date}\n내용:\n{content}\n"
        )

    return "\n---\n".join(formatted_articles)


# 1. 분류 체인 생성 함수 (compact 옵션 추가)
def create_categorization_chain(is_compact=False):
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
                prompt = CATEGORIZATION_PROMPT.format(
                    keywords=keywords,
                    formatted_articles=formatted_articles,
                )

            # 메시지를 HumanMessage로 변환 (Gemini는 시스템 메시지 지원이 불안정함)
            return [HumanMessage(content=prompt)]
        except Exception as e:
            print(f"카테고리 메시지 생성 중 오류: {e}")
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
            print(
                f"카테고리 분류 결과: {json.dumps(result, ensure_ascii=False, indent=2)}"
            )
            return result
        except Exception as e:
            print(f"JSON 파싱 오류: {e}")
            print(f"원본 텍스트: {text}")
            # 기본 구조 반환
            if is_compact:
                return {
                    "categories": [
                        {"title": "주요 동향", "article_indices": list(range(1, 11))}
                    ]
                }
            else:
                return {
                    "categories": [
                        {"title": "기타", "article_indices": [1, 2, 3, 4, 5]}
                    ]
                }

    return chain | RunnableLambda(parse_json_response)


# 2. 카테고리별 요약 체인 생성 함수 (compact 옵션 추가)
def create_summarization_chain(is_compact=False):
    llm = get_llm(temperature=0.3)
    parser = JsonOutputParser()

    # compact 버전용 간소화된 프롬프트
    compact_summary_prompt = """당신은 뉴스를 간결하게 요약하는 전문 편집자입니다.

다음은 "{category_title}" 카테고리에 해당하는 뉴스 기사들입니다:
{category_articles}

위 기사들을 종합적으로 분석하여 다음 정보를 포함한 간단한 요약을 JSON 형식으로 만들어주세요:

1. intro: 해당 카테고리의 주요 내용을 1-2문장으로 간단히 요약
2. definitions: 중요 용어 2-3개만 선정하여 간단히 설명
3. news_links: 원본 기사 링크 정보

출력 형식:
```json
{{
  "intro": "카테고리 소개 문구",
  "definitions": [
    {{"term": "용어1", "explanation": "용어1에 대한 간단한 설명"}},
    {{"term": "용어2", "explanation": "용어2에 대한 간단한 설명"}}
  ],
  "news_links": [
    {{"title": "기사 제목", "url": "기사 URL", "source_and_date": "출처 및 날짜"}}
  ]
}}
```"""

    def process_categories(data):
        categories_data = data["categories_data"]
        articles_data = data["articles_data"]
        results = []

        print(f"처리할 카테고리 수: {len(categories_data.get('categories', []))}")

        for category in categories_data.get("categories", []):
            # 해당 카테고리에 속한 기사들 추출
            category_articles = []
            for idx in category.get("article_indices", []):
                if 0 <= idx - 1 < len(articles_data.get("articles", [])):
                    category_articles.append(articles_data["articles"][idx - 1])

            print(
                f"카테고리 '{category.get('title', '제목 없음')}' - 관련 기사 수: {len(category_articles)}"
            )

            # 카테고리 기사들을 포맷팅
            formatted_articles = "\n---\n".join(
                [
                    f"기사 #{i+1}:\n제목: {article.get('title', '제목 없음')}\n"
                    f"URL: {article.get('url', '#')}\n"
                    f"출처: {article.get('source', '출처 없음')}\n"
                    f"날짜: {article.get('date', '날짜 없음')}\n"
                    f"내용:\n{article.get('content', article.get('snippet', '내용 없음'))}"
                    for i, article in enumerate(category_articles)
                ]
            )

            # 중첩된 중괄호 이스케이프 처리
            formatted_articles = formatted_articles.replace("{", "{{").replace(
                "}", "}}"
            )
            category_title = category.get("title", "제목 없음")

            # compact 버전인지에 따라 프롬프트 선택
            if is_compact:
                prompt_content = compact_summary_prompt.format(
                    category_title=category_title,
                    category_articles=formatted_articles,
                )
            else:
                # 요약 프롬프트 생성
                prompt_content = SUMMARIZATION_PROMPT.format(
                    category_title=category_title,
                    category_articles=formatted_articles,
                )

            # LLM에 요청
            messages = [HumanMessage(content=prompt_content)]
            summary_result = llm.invoke(messages)
            summary_text = summary_result.content

            try:
                # JSON 추출
                import re

                json_match = re.search(
                    r"```(?:json)?\s*(.*?)```", summary_text, re.DOTALL
                )
                if json_match:
                    json_str = json_match.group(1).strip()
                else:
                    # compact 버전에서는 중괄호로 감싸진 JSON도 찾기
                    if is_compact:
                        json_match = re.search(r"\{.*\}", summary_text, re.DOTALL)
                        if json_match:
                            json_str = json_match.group()
                        else:
                            json_str = summary_text.strip()
                    else:
                        json_str = summary_text.strip()

                summary_json = json.loads(json_str)

                # 카테고리 제목 추가
                summary_json["title"] = category.get("title", "제목 없음")

                # compact 버전에서는 간소화된 형태로 변환
                if is_compact:
                    # intro, definitions, news_links를 기본 형태로 변환
                    compact_result = {
                        "title": summary_json["title"],
                        "intro": summary_json.get("intro", ""),
                        "definitions": summary_json.get("definitions", []),
                        "articles": [],
                    }

                    # definitions가 비어있다면 기본 definitions 생성
                    if not compact_result["definitions"]:
                        category_title = summary_json["title"]
                        # 카테고리 제목을 바탕으로 기본 definition 생성
                        if "자율주행" in category_title:
                            compact_result["definitions"] = [
                                {
                                    "term": "자율주행",
                                    "explanation": "운전자의 개입 없이 차량이 스스로 주행하는 기술로, 레벨 0부터 5까지 단계별로 구분됩니다.",
                                }
                            ]
                        elif any(
                            keyword in category_title for keyword in ["기술", "개발"]
                        ):
                            compact_result["definitions"] = [
                                {
                                    "term": "R&D",
                                    "explanation": "연구개발(Research and Development)의 줄임말로, 새로운 기술이나 제품을 개발하는 활동입니다.",
                                }
                            ]
                        elif any(
                            keyword in category_title for keyword in ["정책", "규제"]
                        ):
                            compact_result["definitions"] = [
                                {
                                    "term": "산업정책",
                                    "explanation": "정부가 특정 산업의 발전을 위해 수립하는 정책으로, 규제 완화, 지원책 등을 포함합니다.",
                                }
                            ]
                        else:
                            # 일반적인 기본 definition
                            compact_result["definitions"] = [
                                {
                                    "term": "혁신기술",
                                    "explanation": "기존 기술을 크게 개선하거나 완전히 새로운 방식의 기술로, 산업과 사회에 큰 변화를 가져올 수 있는 기술입니다.",
                                }
                            ]

                    # news_links를 articles로 변환
                    for link in summary_json.get("news_links", []):
                        compact_result["articles"].append(
                            {
                                "title": link.get("title", ""),
                                "url": link.get("url", "#"),
                                "source_and_date": link.get("source_and_date", ""),
                            }
                        )

                    results.append(compact_result)
                else:
                    results.append(summary_json)

            except Exception as e:
                print(
                    f"카테고리 '{category.get('title', '제목 없음')}' 요약 파싱 오류: {e}"
                )
                # 오류 발생 시 기본 구조 제공
                if is_compact:
                    # 파싱 오류 시에도 기본 definitions 제공
                    category_title = category.get("title", "제목 없음")
                    fallback_definitions = []

                    if "자율주행" in category_title:
                        fallback_definitions = [
                            {
                                "term": "자율주행",
                                "explanation": "운전자의 개입 없이 차량이 스스로 주행하는 기술로, 레벨 0부터 5까지 단계별로 구분됩니다.",
                            },
                            {
                                "term": "레벨4",
                                "explanation": "운전자가 없어도 특정 조건에서 완전 자율주행이 가능한 수준입니다.",
                            },
                        ]
                    elif any(keyword in category_title for keyword in ["기술", "개발"]):
                        fallback_definitions = [
                            {
                                "term": "R&D",
                                "explanation": "연구개발(Research and Development)의 줄임말로, 새로운 기술이나 제품을 개발하는 활동입니다.",
                            }
                        ]
                    elif any(keyword in category_title for keyword in ["정책", "규제"]):
                        fallback_definitions = [
                            {
                                "term": "산업정책",
                                "explanation": "정부가 특정 산업의 발전을 위해 수립하는 정책으로, 규제 완화, 지원책 등을 포함합니다.",
                            }
                        ]
                    else:
                        fallback_definitions = [
                            {
                                "term": "혁신기술",
                                "explanation": "기존 기술을 크게 개선하거나 완전히 새로운 방식의 기술로, 산업과 사회에 큰 변화를 가져올 수 있는 기술입니다.",
                            }
                        ]

                    results.append(
                        {
                            "title": category_title,
                            "intro": f"{category_title}에 대한 주요 동향입니다.",
                            "definitions": fallback_definitions,
                            "articles": [
                                {
                                    "title": article.get("title", ""),
                                    "url": article.get("url", "#"),
                                    "source_and_date": f"{article.get('source', 'Unknown')} · {article.get('date', 'Unknown date')}",
                                }
                                for article in category_articles
                            ],
                        }
                    )
                else:
                    results.append(
                        {
                            "title": category.get("title", "제목 없음"),
                            "summary_paragraphs": [
                                "(요약 생성 중 오류가 발생했습니다)"
                            ],
                            "definitions": [],
                            "news_links": [],
                        }
                    )

        # compact 버전에서는 추가 처리
        if is_compact:
            all_definitions = []
            for result in results:
                all_definitions.extend(result.get("definitions", []))

            return {
                "sections": results,
                "all_definitions": all_definitions[:3],  # 최대 3개까지만
            }
        else:
            return {"sections": results}

    return RunnableLambda(process_categories)


# 3. 종합 구성 체인 생성 함수
def create_composition_chain():
    llm = get_llm(temperature=0.4)

    def create_composition_prompt(data):
        current_date = datetime.date.today().strftime("%Y-%m-%d")
        sections_data = json.dumps(data["sections"], ensure_ascii=False, indent=2)

        # JSON 데이터의 중괄호 이스케이프 처리
        sections_data = sections_data.replace("{", "{{").replace("}", "}}")

        keywords = data.get("keywords", "")

        prompt_content = COMPOSITION_PROMPT.format(
            keywords=keywords,
            category_summaries=sections_data,
            current_date=current_date,
        )

        return [HumanMessage(content=prompt_content)]

    # JSON 파싱 함수
    def parse_json_response(text):
        try:
            # JSON 부분만 추출
            import re

            json_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                json_str = text.strip()

            # JSON 파싱
            return json.loads(json_str)
        except Exception as e:
            print(f"종합 구성 JSON 파싱 오류: {e}")
            print(f"원본 텍스트: {text}")
            # 기본 구조 반환
            return {
                "newsletter_topic": "최신 산업 동향",
                "generation_date": datetime.date.today().strftime("%Y-%m-%d"),
                "recipient_greeting": "안녕하세요, 독자 여러분",
                "introduction_message": "이번 뉴스레터에서는 주요 산업 동향을 살펴봅니다.",
                "food_for_thought": {
                    "message": "산업의 변화에 어떻게 대응해 나갈지 생각해 보시기 바랍니다."
                },
                "closing_message": "다음 뉴스레터에서 다시 만나뵙겠습니다.",
                "editor_signature": "편집자 드림",
                "company_name": "Tech Insights",
            }

    # 체인 구성
    chain = (
        RunnableLambda(create_composition_prompt)
        | llm
        | StrOutputParser()
        | RunnableLambda(parse_json_response)
    )

    return chain


# 4. 템플릿 렌더링 체인 생성 함수
def create_rendering_chain():
    # 템플릿 매니저 초기화
    template_manager = TemplateManager()

    def render_with_template(data):
        # 뉴스레터 데이터와 섹션 데이터 병합
        combined_data = {**data["composition"], **data["sections_data"]}

        # 날짜 설정 (이미 composition에서 설정되어 있을 수 있음)
        if "generation_date" not in combined_data:
            combined_data["generation_date"] = datetime.date.today().strftime(
                "%Y-%m-%d"
            )

        # 키워드 처리 및 뉴스레터 주제 설정
        if "keywords" in data and data["keywords"]:
            # 키워드를 문자열로 변환 (템플릿 표시용)
            keywords = data["keywords"]
            domain = data.get("domain", "")

            # 검색 키워드 설정
            if isinstance(keywords, list):
                combined_data["search_keywords"] = ", ".join(keywords)
            else:
                combined_data["search_keywords"] = keywords

            # newsletter_topic 설정 로직
            if domain:
                # 1. 도메인이 있으면 도메인 사용
                combined_data["newsletter_topic"] = domain
            elif isinstance(keywords, list) and len(keywords) == 1:
                # 2. 단일 키워드는 그대로 사용
                combined_data["newsletter_topic"] = keywords[0]
            elif isinstance(keywords, list) and len(keywords) > 1:
                # 3. 여러 키워드의 공통 주제 추출
                common_theme = tools.extract_common_theme_from_keywords(keywords)
                combined_data["newsletter_topic"] = common_theme
            elif isinstance(keywords, str) and "," in keywords:
                # 4. 콤마로 구분된 여러 키워드
                common_theme = tools.extract_common_theme_from_keywords(keywords)
                combined_data["newsletter_topic"] = common_theme
            else:
                # 5. 기본값 - 단일 문자열 키워드
                combined_data["newsletter_topic"] = keywords

        # 기본 템플릿 설정 추가
        combined_data["company_name"] = template_manager.get(
            "company.name", "R&D 기획단"
        )
        combined_data["footer_disclaimer"] = template_manager.get(
            "footer.disclaimer",
            "이 뉴스레터는 정보 제공용으로만 사용되며, 투자 권유를 목적으로 하지 않습니다.",
        )
        combined_data["editor_signature"] = template_manager.get(
            "editor.signature", "편집자 드림"
        )

        # 새로 추가된 필드들 적용
        combined_data["copyright_year"] = template_manager.get(
            "company.copyright_year", datetime.date.today().strftime("%Y")
        )
        combined_data["company_tagline"] = template_manager.get("company.tagline", "")
        combined_data["footer_contact"] = template_manager.get(
            "footer.contact_info", ""
        )
        combined_data["editor_name"] = template_manager.get("editor.name", "")
        combined_data["editor_title"] = template_manager.get("editor.title", "")
        combined_data["editor_email"] = template_manager.get("editor.email", "")
        combined_data["title_prefix"] = template_manager.get(
            "header.title_prefix", "주간 산업 동향 뉴스 클리핑"
        )
        combined_data["greeting_prefix"] = template_manager.get(
            "header.greeting_prefix", "안녕하십니까, "
        )
        combined_data["audience_organization"] = template_manager.get(
            "audience.organization", ""
        )

        # 스타일 설정 적용
        combined_data["primary_color"] = template_manager.get(
            "style.primary_color", "#3498db"
        )
        combined_data["secondary_color"] = template_manager.get(
            "style.secondary_color", "#2c3e50"
        )
        combined_data["font_family"] = template_manager.get(
            "style.font_family", "Malgun Gothic, sans-serif"
        )

        # 인사말이 없는 경우 기본 인사말 설정
        if "recipient_greeting" not in combined_data or not combined_data.get(
            "recipient_greeting"
        ):
            audience_desc = template_manager.get(
                "audience.description", "귀하께서 여기 계시다니 영광입니다"
            )
            combined_data["recipient_greeting"] = (
                f"{combined_data.get('greeting_prefix', '안녕하십니까, ')} {combined_data.get('company_name')} {audience_desc}."
            )

        # Jinja2 템플릿 렌더링
        from jinja2 import Template

        template = Template(HTML_TEMPLATE)
        rendered_html = template.render(**combined_data)

        # 디버깅용 - 렌더링에 사용된 데이터 저장
        # try:
        #     debug_dir = os.path.join("output", "intermediate_processing")
        #     os.makedirs(debug_dir, exist_ok=True)
        #     with open(
        #         os.path.join(
        #             debug_dir,
        #             f"render_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        #         ),
        #         "w",
        #         encoding="utf-8",
        #     ) as f:
        #         json.dump(combined_data, f, ensure_ascii=False, indent=2)
        # except Exception as e:
        #     print(f"디버그 데이터 저장 중 오류: {e}")

        return rendered_html, combined_data

    return RunnableLambda(render_with_template)


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
        print(f"[DEBUG] manage_data_flow 호출됨. is_compact={is_compact}")
        try:
            # 데이터 유효성 검증
            if "articles" not in data:
                raise ValueError("입력 데이터에 'articles' 필드가 없습니다.")

            # 1. 분류 단계 실행
            if is_compact:
                print("Compact 1단계: 뉴스 카테고리 분류 중...")
            else:
                print("1단계: 뉴스 카테고리 분류 중...")
            categories_data = categorization_chain.invoke(data)

            # 2. 요약 단계 실행
            if is_compact:
                print("Compact 2단계: 카테고리별 요약 생성 중...")
            else:
                print("2단계: 카테고리별 요약 생성 중...")
            sections_data = summarization_chain.invoke(
                {"categories_data": categories_data, "articles_data": data}
            )

            if is_compact:
                # Compact 버전: 상위 3개 기사 선정 + 최종 데이터 구성
                print("Compact 3단계: 상위 기사 선정 중...")
                top_articles = []
                for i, article in enumerate(data["articles"][:3]):
                    top_article = {
                        "title": article.get("title", ""),
                        "url": article.get("url", "#"),
                        "snippet": (
                            article.get("snippet", "")[:200] + "..."
                            if len(article.get("snippet", "")) > 200
                            else article.get("snippet", "")
                        ),
                        "source_and_date": f"{article.get('source', 'Unknown')} · {article.get('date', 'Unknown date')}",
                    }
                    top_articles.append(top_article)

                # 생각해볼 거리 생성
                keywords = data.get("keywords", [])
                if isinstance(keywords, str):
                    keywords = [keywords]

                food_for_thought = f"{', '.join(keywords[:2])} 분야의 급속한 발전은 우리에게 어떤 새로운 기회와 도전을 제시할까요?"

                # compose.py의 함수들을 사용하여 올바른 데이터 구조 생성
                sections = sections_data.get("sections", [])

                print(f"[DEBUG] sections 개수: {len(sections)}")
                for i, section in enumerate(sections):
                    print(
                        f"[DEBUG] Section {i}: title='{section.get('title', 'NO_TITLE')}', news_links={len(section.get('news_links', []))}, articles={len(section.get('articles', []))}"
                    )
                    for j, link in enumerate(
                        section.get("news_links", [])[:2]
                    ):  # 처음 2개만 출력
                        print(f"[DEBUG]   Link {j}: url='{link.get('url', 'NO_URL')}'")
                    for j, article in enumerate(
                        section.get("articles", [])[:2]
                    ):  # 처음 2개만 출력
                        print(
                            f"[DEBUG]   Article {j}: url='{article.get('url', 'NO_URL')}'"
                        )

                print(f"[DEBUG] top_articles 개수: {len(top_articles)}")
                for i, article in enumerate(top_articles):
                    print(
                        f"[DEBUG] Top Article {i}: url='{article.get('url', 'NO_URL')}')"
                    )

                grouped_sections = prepare_grouped_sections_for_compact(
                    sections, top_articles[:3]
                )
                definitions = extract_key_definitions_for_compact(sections)

                # 템플릿 매니저로부터 메타데이터 가져오기
                template_manager = TemplateManager()

                # 키워드 및 주제 처리
                keywords = data.get("keywords", [])
                domain = data.get("domain", "")

                # 뉴스레터 주제 결정
                if domain:
                    newsletter_topic = domain
                elif isinstance(keywords, list) and len(keywords) == 1:
                    newsletter_topic = keywords[0]
                elif isinstance(keywords, list) and len(keywords) > 1:
                    newsletter_topic = tools.extract_common_theme_from_keywords(
                        keywords
                    )
                elif isinstance(keywords, str):
                    newsletter_topic = keywords
                else:
                    newsletter_topic = "최신 산업 동향"

                # 최종 데이터 구성
                result_data = {
                    "newsletter_topic": newsletter_topic,
                    "domain": domain,  # 도메인 정보 추가
                    "tagline": "이번 주, 주요 산업 동향을 미리 만나보세요.",
                    "generation_date": os.environ.get(
                        "GENERATION_DATE", datetime.datetime.now().strftime("%Y-%m-%d")
                    ),
                    "generation_timestamp": os.environ.get(
                        "GENERATION_TIMESTAMP",
                        datetime.datetime.now().strftime("%H:%M:%S"),
                    ),
                    "top_articles": top_articles,
                    "grouped_sections": grouped_sections,
                    "definitions": definitions,
                    "food_for_thought": food_for_thought,
                    # 템플릿 매니저에서 가져온 정보
                    "company_name": template_manager.get(
                        "company.name", "산업통상자원 R&D 전략기획단"
                    ),
                    "publisher_name": template_manager.get(
                        "company.name", "산업통상자원 R&D 전략기획단"
                    ),
                    "copyright_year": template_manager.get(
                        "company.copyright_year", datetime.date.today().strftime("%Y")
                    ),
                    "company_tagline": template_manager.get(
                        "company.tagline", "최신 기술 동향을 한눈에"
                    ),
                    "footer_contact": template_manager.get(
                        "footer.contact_info", "문의사항: hjjung2@osp.re.kr"
                    ),
                    "editor_name": template_manager.get("editor.name", "Google Gemini"),
                    "editor_email": template_manager.get(
                        "editor.email", "hjjung2@osp.re.kr"
                    ),
                    "editor_title": template_manager.get("editor.title", "편집자"),
                    "footer_disclaimer": template_manager.get(
                        "footer.disclaimer",
                        "이 뉴스레터는 정보 제공을 목적으로 하며, 내용의 정확성을 보장하지 않습니다.",
                    ),
                }

                print(f"[DEBUG] Compact 최종 데이터 구조:")
                print(f"  - top_articles: {len(result_data['top_articles'])}개")
                print(f"  - grouped_sections: {len(result_data['grouped_sections'])}개")
                print(f"  - definitions: {len(result_data['definitions'])}개")
                print(f"  - grouped_sections 내용: {result_data['grouped_sections']}")
                print(f"  - definitions 내용: {result_data['definitions']}")

                # Compact 모드에서도 템플릿 렌더링 수행
                print("Compact 4단계: HTML 템플릿 렌더링 중...")
                newsletter_html = compose_newsletter(
                    result_data,
                    os.path.join(
                        os.path.dirname(os.path.dirname(__file__)), "templates"
                    ),
                    "compact",
                )

                print("Compact 뉴스레터 생성 완료!")
                return newsletter_html  # HTML 문자열 반환

            else:
                # Detailed 버전: 통합 아키텍처 사용
                print("3단계: Detailed 뉴스레터 데이터 구성 중...")

                # 템플릿 매니저로부터 메타데이터 가져오기
                template_manager = TemplateManager()

                # 키워드 및 주제 처리
                keywords = data.get("keywords", [])
                domain = data.get("domain", "")

                # 뉴스레터 주제 결정
                if domain:
                    newsletter_topic = domain
                elif isinstance(keywords, list) and len(keywords) == 1:
                    newsletter_topic = keywords[0]
                elif isinstance(keywords, list) and len(keywords) > 1:
                    newsletter_topic = tools.extract_common_theme_from_keywords(
                        keywords
                    )
                elif isinstance(keywords, str):
                    newsletter_topic = keywords
                else:
                    newsletter_topic = "최신 산업 동향"

                # 검색 키워드 문자열 생성
                if isinstance(keywords, list):
                    search_keywords = ", ".join(keywords)
                else:
                    search_keywords = keywords

                # Detailed 뉴스레터 데이터 구성
                detailed_data = {
                    "newsletter_topic": newsletter_topic,
                    "domain": domain,  # 도메인 정보 추가
                    "generation_date": os.environ.get(
                        "GENERATION_DATE", datetime.datetime.now().strftime("%Y-%m-%d")
                    ),
                    "generation_timestamp": os.environ.get(
                        "GENERATION_TIMESTAMP",
                        datetime.datetime.now().strftime("%H:%M:%S"),
                    ),
                    "search_keywords": search_keywords,
                    "sections": sections_data.get("sections", []),
                    # 템플릿 매니저에서 가져온 정보
                    "company_name": template_manager.get(
                        "company.name", "산업통상자원 R&D 전략기획단"
                    ),
                    "recipient_greeting": template_manager.get(
                        "audience.description", "R&D 전략기획단 전문위원님들께"
                    ),
                    "introduction_message": f"안녕하십니까. 금주 '{newsletter_topic}' 관련 주요 산업 동향을 정리해 드립니다.",
                    "food_for_thought": {
                        "message": f"이번 주 {newsletter_topic} 분야의 뉴스를 종합해보면, 기술 혁신의 속도가 빨라지고 있으며 글로벌 경쟁이 더욱 치열해지고 있습니다. 특히 AI와의 융합, 공급망 재편, 새로운 규제 환경 등이 산업 전반에 큰 영향을 미치고 있습니다. 우리 R&D 전략기획단은 이러한 변화의 흐름 속에서 어떤 기술 분야에 우선순위를 두고 투자해야 할까요? 또한 국제 협력과 자체 기술 개발 사이에서 어떤 균형점을 찾아야 할까요? 이번 주 뉴스가 제시하는 시사점을 바탕으로 중장기 R&D 로드맵을 재검토해 보시기 바랍니다."
                    },
                    "closing_message": "이번 주 뉴스 클리핑이 위원님들의 연구 개발 활동과 전략 구상에 도움이 되었기를 바랍니다. 다음 주에도 더욱 유익한 정보로 찾아뵙겠습니다. 감사합니다.",
                    "editor_signature": template_manager.get(
                        "editor.signature", "OSP 뉴스레터 편집팀 드림"
                    ),
                    # 추가 템플릿 설정
                    "copyright_year": template_manager.get(
                        "company.copyright_year", datetime.date.today().strftime("%Y")
                    ),
                    "company_tagline": template_manager.get(
                        "company.tagline", "최신 기술 동향을 한눈에"
                    ),
                    "footer_contact": template_manager.get(
                        "footer.contact_info", "문의사항: hjjung2@osp.re.kr"
                    ),
                    "editor_name": template_manager.get("editor.name", "Google Gemini"),
                    "editor_email": template_manager.get(
                        "editor.email", "hjjung2@osp.re.kr"
                    ),
                    "footer_disclaimer": template_manager.get(
                        "footer.disclaimer",
                        "이 뉴스레터는 정보 제공을 목적으로 하며, 내용의 정확성을 보장하지 않습니다.",
                    ),
                }

                # render_data.json 파일 저장
                try:
                    output_dir = os.path.join("output", "intermediate_processing")
                    os.makedirs(output_dir, exist_ok=True)
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

                    # 파일명에 사용할 안전한 주제 문자열 생성
                    topic_slug = tools.get_filename_safe_theme(
                        keywords if isinstance(keywords, list) else [keywords], domain
                    )

                    render_data_filename = (
                        f"render_data_langgraph_{timestamp}_{topic_slug}.json"
                    )
                    render_data_path = os.path.join(output_dir, render_data_filename)

                    with open(render_data_path, "w", encoding="utf-8") as f:
                        json.dump(detailed_data, f, ensure_ascii=False, indent=2)
                    print(f"Render data saved to {render_data_path}")
                except Exception as e:
                    print(f"Render data 저장 중 오류: {e}")

                # 4단계: compose_newsletter 함수로 HTML 렌더링
                print("4단계: HTML 템플릿 렌더링 중...")
                template_dir = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), "templates"
                )

                newsletter_html = compose_newsletter(
                    detailed_data, template_dir, "detailed"  # detailed 템플릿 사용
                )

                print("Detailed 뉴스레터 생성 완료!")
                return newsletter_html  # HTML 문자열 반환

        except Exception as e:
            print(f"뉴스레터 생성 중 오류 발생: {e}")
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
