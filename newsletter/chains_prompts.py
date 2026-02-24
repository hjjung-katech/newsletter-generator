"""
Newsletter Generator prompt and template constants.
"""

import os

from .utils.logger import get_logger

logger = get_logger(__name__)


def load_html_template() -> str:
    """HTML 템플릿 파일을 로드합니다."""
    template_path = os.path.join(
        os.path.dirname(__file__), "..", "templates", "newsletter_template.html"
    )
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Template file not found: {template_path}")
        return ""
    except Exception as e:
        logger.error(f"Error loading template: {e}")
        return ""


HTML_TEMPLATE = load_html_template()

try:
    from .utils.file_naming import save_debug_file

    debug_file_path = save_debug_file(HTML_TEMPLATE, "template_debug", "txt")
    logger.info(f"HTML template debug file saved: {debug_file_path}")
except Exception as e:
    logger.error(f"Error writing debug file: {e}")


CATEGORIZATION_PROMPT = """
당신은 뉴스들을 분석하고 분류하는 전문 편집자입니다.

독자 배경: 독자들은 한국 첨단산업의 R&D 전략기획단 소속 분야별 전문위원들입니다.
이들은 매주 요청된 키워드 분야의 기술 동향과 주요 뉴스를 받아보기를 원합니다.

다음 키워드에 관련된 뉴스 기사들을 분석하여, 의미있는 카테고리로 분류해주세요:
{keywords}

뉴스 기사 목록:
{formatted_articles}

뉴스 기사들을 분석하여 내용에 따라 여러 카테고리로 분류하세요.
예를 들어, "전기차 시장 동향", "하이브리드차 동향", "배터리 기술 발전" 등처럼
의미 있는 카테고리로 나누어야 합니다. 각 카테고리는 적절한 제목을 가져야 합니다.

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

하나의 기사는 여러 카테고리에 포함될 수 있지만,
모든 기사가 최소 하나의 카테고리에는 포함되어야 합니다.
각 카테고리 제목은, 독자가 어떤 내용인지 한눈에 알 수 있도록
명확하고 구체적으로 작성해주세요.
"""

SUMMARIZATION_PROMPT = """
당신은 뉴스들을 분석하고 요약하여 "주간 산업 동향 뉴스 클리핑"을
작성하는 전문 편집자입니다.

독자 배경: 독자들은 한국 첨단산업의 R&D 전략기획단 소속 분야별 전문위원들입니다.
이들은 매주 요청된 키워드 분야의 기술 동향과 주요 뉴스를 받아보기를 원합니다.

다음은 "{category_title}" 카테고리에 해당하는 뉴스 기사들입니다:
{category_articles}

위 기사들을 종합적으로 분석하여 다음 정보를 포함한 요약을 JSON 형식으로 만들어주세요:

1. summary_paragraphs: 해당 카테고리의 주요 내용을 1개의 단락으로 요약
   (각 단락은 배열의 항목)
   - 요약문은 객관적이고 분석적이며, 전체 기사들의 맥락을 포괄해야 합니다.
   - 정중한 존댓말을 사용합니다.

2. definitions: 해당 카테고리에서 등장하는 중요 용어나 개념 설명 (0-2개)
   - 신입직원이 이해하기 어려울 수 있는 전문 용어나 개념 중 가장 핵심적인 것만 선정
   - 다른 카테고리에서 이미 설명된 용어는 피하고,
     해당 카테고리 특유의 용어를 우선 선정
   - 꼭 필요한 경우가 아니면 1-2개로 제한하며,
     명확한 용어가 없다면 0개도 가능

3. news_links: 원본 기사 링크 정보
   - 각 카테고리별로 관련 뉴스 기사들의 원문 링크를
     제목, 출처, 시간 정보와 함께 제공합니다.

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
```"""

