"""Summarization chain builder for newsletter generation."""

# mypy: disable-error-code=no-untyped-def

import json

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableLambda

from .chains_llm_utils import get_llm
from .utils.logger import get_logger

logger = get_logger(__name__)


def build_summarization_chain(summarization_prompt: str, is_compact: bool = False):
    llm = get_llm(temperature=0.3)

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

        logger.info(f"처리할 카테고리 수: {len(categories_data.get('categories', []))}")

        for category in categories_data.get("categories", []):
            # 해당 카테고리에 속한 기사들 추출
            category_articles = []
            for idx in category.get("article_indices", []):
                if 0 <= idx - 1 < len(articles_data.get("articles", [])):
                    category_articles.append(articles_data["articles"][idx - 1])

            logger.info(
                f"카테고리 '{category.get('title', '제목 없음')}' - "
                f"관련 기사 수: {len(category_articles)}"
            )

            # 카테고리 기사들을 포맷팅
            formatted_articles = "\n---\n".join(
                [
                    f"기사 #{i + 1}:\n제목: {article.get('title', '제목 없음')}\n"
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
                prompt_content = summarization_prompt.format(
                    category_title=category_title,
                    category_articles=formatted_articles,
                )

            # LLM에 요청 (연결 오류에 대한 개별 처리 추가)
            messages = [HumanMessage(content=prompt_content)]

            # 개별 카테고리 처리에 try-catch 추가 (연결 문제 대응)
            try:
                logger.info(f"카테고리 '{category.get('title', '제목 없음')}' 요약 생성 중...")
                summary_result = llm.invoke(messages)
                summary_text = summary_result.content
                logger.info(f"카테고리 '{category.get('title', '제목 없음')}' 요약 생성 완료")

                # JSON 파싱 시작
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

                        # definitions가 비어있다면 기본 definition 생성
                        if not compact_result["definitions"]:
                            category_title = summary_json["title"]
                            # 카테고리 제목을 바탕으로 기본 definition 생성
                            if "자율주행" in category_title:
                                compact_result["definitions"] = [
                                    {
                                        "term": "자율주행",
                                        "explanation": (
                                            "운전자의 개입 없이 차량이 스스로 주행하는 기술로, "
                                            "레벨 0부터 5까지 단계별로 구분됩니다."
                                        ),
                                    }
                                ]
                            elif any(
                                keyword in category_title for keyword in ["기술", "개발"]
                            ):
                                compact_result["definitions"] = [
                                    {
                                        "term": "R&D",
                                        "explanation": (
                                            "연구개발(Research and Development)의 "
                                            "줄임말로, 새로운 기술이나 제품을 "
                                            "개발하는 활동입니다."
                                        ),
                                    }
                                ]
                            elif any(
                                keyword in category_title for keyword in ["정책", "규제"]
                            ):
                                compact_result["definitions"] = [
                                    {
                                        "term": "산업정책",
                                        "explanation": (
                                            "정부가 특정 산업의 발전을 위해 "
                                            "수립하는 정책으로, 규제 완화, "
                                            "지원책 등을 포함합니다."
                                        ),
                                    }
                                ]
                            else:
                                # 일반적인 기본 definition
                                compact_result["definitions"] = [
                                    {
                                        "term": "혁신기술",
                                        "explanation": (
                                            "기존 기술을 크게 개선하거나 완전히 새로운 방식의 "
                                            "기술로, 산업과 사회에 큰 변화를 가져올 수 있는 "
                                            "기술입니다."
                                        ),
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

                except Exception as parse_error:
                    logger.error(
                        f"카테고리 '{category.get('title', '제목 없음')}' JSON 파싱 오류: {parse_error}"
                    )
                    # JSON 파싱 실패 시 기본 구조 제공
                    category_title = category.get("title", "제목 없음")
                    if is_compact:
                        results.append(
                            {
                                "title": category_title,
                                "intro": f"{category_title}에 대한 주요 동향입니다. (JSON 파싱 오류)",
                                "definitions": [
                                    {
                                        "term": "기술동향",
                                        "explanation": f"{category_title} 분야의 최신 기술 발전 동향입니다.",
                                    }
                                ],
                                "articles": [
                                    {
                                        "title": article.get("title", ""),
                                        "url": article.get("url", "#"),
                                        "source_and_date": (
                                            f"{article.get('source', 'Unknown')} · "
                                            f"{article.get('date', 'Unknown date')}"
                                        ),
                                    }
                                    for article in category_articles
                                ],
                            }
                        )
                    else:
                        results.append(
                            {
                                "title": category_title,
                                "summary_paragraphs": [
                                    f"{category_title} 분야의 주요 동향입니다. (JSON 파싱 오류)"
                                ],
                                "definitions": [
                                    {
                                        "term": "기술동향",
                                        "explanation": f"{category_title} 분야의 최신 기술 발전 동향입니다.",
                                    }
                                ],
                                "news_links": [
                                    {
                                        "title": article.get("title", ""),
                                        "url": article.get("url", "#"),
                                        "source_and_date": (
                                            f"{article.get('source', 'Unknown')} · "
                                            f"{article.get('date', 'Unknown date')}"
                                        ),
                                    }
                                    for article in category_articles
                                ],
                            }
                        )

            except Exception as llm_error:
                logger.error(
                    f"카테고리 '{category.get('title', '제목 없음')}' LLM 호출 오류: {llm_error}"
                )
                # 연결 오류 발생 시 기본 구조로 fallback
                category_title = category.get("title", "제목 없음")

                if is_compact:
                    # compact 모드 fallback
                    fallback_definitions = [
                        {
                            "term": "기술동향",
                            "explanation": f"{category_title} 분야의 최신 기술 발전 동향입니다.",
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
                                    "source_and_date": (
                                        f"{article.get('source', 'Unknown')} · "
                                        f"{article.get('date', 'Unknown date')}"
                                    ),
                                }
                                for article in category_articles
                            ],
                        }
                    )
                else:
                    # detailed 모드 fallback
                    results.append(
                        {
                            "title": category_title,
                            "summary_paragraphs": [
                                f"{category_title} 분야의 주요 동향입니다. (네트워크 연결 문제로 인해 자세한 요약을 생성할 수 없었습니다)"
                            ],
                            "definitions": [
                                {
                                    "term": "기술동향",
                                    "explanation": f"{category_title} 분야의 최신 기술 발전 동향입니다.",
                                }
                            ],
                            "news_links": [
                                {
                                    "title": article.get("title", ""),
                                    "url": article.get("url", "#"),
                                    "source_and_date": (
                                        f"{article.get('source', 'Unknown')} · "
                                        f"{article.get('date', 'Unknown date')}"
                                    ),
                                }
                                for article in category_articles
                            ],
                        }
                    )

                # 다음 카테고리 처리를 위해 continue
                continue

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
