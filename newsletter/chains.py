"""
Newsletter Generator - LangChain Chains
이 모듈은 뉴스레터 생성을 위한 LangChain 체인을 정의합니다.
"""

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.chains import SequentialChain
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from . import config
from langchain_core.messages import SystemMessage, HumanMessage
import os
import datetime
import grpc
from unittest.mock import MagicMock
from newsletter.sources import NewsSourceManager


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

# 시스템 프롬프트 템플릿
SYSTEM_PROMPT = f"""
Role: 당신은 뉴스들을 분석하고 요약하여, HTML 형식으로 "주간 산업 동향 뉴스 클리핑"을 작성하는 전문 편집자입니다.

Context: 독자들은 한국 첨단산업의 R&D 전략기획단 소속으로, 분야별 전문위원으로 구성되어 있습니다. 이들은 매주 특정 산업 주제에 대한 기술 동향과 주요 뉴스를 받아보기를 원합니다.

Input:
1.  하나 이상의 '키워드' (예: "친환경 자동차", "AI 반도체"). 이 키워드는 뉴스레터의 주된 주제가 됩니다.
2.  여러 '뉴스 기사' 목록. 각 기사는 제목, URL, 본문 내용을 포함합니다.

Output Requirements:
-   **HTML 형식**: 최종 결과물은 다른 설명 없이 순수한 HTML 코드여야 합니다. API로 직접 전달될 예정입니다. 반드시 아래 제공된 HTML 템플릿을 사용해야 합니다.
-   **언어**: 한국어, 정중한 존댓말을 사용합니다.
-   **구조**: 뉴스레터는 아래 제공된 HTML 템플릿을 기반으로 생성해야 합니다. 템플릿 내의 Jinja2와 유사한 구문들 (예: `{{{{ variable }}}}`, `{{% for item in items %}}`, `{{% if condition %}}`)은 실제 데이터로 대체되어야 합니다. 예를 들어, `{{% for section in sections %}}` 루프는 실제 뉴스 섹션들로 채워져야 하며, `{{{{ newsletter_topic }}}}` 같은 플레이스홀더는 해당 값으로 대체되어야 합니다. 템플릿의 모든 플레이스홀더를 이해하고, 가능한 경우 해당 데이터를 채워야 합니다. (예: `{{{{ newsletter_topic }}}}`, `{{{{ generation_date }}}}`, `{{{{ recipient_greeting }}}}`, `{{{{ introduction_message }}}}`, `{{{{ sections }}}}`, `{{{{ food_for_thought }}}}`, `{{{{ closing_message }}}}`, `{{{{ editor_signature }}}}`, `{{{{ company_name }}}}` 등).
    제공된 템플릿에 있는 `{{% for i in range(29, 39) %}}` 와 같은 하드코딩된 루프 예시는 실제 뉴스 데이터에 기반한 내용으로 대체되어야 합니다.

### 제공되는 HTML 템플릿:
```html
{HTML_TEMPLATE}
```

Task Breakdown:
1.  **Data Extraction and Mapping**: 입력된 뉴스 기사들을 분석하여 위 HTML 템플릿의 각 섹션 (예: `sections`, `food_for_thought` 등)에 필요한 정보를 추출하고 매핑합니다.
2.  **Categorization (if applicable)**: `sections` 부분에는 뉴스 기사들을 내용에 따라 여러 카테고리로 분류하고 (예: "전기차 시장 동향", "하이브리드차 동향" 등), 각 카테고리별로 제목(`section.title`), 요약문(`section.summary_paragraphs`), 전문 용어 설명(`section.definitions`), 관련 뉴스 링크(`section.news_links`)를 템플릿 구조에 맞게 구성합니다.
3.  **Summarization per Category**: 각 카테고리별로 해당되는 기사들의 주요 내용을 종합하여 상세하게 설명하는 요약문을 `section.summary_paragraphs`에 작성합니다.
4.  **Terminology Explanation**: 각 카테고리 요약문에서 신입직원이 이해하기 어려울 수 있는 전문 용어나 개념이 있다면, 이를 선정하여 `section.definitions` 형식에 맞게 쉽고 간단하게 설명하는 목록을 만듭니다.
5.  **News Links**: 각 카테고리별로 관련 뉴스 기사들의 원문 링크를 제목, 출처, 시간 정보와 함께 `section.news_links` 형식에 맞게 목록으로 제공합니다.
6.  **Theme Setting**: 입력된 '키워드'를 뉴스레터의 전체 주제(`newsletter_topic`)로 설정하고, 제목과 도입부(`introduction_message`)에 반영합니다.
7.  **Concluding Remarks**: 전체 뉴스 내용을 바탕으로 독자들에게 생각해볼 만한 질문이나 영감을 줄 수 있는 메시지(`food_for_thought`, `closing_message`)를 작성합니다.
8.  **Placeholder Filling**: 템플릿의 나머지 플레이스홀더 (`generation_date`, `recipient_greeting`, `editor_signature`, `company_name` 등)에 적절한 값을 채워줍니다. `generation_date`는 오늘 날짜 (예: {datetime.date.today().strftime('%Y-%m-%d')})로 설정합니다.
"""


