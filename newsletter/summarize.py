try:
    import google.generativeai as genai
except ImportError:
    genai = None  # Gemini API 사용 불가 상태로 표시

from . import config  # Import config module
from typing import List, Union, Dict, Any

SYSTEM_INSTRUCTION = """
Role: 당신은 뉴스들을 분석하고 요약하여, 제공된 HTML 템플릿 형식으로 "주간 산업 동향 뉴스 클리핑"을 작성하는 전문 편집자입니다.

Context: 독자들은 한국 첨단사업의 R&D 전략기획단 소속으로, 젊은 팀원들과 수석전문위원들로 구성되어 있습니다. 이들은 매주 특정 산업 주제에 대한 기술 동향과 주요 뉴스를 받아보기를 원합니다.

Input:
1.  하나 이상의 '키워드' (예: "친환경 자동차", "AI 반도체"). 이 키워드는 뉴스레터의 주된 주제가 됩니다.
2.  여러 '뉴스 기사' 목록. 각 기사는 제목, URL, 본문 내용을 포함합니다.

Output Requirements:
-   **HTML 형식**: 최종 결과물은 다른 설명 없이 순수한 HTML 코드여야 합니다. API로 직접 전달될 예정입니다.
-   **언어**: 한국어, 정중한 존댓말을 사용합니다.
-   **구조**: 다음 HTML 템플릿 구조를 반드시 따라야 합니다.

HTML Template Structure:
```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>주간 산업 동향 뉴스 클리핑</title>
</head>
<body>
    <h2>전략프로젝트팀 주간 산업 동향 뉴스 클리핑 ([주제 키워드 삽입])</h2>
    <p>안녕하세요, 전략프로젝트팀의 젊은 팀원과 수석전문위원 여러분.</p>
    <p>지난 한 주간의 [주제 키워드 삽입] 산업 관련 주요 기술 동향 및 뉴스를 정리하여 보내드립니다. 함께 살펴보시고 R&D 전략 수립에 참고하시면 좋겠습니다.</p>
    <hr>

    <!-- 반복되는 카테고리 섹션 시작 -->
    <h3>[카테고리 번호]. [카테고리 제목]</h3>
    <p>[카테고리별 요약 내용: 여러 기사를 종합하여 해당 카테고리의 동향을 상세히 설명합니다.]</p>
    
    <h4>이런 뜻이에요!</h4>
    <ul>
        <!-- 해당 카테고리에서 설명이 필요한 용어가 있다면 목록으로 제공 -->
        <li><strong>[용어1]:</strong> [용어1에 대한 쉽고 간단한 설명]</li>
        <li><strong>[용어2]:</strong> [용어2에 대한 쉽고 간단한 설명]</li>
        <!-- ... 추가 용어 ... -->
    </ul>
    <br>
    <!-- 반복되는 카테고리 섹션 끝 -->

    <!-- ... 다른 카테고리들 ... -->

    <hr>

    <h3>참고 뉴스 링크</h3>
    <!-- 카테고리별로 그룹화된 뉴스 링크 목록 -->
    <h4>[카테고리 번호]. [카테고리 제목]</h4>
    <ul>
        <li><a href="[기사 URL]" target="_blank">[기사 제목]</a> ([출처], [시간 정보])</li>
        <!-- ... 해당 카테고리의 다른 기사 링크 ... -->
    </ul>
    <!-- ... 다른 카테고리의 뉴스 링크 그룹 ... -->
    <hr>

    <h3>생각해 볼 거리</h3>
    <p><strong>"[인용구]" - [인용구 출처]</strong></p>
    <p>[뉴스 내용과 관련하여 독자들이 생각해볼 만한 점이나 격려의 메시지를 담은 마무리 문단]</p>
    <br>
    <p>다음 주에 더 유익한 정보로 찾아뵙겠습니다. 감사합니다.</p>
    <p><em>편집자 드림</em></p>
</body>
</html>
```

Task Breakdown:
1. **Categorization**: 입력된 뉴스 기사들을 내용에 따라 여러 카테고리로 분류합니다. (예: "전기차 시장 동향", "하이브리드차 동향" 등). 카테고리 제목과 번호를 부여합니다.
2.  **Summarization per Category**: 각 카테고리별로 해당되는 기사들의 주요 내용을 종합하여 상세하게 설명하는 요약문을 작성합니다.
3.  **Terminology Explanation ("이런 뜻이에요!")**: 각 카테고리 요약문에서 신입직원이 이해하기 어려울 수 있는 전문 용어나 개념이 있다면, 이를 선정하여 쉽고 간단하게 설명하는 목록을 만듭니다.
4.  **News Links**: 각 카테고리별로 관련 뉴스 기사들의 원문 링크를 제목, 출처, 시간 정보와 함께 목록으로 제공합니다.
5.  **Theme Setting**: 입력된 '키워드'를 뉴스레터의 전체 주제로 설정하고, 제목과 도입부에 반영합니다. (예: "친환경 자동차")
6.  **Concluding Remarks ("생각해 볼 거리")**: 전체 뉴스 내용을 바탕으로 독자들에게 생각해볼 만한 질문이나 영감을 줄 수 있는 인용구를 포함한 마무리 메시지를 작성합니다.

Instructions:
-   입력된 모든 뉴스 기사를 분석하여 적절한 카테고리로 분류하고, 각 카테고리별로 위 구조에 맞춰 내용을 채워주세요.
-   '키워드'는 뉴스레터의 주제로 사용됩니다. 예를 들어, 키워드가 "친환경 자동차"라면, HTML 제목은 "전략프로젝트팀 주간 산업 동향 뉴스 클리핑 (친환경 자동차)"가 됩니다.
-   '이런 뜻이에요!' 섹션은 필요에 따라 각 카테고리마다 포함시키거나, 용어가 없다면 생략해도 됩니다.
-   '참고 뉴스 링크'는 반드시 카테고리별로 분류하여 제공해야 합니다. 기사 제목, URL, 그리고 가능하다면 출처와 시간 정보를 포함해주세요.
-   최종 결과물은 위의 HTML 템플릿을 완벽하게 따르는 단일 HTML 문자열이어야 합니다. 다른 부가적인 텍스트나 설명은 포함하지 마세요.
"""


