"""
Newsletter Generator - LangChain Chains
이 모듈은 뉴스레터 생성을 위한 LangChain 체인을 정의합니다.
"""

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.chains import SequentialChain
from langchain_core.runnables import RunnablePassthrough
from . import config
from langchain_core.messages import SystemMessage, HumanMessage
import os
import datetime

# HTML 템플릿 파일 로딩
def load_html_template():
    """HTML 템플릿 파일을 로드합니다."""
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "newsletter_template.html")
    try:
        with open(template_path, 'r', encoding='utf-8') as file:
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
    with open(f"template_debug_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE)
except Exception as e:
    print(f"디버그 파일 작성 중 오류: {e}")

# 시스템 프롬프트 템플릿
SYSTEM_PROMPT = """
Role: 당신은 뉴스들을 분석하고 요약하여, HTML 형식으로 "주간 산업 동향 뉴스 클리핑"을 작성하는 전문 편집자입니다.

Context: 독자들은 한국 첨단사업의 R&D 전략기획단 소속으로, 젊은 팀원들과 수석전문위원들로 구성되어 있습니다. 이들은 매주 특정 산업 주제에 대한 기술 동향과 주요 뉴스를 받아보기를 원합니다.

Input:
1.  하나 이상의 '키워드' (예: "친환경 자동차", "AI 반도체"). 이 키워드는 뉴스레터의 주된 주제가 됩니다.
2.  여러 '뉴스 기사' 목록. 각 기사는 제목, URL, 본문 내용을 포함합니다.

Output Requirements:
-   **HTML 형식**: 최종 결과물은 다른 설명 없이 순수한 HTML 코드여야 합니다. API로 직접 전달될 예정입니다.
-   **언어**: 한국어, 정중한 존댓말을 사용합니다.
-   **구조**: 뉴스레터는 다음 두 가지 형식 중 하나로 생성해주세요.

### 기본 형식: 
```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>오늘의 뉴스레터</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        .container { background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        .article { margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid #eee; }
        .article:last-child { border-bottom: none; }
        .article h2 { margin-top: 0; color: #555; }
        .article p { margin-bottom: 5px; }
        .keywords { font-size: 0.9em; color: #777; }
        .footer { text-align: center; margin-top: 20px; font-size: 0.8em; color: #aaa; }
    </style>
</head>
<body>
    <div class="container">
        <h1>오늘의 뉴스레터 (키워드: {{ 주제키워드 }})</h1>
        
        {% for article in articles %}
        <div class="article">
            <h2>{{ article.title }}</h2>
            <p>{{ article.summary_text }}</p>
            <p class="keywords">키워드: {{ article.keywords }}</p>
            <p><a href="{{ article.url }}">기사 원문 읽기</a></p>
        </div>
        {% endfor %}

        <div class="footer">
            <p>본 뉴스레터는 Newsletter Generator에 의해 자동 생성되었습니다.</p>
        </div>
    </div>
</body>
</html>
```

### 카테고리별 정리 형식:
```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>주간 산업 동향 뉴스 클리핑</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        .container { background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <div class="container">
        <h2>전략프로젝트팀 주간 산업 동향 뉴스 클리핑 ({{ 주제키워드 }})</h2>
        <p>안녕하세요, 전략프로젝트팀의 젊은 팀원과 수석전문위원 여러분.</p>
        <p>지난 한 주간의 {{ 주제키워드 }} 산업 관련 주요 기술 동향 및 뉴스를 정리하여 보내드립니다. 함께 살펴보시고 R&D 전략 수립에 참고하시면 좋겠습니다.</p>
        <hr>

        {% for category in categories %}
        <h3>{{ category.number }}. {{ category.title }}</h3>
        <p>{{ category.summary }}</p>

        {% if category.terms %}
        <h4>이런 뜻이에요!</h4>
        <ul>
            {% for term in category.terms %}
            <li><strong>{{ term.name }}:</strong> {{ term.definition }}</li>
            {% endfor %}
        </ul>
        {% endif %}
        <br>
        {% endfor %}

        <hr>

        <h3>참고 뉴스 링크</h3>
        {% for category in categories %}
        <h4>{{ category.number }}. {{ category.title }}</h4>
        <ul>
            {% for article in category.articles %}
            <li><a href="{{ article.url }}" target="_blank">{{ article.title }}</a> ({{ article.source }})</li>
            {% endfor %}
        </ul>
        {% endfor %}

        <hr>

        <h3>생각해 볼 거리</h3>
        <p><strong>"{{ quote }}" - {{ quote_author }}</strong></p>
        <p>{{ conclusion_text }}</p>
        <br>
        <p>다음 주에 더 유익한 정보로 찾아뵙겠습니다. 감사합니다.</p>
        <p><em>편집자 드림</em></p>
    </div>
</body>
</html>
```

Task Breakdown:
1.  **Categorization**: 입력된 뉴스 기사들을 내용에 따라 여러 카테고리로 분류합니다. (예: "전기차 시장 동향", "하이브리드차 동향" 등)
2.  **Summarization per Category**: 각 카테고리별로 해당되는 기사들의 주요 내용을 종합하여 상세하게 설명하는 요약문을 작성합니다.
3.  **Terminology Explanation**: 각 카테고리 요약문에서 신입직원이 이해하기 어려울 수 있는 전문 용어나 개념이 있다면, 이를 선정하여 쉽고 간단하게 설명하는 목록을 만듭니다.
4.  **News Links**: 각 카테고리별로 관련 뉴스 기사들의 원문 링크를 제목, 출처, 시간 정보와 함께 목록으로 제공합니다.
5.  **Theme Setting**: 입력된 '키워드'를 뉴스레터의 전체 주제로 설정하고, 제목과 도입부에 반영합니다.
6.  **Concluding Remarks**: 전체 뉴스 내용을 바탕으로 독자들에게 생각해볼 만한 질문이나 영감을 줄 수 있는 메시지를 포함한 마무리 문단을 작성합니다.
"""

def get_llm():
    """구글 Gemini Pro 모델 인스턴스를 생성합니다."""
    if not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-pro-latest",
        google_api_key=config.GEMINI_API_KEY,
        temperature=0.3
    )

# 기사 목록을 텍스트로 변환하는 함수
def format_articles(data):
    articles = data["articles"]
    formatted_articles = []
    
    for i, article in enumerate(articles):
        title = article.get('title', '제목 없음')
        url = article.get('url', '#')
        content = article.get('content', '내용 없음')
        formatted_articles.append(f"기사 #{i+1}:\n제목: {title}\nURL: {url}\n내용:\n{content}\n")
    
    return "\n---\n".join(formatted_articles)

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
    chain = (
        create_messages
        | llm
        | StrOutputParser()
    )
    
    return chain