COMPOSITION_PROMPT = """
당신은 뉴스들을 분석하고 요약하여, HTML 형식으로 "주간 산업 동향 뉴스 클리핑"을
작성하는 전문 편집자입니다.

독자 배경: 독자들은 한국 첨단산업의 R&D 전략기획단 소속 분야별 전문위원들입니다.
이들은 매주 요청된 키워드 분야의 기술 동향과 주요 뉴스를 받아보기를 원합니다.

이미 각 카테고리별로 상세 요약이 완료되었습니다.
이제 뉴스레터의 전체 구성을 완성해야 합니다.

주제 키워드: {keywords}
카테고리 요약:
{category_summaries}

**매우 중요한 지시사항:**
- 위에 제공된 **주제 키워드({keywords})**와 **실제 카테고리 요약 내용**만을 사용하세요
- 주제 키워드와 관련 없는 내용은 절대 포함하지 마세요
- newsletter_topic은 제공된 키워드를 기반으로만 설정하세요
- introduction_message는 제공된 카테고리 요약의 실제 내용만을 반영하세요
- 제공된 뉴스 내용이 없더라도 키워드 주제에 맞는 유용한 뉴스레터를 작성하세요
- "[카테고리 요약]", "(각 카테고리별 핵심 내용)" 같은 placeholder 텍스트는 절대 사용하지 마세요
- food_for_thought의 message도 제공된 뉴스 내용과 키워드에만 기반하여 작성하세요

다음 정보를 포함한 뉴스레터 구성 정보를 JSON 형식으로 반환해주세요:

```json
{{
  "newsletter_topic": "제공된 키워드({keywords})를 기반으로 한 구체적인 뉴스레터 주제",
  "generation_date": "{current_date}",
  "recipient_greeting": "안녕하세요, R&D 전략기획단 전문위원 여러분",
  "introduction_message": "키워드 주제에 맞는 구체적이고 유용한 소개 문구 (뉴스가 없어도 해당 분야의 중요성이나 동향에 대한 통찰 제공)",
  "food_for_thought": {{
    "quote": "관련 명언 (선택사항)",
    "author": "명언 출처 (선택사항)",
    "message": "제공된 키워드 주제에 기반한 구체적인 질문이나 제안"
  }},
  "closing_message": "다음 주에 더 유익한 정보로 찾아뵙겠습니다. 감사합니다.",
  "editor_signature": "편집자 드림",
  "company_name": "R&D 전략기획단"
}}
```

참고:
- generation_date는 {current_date} 형식으로 유지해주세요.
- 모든 항목은 한국어로 작성하며, 정중한 존댓말을 사용합니다.
- 뉴스가 수집되지 않았더라도 키워드 주제의 중요성과 전략적 관점을 강조하는 유용한 내용을 작성하세요.
"""

SYSTEM_PROMPT = f"""
Role: 당신은 뉴스들을 분석하고 요약하여, HTML 형식으로 "주간 산업 동향 뉴스 클리핑"을
작성하는 전문 편집자입니다.

Context: 독자들은 한국 첨단산업의 R&D 전략기획단 소속으로,
분야별 전문위원으로 구성되어 있습니다. 이들은 매주 특정 산업 주제에 대한
기술 동향과 주요 뉴스를 받아보기를 원합니다.

Input:
1.  하나 이상의 '키워드' (예: "친환경 자동차", "AI 반도체").
    이 키워드는 뉴스레터의 주된 주제가 됩니다.
2.  여러 '뉴스 기사' 목록. 각 기사는 제목, URL, 본문 내용을 포함합니다.

Output Requirements:
-   **HTML 형식**: 최종 결과물은 다른 설명 없이 순수한 HTML 코드여야 합니다.
    API로 직접 전달될 예정입니다.
    반드시 아래 제공된 HTML 템플릿을 사용해야 합니다.
-   **언어**: 한국어, 정중한 존댓말을 사용합니다.
-   **구조**: 뉴스레터는 아래 제공된 HTML 템플릿을 기반으로 생성해야 합니다.

### 제공되는 HTML 템플릿:
```html
{HTML_TEMPLATE}
```

주의: SYSTEM_PROMPT는 하위 호환성을 위해 유지되었습니다.
새로운 코드에서는 CATEGORIZATION_PROMPT, SUMMARIZATION_PROMPT,
COMPOSITION_PROMPT를 사용하세요.
"""