def summarize_articles(
    keywords: List[str],
    articles: Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]],
) -> str:
    """
    Summarize articles using Gemini Pro.

    Args:
        keywords: List of keywords to create context for summarization
        articles: Either a list of article dictionaries OR a dictionary of articles grouped by keywords
                 Each article has 'title', 'url', and 'content' keys

    Returns:
        HTML string containing the summarized newsletter
    """
    # Check if we have any articles to summarize
    if not articles:
        print("No articles to summarize.")
        # 비어있는 기사 목록에 대해 Gemini API를 호출하지 않고 즉시 결과 반환
        return "<html><body>No articles summary</body></html>"

    # 기사 수 계산
    article_count = (
        len(articles)
        if isinstance(articles, list)
        else sum(len(group) for group in articles.values())
    )

    # 키워드가 비어있는지 확인
    keyword_display = ", ".join(keywords) if keywords else ""

    print(
        f"Summarizing {article_count} articles for keywords: {keyword_display} using Gemini Pro..."
    )

    # Check if Gemini API is available
    if genai is None:
        print("ERROR: google.generativeai module is not available.")
        error_html = """
        <html>
        <body>
        <h1>오류: google.generativeai 모듈을 찾을 수 없습니다.</h1>
        <p>뉴스레터를 생성하려면 google-generativeai 패키지가 설치되어 있어야 합니다.</p>
        <p>설치 방법: pip install google-generativeai</p>
        <p>키워드: {}</p>
        <p>제공된 기사 수: {}</p>
        </body>
        </html>
        """.format(
            keyword_display,
            article_count,
        )
        return error_html

    # Check API key
    if not hasattr(config, "GEMINI_API_KEY") or not config.GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY is not set. Cannot generate newsletter.")
        error_html = """
        <html>
        <body>
        <h1>오류: GEMINI_API_KEY가 설정되지 않았습니다.</h1>
        <p>뉴스레터를 생성하려면 Gemini API 키가 필요합니다.</p>
        <p>키워드: {}</p>
        <p>제공된 기사 수: {}</p>
        </body>
        </html>
        """.format(
            keyword_display,
            article_count,
        )
        return error_html

    try:
        genai.configure(api_key=config.GEMINI_API_KEY)

        # Create the model with system instructions
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro-latest",
            system_instruction=SYSTEM_INSTRUCTION,
        )

        # Convert keywords to comma-separated string for prompt
        if not keywords:
            keyword_str = "지정된 주제 없음"
        else:
            keyword_str = ", ".join(keywords)

        # Prepare content for LLM. Combine all articles and keywords into one prompt.
        articles_details = []

        # Handle different article formats
        if isinstance(articles, dict):
            # Process grouped articles (dictionary where keys are keywords and values are article lists)
            for keyword, keyword_articles in articles.items():
                for article in keyword_articles:
                    title = article.get("title", "제목 없음")
                    url = article.get("url", "#")
                    content = article.get("content", "내용 없음")
                    articles_details.append(
                        f"기사 제목: {title}\nURL: {url}\n내용:\n{content}"
                    )
        else:
            # Process flat list of articles (original format)
            for article in articles:
                title = article.get("title", "제목 없음")
                url = article.get("url", "#")
                content = article.get("content", "내용 없음")
                articles_details.append(
                    f"기사 제목: {title}\nURL: {url}\n내용:\n{content}"
                )

        # Combine article details with newlines between each article
        articles_text = "\n\n---\n\n".join(articles_details)

        # Create the full prompt for Gemini Pro
        prompt = f"키워드: {keyword_str}\n\n뉴스 기사 목록:\n\n{articles_text}"

        try:
            # Generate the summary using Gemini Pro
            response = model.generate_content([prompt])
            if hasattr(response, "text"):
                html_content = response.text
                return html_content
            else:
                print("Error: Could not get text from Gemini response.")
                error_html = f"""
                <html>
                <body>
                <h1>오류 발생</h1>
                <p>키워드 '{keyword_display}'에 대한 뉴스레터 요약 중 오류가 발생했습니다: 응답에서 텍스트를 가져올 수 없습니다.</p>
                </body>
                </html>
                """
                return error_html
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            error_html = f"""
            <html>
            <body>
            <h1>오류 발생</h1>
            <p>키워드 '{keyword_display}'에 대한 뉴스레터 요약 중 오류가 발생했습니다: {str(e)}</p>
            </body>
            </html>
            """
            return error_html
    except Exception as e:
        print(f"General error in summarization process: {e}")
        error_html = f"""
        <html>
        <body>
        <h1>오류 발생</h1>
        <p>뉴스레터 요약 시스템 오류: {str(e)}</p>
        </body>
        </html>
        """
        return error_html
