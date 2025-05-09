import google.generativeai as genai
from . import config # Import config module

SYSTEM_PROMPT = """
Role: 당신은 뉴스들을 정리해서 친절하고 의미있게 설명해주는 편집자야. 한 주 간의 특정 주제의 산업의 기술 동향 및 주요 뉴스를 선별하고, "산업 동향 뉴스 클리핑"을 제공하려고해. 
Context: 당신의 독자들은 한국 첨단사업의 R&D 전략기획단의 전략프로젝트팀에서 함께 뉴스들을 매일 확인하고 싶어하는 젊은 팀원과 수석전문위원들이야.
Tone: 한글로 정중한 존댓말로 써주기를 바래
Objective: 이 뉴스를 읽고, 함께 묶을 수 있는 이슈가 있으면 여러개로 묶어서 분류하고, 그안의 주요 내용들을 상세하게 설명해줘. 주요 카테고리별 주요언론사 뉴스링크를 남겨서 함께 제공해줘. 그래서 기사의 원문에 접근할 수 있도록 하되, 가독성을 위해서 참고링크를 하단에 만들어서 읽기 쉽게 만들어줘.
Explain: 각 카테고리 별로 관련분야 신입직원이 잘 모르는 어려운 용어나 개념이 나온다면 추가로 '이런 뜻이에요' 칸을 만들어서 간단하고 쉽게 설명해줘.
End: 마지막은 독자들을 위해 위 뉴스에서 도출할 수 있는 생각해볼 만한 거리나 명언들을 생각해서 인사말을 전해줘.
Provider: Email의 HTML 형식으로 출력해주되, 바로 입력할 수 있할 수 있는형태로 부가적인 설명없이 결과만 보여줘. 바로 API로 전달하므로 본문 이외의 다른 것은 모두 제거해줘.
"""

def summarize_articles(articles: list):
    print(f"Summarizing {len(articles)} articles using Gemini Pro...")
    if not config.GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not found. Please set it in the .env file.")
        # Fallback to placeholder summarization if API key is missing
        return [
            {
                "title": f"Summary for {article['title']}",
                "summary_text": f"This is a placeholder summary of '{article.get('content', 'N/A')[:50]}...'. Configure Gemini API for actual summaries.",
                "keywords": ["keyword1", "keyword2"],
                "url": article.get("url", "#")
            } for article in articles
        ]

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name='gemini-pro',
        system_instruction=SYSTEM_PROMPT # Apply the system prompt
    )

    summaries = []
    for i, article in enumerate(articles):
        print(f"  Summarizing article {i+1}/{len(articles)}: {article.get('title', 'No Title')}")
        # Prepare content for LLM. Combine title and content for better context.
        content_to_summarize = f"Title: {article.get('title', 'No Title')}\n\nContent: {article.get('content', 'No Content')}"
        
        try:
            response = model.generate_content(content_to_summarize)
            # Assuming the response.text contains the HTML formatted summary as requested in the prompt
            # For this example, we'll assume the LLM returns a block of HTML for the article summary.
            summaries.append({
                "title": article.get('title', 'No Title'), 
                "summary_text": response.text, # This will be the HTML content from LLM
                "keywords": [], # Keywords might be part of the LLM's HTML or need separate extraction
                "url": article.get("url", "#")
            })
        except Exception as e:
            print(f"Error summarizing article '{article.get('title', 'No Title')}' with Gemini: {e}")
            summaries.append({
                "title": f"Error Summarizing: {article.get('title', 'No Title')}",
                "summary_text": f"Could not summarize article due to an error: {e}",
                "keywords": [],
                "url": article.get("url", "#")
            })
    return summaries