def get_llm():
    """구글 Gemini Pro 모델 인스턴스를 생성합니다."""
    if not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")

    # gRPC 메타데이터 관련 옵션 설정
    transport = "rest"  # 기본적으로 REST API 사용 (gRPC 대신)

    return ChatGoogleGenerativeAI(
        model="gemini-1.5-pro-latest",
        google_api_key=config.GEMINI_API_KEY,
        temperature=0.3,
        transport=transport,
        convert_system_message_to_human=True,  # 시스템 메시지를 휴먼 메시지로 변환
    )


# 기사 목록을 텍스트로 변환하는 함수
def format_articles(data):
    # 그룹화된 기사 또는 일반 기사 목록 처리
    if "articles" in data:
        # 일반 기사 목록
        articles = data["articles"]
        formatted_articles = []

        for i, article in enumerate(articles):
            title = article.get("title", "제목 없음")
            url = article.get("url", "#")
            content = article.get("content", "내용 없음")
            source = article.get("source", "출처 없음")  # 추가
            date = article.get("date", "날짜 없음")  # 추가
            formatted_articles.append(
                f"기사 #{i+1}:\n제목: {title}\nURL: {url}\n출처: {source}\n날짜: {date}\n내용:\n{content}\n"
            )

        return "\n---\n".join(formatted_articles)

    elif "grouped_articles" in data:
        # 그룹화된 기사 목록
        grouped_articles = data["grouped_articles"]
        formatted_sections = []

        for keyword, articles in grouped_articles.items():
            # 각 키워드를 섹션으로 처리
            section = f"## 키워드: {keyword}\n\n"

            for i, article in enumerate(articles):
                title = article.get("title", "제목 없음")
                url = article.get("url", "#")
                content = article.get("content", "내용 없음")
                source = article.get("source", "출처 없음")
                date = article.get("date", "날짜 없음")

                section += f"기사 #{i+1}:\n제목: {title}\nURL: {url}\n출처: {source}\n날짜: {date}\n내용:\n{content}\n\n"

            formatted_sections.append(section)

        return "\n\n===\n\n".join(formatted_sections)

    else:
        return "기사 데이터를 찾을 수 없습니다."


def get_summarization_chain():
    llm = get_llm()

    # 메시지 생성 함수
    def create_messages(data):
        # 시스템 메시지 생성
        system_message = SystemMessage(content=SYSTEM_PROMPT)

        # 사용자 메시지 생성
        user_content = f"""다음 키워드에 대한 뉴스레터를 생성해주세요: {data['keywords']}

다음은 뉴스 기사 목록입니다 (각 기사는 제목, URL, 내용으로 구성됩니다):
{format_articles(data)}

위 정보를 바탕으로 시스템 프롬프트에 명시된 HTML 형식 중 더 적합한 것을 선택하여 전체 뉴스레터 HTML을 생성해주세요.
기사 수와 주제에 따라 "기본 형식"이나 "카테고리별 정리 형식" 중 알맞은 것을 선택해주세요.
복잡한 주제나 여러 기사가 있는 경우 카테고리별로 정리하는 것이 좋습니다.
"""
        human_message = HumanMessage(content=user_content)

        return [system_message, human_message]

    # 체인 정의
    chain = RunnableLambda(create_messages) | llm | StrOutputParser()

    return chain
