"""
Newsletter Generator - Custom Tools
이 모듈은 뉴스레터 생성을 위한 LangChain 도구를 정의합니다.
"""

import json
import logging
import os
from typing import Any, Dict, List, cast

import markdownify
import requests  # type: ignore[import-untyped]
from bs4 import BeautifulSoup
from langchain.prompts import PromptTemplate
from langchain.tools import tool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import ToolException
from langchain_google_genai import ChatGoogleGenerativeAI

from newsletter_core.application.tools_search_flow import (
    SerperKeywordFailure,
    SerperKeywordReport,
    SerperLogMessage,
    SerperSearchPlan,
    SerperSearchRequestError,
    SerperSearchResponseDecodeError,
    build_serper_failure_log_messages,
    build_serper_keyword_log_messages,
    build_serper_search_plans,
    execute_serper_search_plan,
    summarize_serper_search_reports,
)
from newsletter_core.application.tools_support import (
    extract_common_theme_fallback,
    parse_generated_keywords,
    resolve_filename_theme,
    resolve_search_request,
    sanitize_filename,
)

from . import config
from .html_utils import clean_html_markers
from .utils.error_handling import handle_exception
from .utils.logger import get_logger, show_collection_brief

# 로거 초기화
logger = get_logger()


def _execute_serper_search_request(
    search_plan: SerperSearchPlan,
) -> dict[str, Any]:
    try:
        response = requests.request(
            "POST",
            search_plan.url,
            headers=search_plan.headers,
            data=search_plan.payload,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise SerperSearchRequestError(str(exc)) from exc

    try:
        raw_results = response.json()
    except json.JSONDecodeError as exc:
        raise SerperSearchResponseDecodeError(response.text) from exc

    return cast(dict[str, Any], raw_results)


def _emit_serper_log_messages(log_messages: list[SerperLogMessage]) -> None:
    for log_message in log_messages:
        getattr(logger, log_message.level)(log_message.message)


@tool  # type: ignore[untyped-decorator]
def search_news_articles(keywords: str, num_results: int = 10) -> List[Dict]:
    """
    Search for news articles using the Serper.dev API for each keyword.

    Args:
        keywords: Comma-separated keywords to search for, like 'AI,Machine Learning'
        num_results: Number of results to return per keyword (default: 10, max: 20)
      Returns:
        A list of article dictionaries with 'title', 'url', 'snippet', 'source', and 'date' keys.
    """
    if not config.SERPER_API_KEY:
        raise ToolException("SERPER_API_KEY not found. Please set it in the .env file.")

    search_request = resolve_search_request(keywords, num_results)
    search_plans = build_serper_search_plans(
        search_request, api_key=config.SERPER_API_KEY
    )
    keyword_reports: list[SerperKeywordReport] = []

    logger.info("\nStarting article collection process:")
    for search_plan in search_plans:
        logger.info(f"Searching articles for keyword: '{search_plan.keyword}'")
        keyword_result = execute_serper_search_plan(
            search_plan,
            executor=_execute_serper_search_request,
        )

        if isinstance(keyword_result, SerperKeywordFailure):
            _emit_serper_log_messages(
                list(build_serper_failure_log_messages(keyword_result))
            )
            continue

        _emit_serper_log_messages(
            list(build_serper_keyword_log_messages(keyword_result))
        )
        keyword_reports.append(keyword_result)

    search_summary = summarize_serper_search_reports(keyword_reports)

    # 검색 결과 간결 표시
    total_collected = len(search_summary.all_articles)
    if search_summary.keyword_article_counts and total_collected > 0:
        show_collection_brief(search_summary.keyword_article_counts)
    elif total_collected > 0:
        logger.info(f"📰 총 {total_collected}개 기사 수집 완료")
    else:
        logger.warning("⚠️  수집된 기사가 없습니다")

    return cast(List[Dict], search_summary.all_articles)


@tool  # type: ignore[untyped-decorator]
def fetch_article_content(url: str) -> Dict[str, Any]:
    """
    Fetch the full content of an article from its URL.

    Args:
        url: The URL of the article to fetch

    Returns:
        A dictionary with 'title', 'url', and 'content' keys
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # 타이틀 추출
        title = soup.title.text.strip() if soup.title else "제목 없음"

        # 메인 콘텐츠 추출 시도 (다양한 방법으로)
        content = ""

        # 메타 설명 추출
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            content += meta_desc.get("content") + "\n\n"

        # article 태그 찾기
        article_tag = soup.find("article")
        if article_tag:
            # 불필요한 요소 제거
            for tag in article_tag.find_all(
                ["script", "style", "nav", "footer", "aside"]
            ):
                tag.decompose()

            content += article_tag.get_text(separator="\n", strip=True)
        else:
            # 본문으로 추정되는 태그들 찾기
            for tag_name in ["div", "section"]:
                for attr in ["id", "class"]:
                    for keyword in [
                        "content",
                        "article",
                        "main",
                        "body",
                        "entry",
                        "post",
                    ]:
                        main_content = soup.find(
                            tag_name,
                            {
                                attr: lambda x: (
                                    x and keyword in x.lower() if x else False
                                )
                            },
                        )
                        if main_content:
                            # 불필요한 요소 제거
                            for tag in main_content.find_all(
                                ["script", "style", "nav", "footer", "aside"]
                            ):
                                tag.decompose()

                            content += main_content.get_text(separator="\n", strip=True)
                            break
                    if content:
                        break
                if content:
                    break

        # 본문을 찾지 못한 경우 전체 텍스트 사용
        if not content:
            # 불필요한 요소 제거
            for tag in soup.find_all(["script", "style", "nav", "footer", "aside"]):
                tag.decompose()

            content = (
                soup.body.get_text(separator="\n", strip=True)
                if soup.body
                else "내용을 추출할 수 없습니다."
            )

        # 결과 반환
        return {
            "title": title,
            "url": url,
            "content": content[:5000],  # 컨텐츠 길이 제한 (토큰 절약)
        }

    except Exception as e:
        import logging

        logging.warning(f"fetch_article_content 예외 발생: {e}")
        raise ToolException(f"Error fetching article content: {str(e)}")


@tool  # type: ignore[untyped-decorator]
def save_newsletter_locally(
    html_content: str, filename_base: str, output_format: str = "html"
) -> str:
    """
    Save newsletter content locally as HTML or Markdown.

    Args:
        html_content: HTML content of the newsletter
        filename_base: Base filename (without extension)
        output_format: Format to save as ('html' or 'md')

    Returns:
        Path to the saved file
    """
    if output_format not in ["html", "md"]:
        raise ToolException("Format must be 'html' or 'md'")

    try:
        # Clean HTML markers from content before saving
        cleaned_html_content = clean_html_markers(html_content)

        # 출력 디렉토리 생성 (없는 경우)
        output_dir = os.path.join(os.getcwd(), "output")
        os.makedirs(output_dir, exist_ok=True)

        # 파일 경로 생성
        file_path = os.path.join(output_dir, f"{filename_base}.{output_format}")

        # 마크다운으로 변환 (필요한 경우)
        if output_format == "md":
            content = markdownify.markdownify(cleaned_html_content, heading_style="ATX")
        else:
            content = cleaned_html_content

        # 파일 저장
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Newsletter saved locally as {filename_base}.{output_format} at {file_path}"

    except Exception as e:
        raise ToolException(f"Error saving newsletter locally: {e}")


# Keyword generation still owns LLM/runtime glue in the legacy wrapper.
def generate_keywords_with_gemini(
    domain: str,
    count: int = 10,
    callbacks: list[Any] | None = None,
) -> list[str]:
    """
    Generates high-quality trend keywords for a given domain using configured LLM.
    """
    try:
        if callbacks is None:
            callbacks = []
        if os.environ.get("ENABLE_COST_TRACKING"):
            try:
                from .cost_tracking import get_tracking_callbacks

                handle_exception(None, "비용 추적 콜백 추가", log_level=logging.INFO)
                callbacks += get_tracking_callbacks()
            except Exception as e:
                handle_exception(e, "비용 추적 콜백 추가", log_level=logging.INFO)
                # 비용 추적 실패는 치명적이지 않음

        # LLM 팩토리를 사용하여 키워드 생성에 최적화된 모델 사용
        try:
            from .llm_factory import get_llm_for_task

            llm = get_llm_for_task(
                "keyword_generation", callbacks, enable_fallback=True
            )
        except Exception as e:
            logger.warning(f"LLM factory failed, using fallback: {e}")
            # Fallback to stable Gemini model
            if not config.GEMINI_API_KEY:
                logger.error(
                    "GEMINI_API_KEY is not configured. Cannot generate keywords."
                )
                return []

            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-pro",  # 더 안정적인 모델로 변경
                temperature=0.7,
                google_api_key=config.GEMINI_API_KEY,
                transport="rest",
                convert_system_message_to_human=True,
                callbacks=callbacks,
                timeout=60,
                max_retries=3,  # 재시도 횟수 증가
                disable_streaming=False,
            )

        prompt_template = PromptTemplate.from_template(
            """You are a news search expert highly skilled at identifying effective search queries for finding the latest news articles about a given field.

        Based on the [Field Information] provided below, please generate exactly {count} highly effective search keywords (search queries) that someone would use *right now* to find recent news or significant events within this field.

        **IMPORTANT:** The generated keywords must be in **Korean**.

        Keyword Generation Guidelines:
        1.  Each keyword should be in the form of a natural phrase (generally 2-4 words) suitable for use in a real news search engine.
        2.  Prioritize terms that cover recent or currently notable major events, individuals, companies/organizations, technological changes, or other timely developments within the given field.
        3.  Include keywords that can yield specific search results rather than overly general or broad single words.
        4.  Ensure the generated keywords are likely to appear in Korean news headlines or body text and have a high probability of being used in actual news searches by Korean speakers.
        5.  Ensure you provide exactly the requested number of keywords ({count}).

        [Field Information]:
        {domain}

        Generated Search Keyword List (in Korean):
        (Provide each keyword on a new line, without any numbering or bullet points. Include only the Korean keywords themselves.)
        """
        )

        chain = prompt_template | llm | StrOutputParser()

        logger.info(f"Generating keywords for '{domain}' using Google Gemini...")

        # 실행 및 응답 처리
        response_content = chain.invoke({"domain": domain, "count": count})
        logger.debug(f"Raw response from Gemini:\n{response_content}")
        final_keywords = parse_generated_keywords(response_content, count)

        # 키워드 효과성 검증 (옵션)
        final_keywords = validate_and_refine_keywords(
            final_keywords, min_results_per_keyword=3, count=count
        )

        logger.info(f"최종 키워드 ({len(final_keywords)}):")
        for i, kw in enumerate(final_keywords, 1):
            logger.info(f"  {i}. {kw}")

        return final_keywords

    except Exception as e:
        logger.error(f"Error generating keywords with Gemini: {e}")
        return []


def validate_and_refine_keywords(
    keywords: list[str], min_results_per_keyword: int = 3, count: int = 10
) -> list[str]:
    """각 키워드로 검색했을 때 충분한 결과가 나오는지 검증하고, 문제가 있는 키워드는 대체합니다."""

    validated_keywords = []
    replacement_needed = []

    logger.info("\n검증 중: 각 키워드가 충분한 뉴스 결과를 반환하는지 확인합니다...")

    for keyword in keywords:
        try:
            # 키워드로 테스트 검색 (invoke 메서드 사용)
            test_results = search_news_articles.invoke(
                {"keywords": keyword, "num_results": 5}
            )

            if len(test_results) >= min_results_per_keyword:
                validated_keywords.append(keyword)
                logger.info(f"[green]✓ '{keyword}': {len(test_results)}개 결과 확인[/green]")
            else:
                replacement_needed.append(keyword)
                logger.info(
                    f"[yellow]✗ '{keyword}': 결과 부족 ({len(test_results)}개)[/yellow]"
                )

        except Exception as e:
            logger.info(f"[red]! '{keyword}' 검증 중 오류: {e}[/red]")
            replacement_needed.append(keyword)

    # 대체 키워드 생성이 필요한 경우
    if replacement_needed and validated_keywords:
        logger.info(
            f"[yellow]{len(replacement_needed)}개 키워드에 대한 대체 키워드 생성 중...[/yellow]"
        )

        # 이 부분도 수정 필요 - domain 변수가 함수 내에서 접근할 수 없음
        new_keywords: list[str] = []  # 임시 빈 리스트로 대체

        validated_keywords.extend(new_keywords)

    return validated_keywords[:count]  # 원래 요청한 개수만큼 반환


def extract_common_theme_from_keywords(
    keywords: Any,
    api_key: str | None = None,
    callbacks: list[Any] | None = None,
) -> str:
    """Extracts a common theme from a list of keywords using configured LLM."""
    if not keywords:
        return "General News"

    # Check if any API keys are available before attempting LLM calls
    if not api_key:
        api_key = config.GEMINI_API_KEY

    # Also check for other API keys that might be used by LLM factory
    has_any_api_key = (
        api_key
        or getattr(config, "OPENAI_API_KEY", None)
        or getattr(config, "ANTHROPIC_API_KEY", None)
    )

    if not has_any_api_key:
        logger.warning("API 키가 없습니다. 테마 추출을 위한 간단한 대체 방법을 사용합니다.")
        return extract_common_theme_fallback(keywords)

    try:
        # LLM 팩토리를 사용하여 테마 추출에 최적화된 모델 사용
        try:
            from langchain_core.output_parsers import StrOutputParser
            from langchain_core.prompts import PromptTemplate

            from .llm_factory import get_llm_for_task

            if callbacks is None:
                callbacks = []
            if os.environ.get("ENABLE_COST_TRACKING"):
                try:
                    from .cost_tracking import get_tracking_callbacks

                    callbacks += get_tracking_callbacks()
                except Exception as e:
                    logging.warning(f"get_tracking_callbacks 예외 발생: {e}")

            llm = get_llm_for_task("theme_extraction", callbacks, enable_fallback=False)

            prompt_template = PromptTemplate.from_template(
                """다음 키워드들의 공통 분야나 주제를 한국어로 추출해 주세요:
                {keywords}

                출력 형식:
                - 공통 분야/주제만 간결하게 답변해 주세요 (3단어 이내)
                - 설명이나 부가 정보는 포함하지 마세요
                - 반드시 한국어로 답변해 주세요"""
            )

            chain = prompt_template | llm | StrOutputParser()
            extracted_theme = chain.invoke({"keywords": ", ".join(keywords)})

            if len(extracted_theme) > 30:
                extracted_theme = extracted_theme[:30]

            return str(extracted_theme).strip()

        except Exception as e:
            logger.warning(f"LLM 팩토리를 통한 테마 추출이 실패했습니다. 대체 방법을 사용합니다: {e}")
            # Check if API key is available before trying Gemini fallback
            if not api_key:
                logger.warning("GEMINI_API_KEY를 찾을 수 없습니다. 테마 추출을 위한 간단한 대체 방법을 사용합니다.")
                return extract_common_theme_fallback(keywords)

        # Fallback using LangChain Google GenAI
        from langchain_core.messages import HumanMessage as FallbackHumanMessage

        from .llm_factory import get_llm_for_task

        try:
            llm = get_llm_for_task("theme_extraction", callbacks, enable_fallback=True)

            final_prompt = f"""
다음 키워드들의 공통 분야나 주제를 한국어로 추출해 주세요:
{', '.join(keywords)}

출력 형식:
- 공통 분야/주제만 간결하게 답변해 주세요 (3단어 이내)
- 설명이나 부가 정보는 포함하지 마세요
- 반드시 한국어로 답변해 주세요
"""

            response = llm.invoke([FallbackHumanMessage(content=final_prompt)])
            extracted_theme = str(response.content).strip()

            if len(extracted_theme) > 30:  # Keep the length check
                extracted_theme = extracted_theme[:30]

            return extracted_theme

        except Exception as llm_error:
            logger.warning(f"LLM factory를 통한 테마 추출이 실패했습니다: {llm_error}")
            return extract_common_theme_fallback(keywords)

    except Exception as e:
        logger.error(f"테마 추출 중 오류 발생: {e}")
        return extract_common_theme_fallback(keywords)


def get_filename_safe_theme(keywords: Any, domain: str | None = None) -> str:
    """
    키워드 또는 도메인에서 파일명에 안전한 테마 문자열을 생성합니다.

    Args:
        keywords: 키워드 리스트 또는 문자열
        domain: 도메인 (있는 경우)

    Returns:
        파일명에 적합한 테마 문자열
    """
    theme = resolve_filename_theme(
        keywords,
        domain,
        theme_extractor=extract_common_theme_from_keywords,
    )
    return sanitize_filename(theme)


def regenerate_section_with_gemini(section_title: str, news_links: list) -> list:
    """
    구성된 LLM을 사용하여 뉴스 링크 목록으로부터 섹션 요약문을 재생성합니다.

    Args:
        section_title: 섹션 제목
        news_links: 뉴스 링크 정보 목록 (title, url, source_and_date 포함)

    Returns:
        list: 생성된 요약문 문단 목록
    """
    # LLM 팩토리를 사용하여 섹션 재생성에 최적화된 모델 사용
    try:
        from langchain_core.messages import HumanMessage

        from .llm_factory import get_llm_for_task

        llm = get_llm_for_task("section_regeneration", enable_fallback=False)

        # 뉴스 링크 정보를 문자열로 변환
        news_links_text = ""
        for i, link in enumerate(news_links, 1):
            title = (
                str(link.get("title", "No Title")).replace("{", "{{").replace("}", "}}")
            )
            source = (
                str(link.get("source_and_date", "Unknown Source"))
                .replace("{", "{{")
                .replace("}", "}}")
            )
            url = str(link.get("url", "#")).replace("{", "{{").replace("}", "}}")

            news_links_text += f"기사 {i}:\n"
            news_links_text += f"제목: {title}\n"
            news_links_text += f"출처: {source}\n"
            news_links_text += f"URL: {url}\n\n"

        prompt = f"""
        다음은 '{section_title}'에 관련된 뉴스 기사 목록입니다:

        {news_links_text}

        위 뉴스 기사들을 바탕으로 '{section_title}'에 대한 종합적인 요약문을 작성해주세요.

        요구사항:
        1. 1개의 문단으로 나누어 작성해주세요. 각 문단은 최소 3-4문장 이상으로 구성해주세요.
        2. 문단은 주요 트렌드나 동향을 설명해주세요.
        5. 전문적이고 객관적인 톤으로 작성해주세요.
        6. 한국어로 작성해주세요.
        7. 각 문단은 별도의 문자열로 반환해주세요 (리스트 형태).
        """

        response = llm.invoke([HumanMessage(content=prompt)])
        response_text = response.content.strip()

        # 문단으로 분리
        paragraphs = [p.strip() for p in response_text.split("\n\n") if p.strip()]

        # 최소 3개의 문단 확보
        while len(paragraphs) < 3:
            paragraphs.append("추가 정보가 필요합니다.")

        # 최대 3개 문단으로 제한
        return paragraphs[:3]

    except Exception as e:
        logger.warning(f"LLM 팩토리를 통한 섹션 재생성이 실패했습니다. 대체 방법을 사용합니다: {e}")

    # Fallback using LangChain Google GenAI
    from langchain_core.messages import HumanMessage

    from .llm_factory import get_llm_for_task

    try:
        llm = get_llm_for_task("section_regeneration", enable_fallback=True)
    except Exception as e:
        raise ValueError(f"LLM factory 초기화 실패: {e}")

    # 뉴스 링크 정보를 문자열로 변환 - 수정된 형식으로
    news_links_text = ""
    for i, link in enumerate(news_links, 1):
        title = str(link.get("title", "No Title")).replace("{", "{{").replace("}", "}}")
        source = (
            str(link.get("source_and_date", "Unknown Source"))
            .replace("{", "{{")
            .replace("}", "}}")
        )
        url = str(link.get("url", "#")).replace("{", "{{").replace("}", "}}")

        news_links_text += f"기사 {i}:\n"
        news_links_text += f"제목: {title}\n"
        news_links_text += f"출처: {source}\n"
        news_links_text += f"URL: {url}\n\n"

    # 프롬프트 구성
    prompt = f"""
    다음은 '{section_title}'에 관련된 뉴스 기사 목록입니다:

    {news_links_text}

    위 뉴스 기사들을 바탕으로 '{section_title}'에 대한 종합적인 요약문을 작성해주세요.

    요구사항:
    1. 3개의 문단으로 나누어 작성해주세요. 각 문단은 최소 3-4문장 이상으로 구성해주세요.
    2. 첫 번째 문단은 주요 트렌드나 동향을 설명해주세요.
    3. 두 번째 문단은 주요 이슈나 구체적인 사례를 다루어주세요.
    4. 세 번째 문단은 시사점이나 전망을 제시해주세요.
    5. 전문적이고 객관적인 톤으로 작성해주세요.
    6. 한국어로 작성해주세요.
    7. 각 문단은 별도의 문자열로 반환해주세요 (리스트 형태).
    """

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        response_text = response.content.strip()

        # 문단으로 분리
        paragraphs = [p.strip() for p in response_text.split("\n\n") if p.strip()]

        # 최소 3개의 문단 확보
        while len(paragraphs) < 3:
            paragraphs.append("추가 정보가 필요합니다.")

        # 최대 3개 문단으로 제한
        return paragraphs[:3]

    except Exception as e:
        import traceback

        logger.error(f"LLM을 사용한 콘텐츠 생성 중 오류 발생: {e}")
        logger.debug(f"오류 세부 정보: {traceback.format_exc()}")
        return [
            "요약 생성 중 오류가 발생했습니다.",
            "추가 정보가 필요합니다.",
            "더 자세한 분석이 필요합니다.",
        ]


def generate_introduction_with_gemini(
    newsletter_topic: str, section_titles: list
) -> str:
    """
    구성된 LLM을 사용하여 뉴스레터 주제와 섹션 제목을 기반으로 소개 메시지를 생성합니다.

    Args:
        newsletter_topic: 뉴스레터 주제
        section_titles: 섹션 제목 목록

    Returns:
        str: 생성된 소개 메시지
    """
    # LLM 팩토리를 사용하여 소개 생성에 최적화된 모델 사용
    try:
        from langchain_core.messages import HumanMessage

        from .llm_factory import get_llm_for_task

        llm = get_llm_for_task("introduction_generation", enable_fallback=False)

        # 섹션 제목을 문자열로 변환
        safe_topic = str(newsletter_topic).replace("{", "{{").replace("}", "}}")
        section_titles_text = ""
        for i, title in enumerate(section_titles, 1):
            safe_title = str(title).replace("{", "{{").replace("}", "}}")
            section_titles_text += f"- {safe_title}\n"

        prompt = f"""
        다음은 뉴스레터의 주제와 포함된 섹션 제목들입니다:

        뉴스레터 주제: {safe_topic}

        섹션 제목:
        {section_titles_text}

        위 정보를 바탕으로 뉴스레터의 소개 메시지를 작성해주세요.

        요구사항:
        1. 전문적이고 친절한 톤으로 작성해주세요.
        2. 2-3 문장으로 간결하게 작성해주세요.
        3. 이번 뉴스레터의 가치와 중요성을 강조해주세요.
        4. 한국어로 작성해주세요.
        5. 각 섹션의 핵심 내용이 무엇인지 간략히 언급해주세요.
        6. 'R&D 전략 수립' 또는 '의사결정'에 도움이 될 수 있다는 점을 언급해주세요.

        소개 메시지만 반환해 주세요.
        """

        response = llm.invoke([HumanMessage(content=prompt)])
        return str(response.content).strip()

    except Exception as e:
        logger.warning(f"LLM 팩토리를 통한 소개 생성이 실패했습니다. 대체 방법을 사용합니다: {e}")
        # Fallback using LangChain Google GenAI
        from .llm_factory import get_llm_for_task

        try:
            llm = get_llm_for_task("introduction_generation", enable_fallback=True)
        except Exception as e:
            raise ValueError(f"LLM factory 초기화 실패: {e}")

    # 섹션 제목을 문자열로 변환
    safe_topic = str(newsletter_topic).replace("{", "{{").replace("}", "}}")
    section_titles_text = ""
    for i, title in enumerate(section_titles, 1):
        safe_title = str(title).replace("{", "{{").replace("}", "}}")
        section_titles_text += f"- {safe_title}\n"

    # 프롬프트 구성
    prompt = f"""
    다음은 뉴스레터의 주제와 포함된 섹션 제목들입니다:

    뉴스레터 주제: {safe_topic}

    섹션 제목:
    {section_titles_text}

    위 정보를 바탕으로 뉴스레터의 소개 메시지를 작성해주세요.

    요구사항:
    1. 전문적이고 친절한 톤으로 작성해주세요.
    2. 2-3 문장으로 간결하게 작성해주세요.
    3. 이번 뉴스레터의 가치와 중요성을 강조해주세요.
    4. 한국어로 작성해주세요.
    5. 각 섹션의 핵심 내용이 무엇인지 간략히 언급해주세요.
    6. 'R&D 전략 수립' 또는 '의사결정'에 도움이 될 수 있다는 점을 언급해주세요.

    소개 메시지만 반환해 주세요.
    """

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        introduction = str(response.content).strip()

        return introduction
    except Exception as e:
        import traceback

        logger.error(f"LLM을 사용한 소개 생성 중 오류 발생: {e}")
        logger.debug(f"오류 세부 정보: {traceback.format_exc()}")
        return f"금주 {safe_topic} 관련 최신 동향과 주요 뉴스를 정리하여 제공합니다. 본 뉴스레터가 업무에 도움이 되기를 바랍니다."
