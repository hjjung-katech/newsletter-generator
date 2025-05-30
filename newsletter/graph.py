"""
Newsletter Generator - LangGraph Workflow
이 모듈은 LangGraph를 사용하여 뉴스레터 생성 워크플로우를 정의합니다.
"""

import json
import os  # Added import
import re  # Added import for regex date parsing
import time
from datetime import datetime, timedelta, timezone  # Added imports
from typing import Annotated, Any, Dict, List, Literal, Optional, Tuple, TypedDict

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from pydantic.v1 import BaseModel, Field  # Updated import for Pydantic v1 compatibility

from . import collect as news_collect
from . import config
from .chains import get_newsletter_chain
from .date_utils import parse_date_string
from .utils.file_naming import generate_unified_newsletter_filename
from .utils.logger import get_logger

# 로거 초기화
logger = get_logger()


# State 정의
class NewsletterState(TypedDict):
    """뉴스레터 생성 과정의 상태를 정의하는 클래스"""

    # 입력 값
    keywords: List[str]
    news_period_days: int  # Configurable days for news recency filter
    domain: str  # Added domain field
    template_style: str  # Template style: 'compact' or 'detailed'
    email_compatible: bool  # Email compatibility processing flag
    # 중간 결과물
    collected_articles: Optional[List[Dict]]  # Made Optional
    processed_articles: Optional[List[Dict]]  # New field
    ranked_articles: Optional[List[Dict]]  # Articles scored and ranked
    article_summaries: Optional[Dict]  # Made Optional
    category_summaries: Optional[Dict]  # 카테고리별 요약 결과
    newsletter_topic: Optional[str]  # 뉴스레터 주제 필드
    # 최종 결과물
    newsletter_html: Optional[str]  # Made Optional
    # 제어 및 메타데이터
    error: Optional[str]  # Made Optional
    status: str  # 'collecting', 'processing', 'summarizing', 'composing', 'complete', 'error'
    start_time: float
    step_times: Dict[str, float]
    total_time: Optional[float]


# Store info about the most recent generation for inspection
_last_generation_info: Dict[str, Any] = {}


def get_last_generation_info() -> Dict[str, Any]:
    """Return metrics from the most recent newsletter generation."""
    return _last_generation_info


# Helper function to parse article dates
def parse_article_date_for_graph(date_str: Any) -> Optional[datetime]:
    """
    다양한 형식의 날짜 문자열을 파싱하여 datetime 객체로 변환합니다.
    date_utils 모듈의 parse_date_string 함수를 사용하여 일관된 날짜 처리를 지원합니다.

    Args:
        date_str: 변환할 날짜 문자열

    Returns:
        datetime 객체 또는 변환 실패 시 None
    """
    return parse_date_string(date_str)


# 노드 함수 정의
def collect_articles_node(
    state: NewsletterState,
) -> NewsletterState:  # Renamed for clarity
    """
    키워드를 기반으로 기사를 수집하는 노드
    """
    from .tools import search_news_articles

    logger.info("\n[cyan]Step: Collecting articles...[/cyan]")
    start_time = time.time()

    try:
        keyword_str = ", ".join(state["keywords"])
        articles = search_news_articles.invoke(
            {"keywords": keyword_str, "num_results": 10}
        )

        step_times = state.get("step_times", {})
        step_times["collect_articles"] = time.time() - start_time
        return {
            **state,
            "collected_articles": articles,
            "status": "processing",  # Next status is processing
            "step_times": step_times,
        }
    except Exception as e:
        logger.error(f"[red]Error during article collection: {e}[/red]")
        step_times = state.get("step_times", {})
        step_times["collect_articles"] = time.time() - start_time
        return {
            **state,
            "collected_articles": [],  # Ensure it's an empty list on error
            "error": f"기사 수집 중 오류 발생: {str(e)}",
            "status": "error",
            "step_times": step_times,
        }


# New node for processing articles
def process_articles_node(state: NewsletterState) -> NewsletterState:
    logger.info(
        "\n[cyan]Step: Processing collected articles (filtering, sorting, deduplicating)...[/cyan]"
    )
    start_time = time.time()
    collected_articles = state.get("collected_articles")

    if not collected_articles or not isinstance(collected_articles, list):
        logger.warning(
            "[yellow]Warning: No articles collected or 'collected_articles' is not a list. Skipping processing.[/yellow]"
        )
        step_times = state.get("step_times", {})
        step_times["process_articles"] = time.time() - start_time
        return {
            **state,
            "processed_articles": [],
            "error": "수집된 기사가 없거나 형식이 잘못되어 처리할 수 없습니다.",
            "status": "error",
            "step_times": step_times,
        }

    logger.info(f"Total articles received for processing: {len(collected_articles)}")

    output_dir = os.path.join(os.getcwd(), "output", "intermediate_processing")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_output_filename = f"{timestamp}_articles_raw.json"
    raw_output_path = os.path.join(output_dir, raw_output_filename)
    try:
        # Create a dictionary that includes metadata for raw articles too
        raw_data_with_metadata = {
            "keywords": state.get("keywords", []),
            "domain": state.get("domain"),
            "news_period_days": state.get("news_period_days", 14),
            "articles": collected_articles,
        }

        with open(raw_output_path, "w", encoding="utf-8") as f:
            json.dump(raw_data_with_metadata, f, ensure_ascii=False, indent=4)
        logger.info(f"Saved raw collected articles to {raw_output_path}")
    except Exception as e:
        logger.error(f"[red]Error saving raw articles: {e}[/red]")
    now_utc = datetime.now(timezone.utc)
    news_period_days = state.get("news_period_days", 14)  # 기본값은 14일(2주)로 설정
    news_period_ago_utc = now_utc - timedelta(days=news_period_days)

    recent_articles = []
    articles_with_date = (
        0  # Count of articles where a date string was present and parsing was attempted
    )
    articles_missing_date = (
        0  # Count of articles where date string was initially missing
    )
    articles_unparseable_date = (
        0  # Count of articles where date string was present but unparseable
    )

    # Counters for articles kept or discarded
    articles_kept_recent_date = 0
    articles_kept_missing_date = 0
    articles_kept_unparseable_date = 0
    articles_discarded_old_date = 0

    for article in collected_articles:
        if not isinstance(article, dict):
            logger.warning(
                f"Warning: Skipping non-dictionary item in collected_articles: {article}"
            )
            continue

        article_title_for_log = article.get("title", "N/A")  # For cleaner logs
        article_date_str = article.get("date")

        if not article_date_str or str(article_date_str).strip() == "날짜 없음":
            articles_missing_date += 1
            logger.info(
                f"Debug: Article has missing date: '{article_title_for_log}'. Including by default."
            )
            recent_articles.append(article)
            articles_kept_missing_date += 1
            continue  # Process next article

        # At this point, article_date_str is present and not "날짜 없음"
        article_date_obj = parse_article_date_for_graph(article_date_str)

        if article_date_obj:
            articles_with_date += 1  # Incremented because parsing was successful
            # Ensure timezone-aware comparison
            if (
                article_date_obj.tzinfo is None
                or article_date_obj.tzinfo.utcoffset(article_date_obj) is None
            ):
                # Assuming naive datetimes from parsing are UTC. Adjust if this assumption is wrong.
                article_date_obj = article_date_obj.replace(tzinfo=timezone.utc)
            if article_date_obj >= news_period_ago_utc:
                recent_articles.append(article)
                articles_kept_recent_date += 1
            else:
                articles_discarded_old_date += 1
                logger.info(
                    f"Debug: Article too old: '{article_title_for_log}', Date: {article_date_obj.isoformat()}. Discarding."
                )
        else:
            # article_date_str was present, but parse_article_date_for_graph returned None
            articles_unparseable_date += 1
            logger.info(
                f"Debug: Article with unparseable date: '{article_title_for_log}', Date string: '{article_date_str}'. Including by default."
            )
            recent_articles.append(article)
            articles_kept_unparseable_date += 1

    logger.info(f"\nArticle date processing summary:")
    logger.info(f"  Total collected articles: {len(collected_articles)}")
    logger.info(
        f"  Articles with a date string provided: {articles_with_date + articles_unparseable_date}"
    )
    logger.info(f"    Successfully parsed dates: {articles_with_date}")
    logger.info(f"    Unparseable date strings: {articles_unparseable_date}")
    logger.info(
        f"  Articles with missing date string (initially): {articles_missing_date}"
    )
    logger.info(
        f"  Total articles included for further processing (recent_articles): {len(recent_articles)}"
    )
    logger.info(f"    Kept (recent with valid date): {articles_kept_recent_date}")
    logger.info(f"    Kept (due to missing date): {articles_kept_missing_date}")
    logger.info(f"    Kept (due to unparseable date): {articles_kept_unparseable_date}")
    logger.info(
        f"  Articles discarded (parseable but too old): {articles_discarded_old_date}\n"
    )

    if not recent_articles:
        logger.warning(
            "[yellow]Warning: No articles retained after recency filter.[/yellow]"
        )
        # Optionally, save an empty processed file or skip
        processed_output_filename = f"{timestamp}_articles_processed_EMPTY.json"
        processed_output_path = os.path.join(output_dir, processed_output_filename)
        try:
            with open(processed_output_path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=4)
            logger.info(
                f"Saved empty processed articles list to {processed_output_path}"
            )
        except Exception as e:
            logger.error(f"[red]Error saving empty processed articles list: {e}[/red]")

        return {
            **state,
            "processed_articles": [],
            "error": f"최근 {news_period_days}일 내 기사가 없거나, 기사 날짜 정보를 파싱할 수 없어 요약할 내용이 없습니다.",
            "status": "error",
        }

    unique_articles_dict = {}
    for article in recent_articles:
        url = article.get("url")
        # Ensure URL is a string and not empty before processing
        if url and isinstance(url, str) and url.strip():
            normalized_url = (
                url.lower().strip().rstrip("/")
            )  # Normalize by lowercasing and removing trailing slash
            if normalized_url not in unique_articles_dict:
                unique_articles_dict[normalized_url] = article
            else:
                logger.info(
                    f"Debug: Deduplicated article (URL already seen): {article.get('title', 'N/A')}, URL: {url}"
                )
        else:
            logger.warning(
                f"Warning: Article missing URL or URL is not a string, cannot deduplicate: {article.get('title', 'N/A')}"
            )
            # Decide how to handle articles without URLs: include them, or skip them for deduplication.
            # For now, let's include them if they passed the date filter, but they won't be part of URL-based deduplication.
            # To ensure they are added if no URL, generate a unique key or handle separately.
            # A simple way: if no URL, use a unique ID if available, or just add it (might lead to duplicates if content is same but no URL)
            # For this implementation, if no valid URL, it won't be added to unique_articles_dict, effectively skipping it from deduplicated list.
            # If you want to keep them, you'd need a different strategy.

    deduplicated_articles = list(unique_articles_dict.values())
    logger.info(f"Retained {len(deduplicated_articles)} articles after deduplication.")

    if not deduplicated_articles:
        logger.warning(
            "[yellow]Warning: No articles retained after deduplication.[/yellow]"
        )
        # Optionally, save an empty processed file or skip
        processed_output_filename = f"{timestamp}_articles_processed_EMPTY_DEDUP.json"
        processed_output_path = os.path.join(output_dir, processed_output_filename)
        try:
            with open(processed_output_path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=4)
            logger.info(
                f"Saved empty processed articles list (post-dedup) to {processed_output_path}"
            )
        except Exception as e:
            logger.error(f"[red]Error saving empty processed articles list: {e}[/red]")

        return {
            **state,
            "processed_articles": [],
            "error": "기사 중복 제거 후 요약할 내용이 없습니다.",
            "status": "error",
        }

    def get_sort_key(article_dict_item: Dict) -> datetime:
        dt = parse_article_date_for_graph(article_dict_item.get("date"))
        if dt:
            if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        return datetime.min.replace(tzinfo=timezone.utc)

    processed_articles_sorted = sorted(
        deduplicated_articles, key=get_sort_key, reverse=True
    )
    logger.info(f"Sorted {len(processed_articles_sorted)} articles by date.")

    processed_output_filename = f"{timestamp}_articles_processed.json"
    processed_output_path = os.path.join(output_dir, processed_output_filename)
    try:
        # Create a dictionary that includes metadata
        processed_data_with_metadata = {
            "keywords": state.get("keywords", []),
            "domain": state.get("domain"),
            "news_period_days": state.get("news_period_days", 14),
            "articles": processed_articles_sorted,
        }

        with open(processed_output_path, "w", encoding="utf-8") as f:
            json.dump(processed_data_with_metadata, f, ensure_ascii=False, indent=4)
        logger.info(
            f"Saved processed articles with metadata to {processed_output_path}"
        )
    except Exception as e:
        logger.error(f"[red]Error saving processed articles: {e}[/red]")

    step_times = state.get("step_times", {})
    step_times["process_articles"] = time.time() - start_time
    return {
        **state,
        "processed_articles": processed_articles_sorted,
        "status": "scoring",  # Next step is scoring
        "step_times": step_times,
    }


def score_articles_node(state: NewsletterState) -> NewsletterState:
    """Score articles using LLM to rank priority."""
    from .scoring import load_scoring_weights_from_config, score_articles

    logger.info("\n[cyan]Step: Scoring articles...[/cyan]")
    start_time = time.time()

    processed = state.get("processed_articles") or []
    if not processed:
        logger.warning("[yellow]No articles to score.[/yellow]")
        step_times = state.get("step_times", {})
        step_times["score_articles"] = time.time() - start_time
        return {
            **state,
            "error": "기사 점수를 매길 데이터가 없습니다.",
            "status": "error",
            "step_times": step_times,
        }

    domain = state.get("domain", "")
    keywords = state.get("keywords", [])
    news_period_days = state.get("news_period_days", 14)

    # Load scoring weights from config.yml
    scoring_weights = load_scoring_weights_from_config()
    logger.info(f"[cyan]Using scoring weights: {scoring_weights}[/cyan]")

    # Get full ranked list for saving; top 10 will be passed forward
    ranked = score_articles(processed, domain, top_n=None, weights=scoring_weights)

    output_dir = os.path.join(os.getcwd(), "output", "intermediate_processing")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scored_path = os.path.join(output_dir, f"{timestamp}_articles_scored.json")
    try:
        with open(scored_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "keywords": keywords,
                    "domain": domain,
                    "news_period_days": news_period_days,
                    "articles": ranked,
                },
                f,
                ensure_ascii=False,
                indent=4,
            )
        logger.info(f"Saved scored articles to {scored_path}")
    except Exception as e:
        logger.error(f"[red]Error saving scored articles: {e}[/red]")

    step_times = state.get("step_times", {})
    step_times["score_articles"] = time.time() - start_time
    return {
        **state,
        "ranked_articles": ranked[:10],
        "status": "summarizing",
        "step_times": step_times,
    }


def summarize_articles_node(
    state: NewsletterState,
) -> NewsletterState:  # Renamed for clarity
    """
    수집된 기사를 요약하는 노드
    """
    import os

    from .chains import get_newsletter_chain

    logger.info("\n[cyan]Step: Summarizing articles...[/cyan]")
    start_time = time.time()

    articles_for_summary = state.get("ranked_articles") or state.get(
        "processed_articles"
    )
    if not articles_for_summary:
        logger.warning("[yellow]No articles to summarize.[/yellow]")
        step_times = state.get("step_times", {})
        step_times["summarize_articles"] = time.time() - start_time
        return {
            **state,
            "error": "요약할 기사가 없습니다.",
            "status": "error",
            "step_times": step_times,
        }

    template_style = state.get("template_style", "compact")

    try:
        # 비용 추적 설정 (ENABLE_COST_TRACKING 환경 변수 설정된 경우에만)
        callbacks = []

        if os.environ.get("ENABLE_COST_TRACKING") or os.environ.get(
            "LANGCHAIN_TRACING_V2"
        ):
            try:
                from .cost_tracking import (
                    get_tracking_callbacks,
                    register_recent_callbacks,
                )

                callbacks = get_tracking_callbacks()
                register_recent_callbacks(callbacks)
            except Exception as e:
                logger.warning(
                    f"[yellow]Cost tracking setup error: {e}. Continuing without tracking.[/yellow]"
                )

        # template_style에 따라 compact 또는 detailed 체인 사용
        is_compact = template_style == "compact"

        if is_compact:
            logger.info(
                "[cyan]Using compact processing - running compact newsletter chain...[/cyan]"
            )
        else:
            logger.info(
                "[cyan]Using detailed processing - running full summarization chain...[/cyan]"
            )

        # 통합된 체인 가져오기 및 실행
        newsletter_chain = get_newsletter_chain(is_compact=is_compact)

        # 데이터 형식 맞추기: processed_articles를 'articles' 키를 가진 딕셔너리로 감싸기
        input_data = {
            "articles": articles_for_summary,
            "keywords": state.get("keywords", ""),
            "email_compatible": state.get("email_compatible", False),
            "template_style": state.get("template_style", "compact"),
            "domain": state.get("domain"),
        }

        chain_result = newsletter_chain.invoke(input_data)

        # chains에서 반환되는 새로운 형태 처리
        if isinstance(chain_result, dict) and "html" in chain_result:
            # 새로운 형태: {"html": ..., "structured_data": ..., "sections": ..., "mode": ...}
            category_summaries = chain_result["structured_data"]
            html_content = chain_result["html"]
            sections = chain_result.get("sections", [])

            logger.info(
                f"[green]Successfully processed {chain_result['mode']} mode newsletter[/green]"
            )
            logger.info(
                f"[cyan]Structured data keys: {list(category_summaries.keys())}[/cyan]"
            )
        elif isinstance(chain_result, str):
            # 기존 형태: HTML 문자열 (하위 호환성)
            category_summaries = chain_result
            html_content = chain_result
            sections = []
            logger.info(f"[yellow]Received HTML string (legacy format)[/yellow]")
        else:
            # 예상치 못한 형태
            logger.error(
                f"[red]Unexpected chain result type: {type(chain_result)}[/red]"
            )
            category_summaries = chain_result
            html_content = None
            sections = []

        if not category_summaries:
            return {
                **state,
                "error": "카테고리 요약 생성에 실패했습니다.",
                "status": "error",
            }

        step_times = state.get("step_times", {})
        step_times["summarize_articles"] = time.time() - start_time
        return {
            **state,
            "category_summaries": category_summaries,
            "newsletter_html": html_content,  # 생성된 HTML도 저장
            "sections": sections,  # sections 데이터 추가
            "status": "composing",  # Changed to composing to indicate next step
            "step_times": step_times,
        }
    except Exception as e:
        import traceback

        error_msg = f"기사 요약 중 오류가 발생했습니다: {str(e)}"
        logger.error(f"[bold red]Error in summarization: {str(e)}[/bold red]")
        traceback.print_exc()
        step_times = state.get("step_times", {})
        step_times["summarize_articles"] = time.time() - start_time
        return {
            **state,
            "error": error_msg,
            "status": "error",
            "step_times": step_times,
        }


def compose_newsletter_node(
    state: NewsletterState,
) -> NewsletterState:
    """
    카테고리 요약에서 최종 뉴스레터 HTML을 생성하는 노드
    """
    import os
    from datetime import datetime  # Import datetime for timestamp

    from .compose import compose_newsletter

    logger.info("\n[cyan]Step: Composing final newsletter...[/cyan]")
    start_time = time.time()

    category_summaries = state.get("category_summaries")
    if not category_summaries:
        logger.warning("[yellow]No category summaries to compose newsletter.[/yellow]")
        step_times = state.get("step_times", {})
        step_times["compose_newsletter"] = time.time() - start_time
        return {
            **state,
            "error": "카테고리 요약이 없어 뉴스레터를 생성할 수 없습니다.",
            "status": "error",
            "step_times": step_times,
        }

    try:
        # 변수들을 조건문 외부에서 미리 정의
        template_style = state.get("template_style", "compact")
        email_compatible = state.get("email_compatible", False)

        # 이미 생성된 HTML이 있는지 확인 (summarize_articles_node에서 생성된 경우)
        newsletter_html = state.get("newsletter_html")

        if newsletter_html:
            logger.info(f"[cyan]Using pre-generated HTML from chains[/cyan]")
        else:
            # HTML이 없으면 직접 생성
            if isinstance(category_summaries, str):
                # If it's already HTML, just use it
                newsletter_html = category_summaries
            else:
                # If it's structured data, render with appropriate template using unified function
                template_dir = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), "templates"
                )

                # email_compatible인 경우 원래 template_style 정보를 데이터에 포함
                if email_compatible:
                    # 데이터에 template_style 정보 추가 (compose.py에서 사용)
                    if isinstance(category_summaries, dict):
                        category_summaries["template_style"] = template_style

                    effective_style = "email_compatible"
                    logger.info(
                        f"[cyan]Using email-compatible template with {template_style} content style...[/cyan]"
                    )
                else:
                    effective_style = template_style
                    logger.info(
                        f"[cyan]Using {template_style} newsletter template...[/cyan]"
                    )

                newsletter_html = compose_newsletter(
                    category_summaries, template_dir, effective_style
                )

        # 뉴스레터 HTML 저장
        def save_newsletter_html(html_content, topic, style):
            """
            생성된 뉴스레터 HTML을 파일로 저장합니다.

            Args:
                html_content: 저장할 HTML 내용
                topic: 뉴스레터 주제 (파일명 생성에 사용)
                style: 템플릿 스타일 (파일명에 추가)

            Returns:
                str: 저장된 파일 경로
            """
            # 통일된 파일명 생성 함수 사용
            from .utils.file_naming import generate_unified_newsletter_filename

            # 현재 타임스탬프 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 통일된 파일명으로 경로 생성
            file_path = generate_unified_newsletter_filename(
                topic=topic,
                style=style,
                timestamp=timestamp,
                use_current_date=True,
                generation_type="original",
            )

            # 파일 저장
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.info(f"[green]Newsletter saved to {file_path}[/green]")
            return file_path

        # 뉴스레터 저장
        newsletter_topic = state.get("newsletter_topic", "뉴스레터")
        save_path = save_newsletter_html(
            newsletter_html, newsletter_topic, template_style
        )

        # 렌더 데이터 저장 (재사용 및 테스트용)
        def save_render_data(state_data, topic, timestamp_override=None):
            """
            뉴스레터 렌더링 데이터를 JSON 파일로 저장합니다.

            Args:
                state_data: 저장할 상태 데이터
                topic: 뉴스레터 주제
                timestamp_override: 선택적 타임스탬프 덮어쓰기

            Returns:
                str: 저장된 파일 경로
            """
            from .utils.file_naming import generate_render_data_filename

            # 타임스탬프 생성 (통일성을 위해 같은 시간 사용)
            if timestamp_override:
                timestamp = timestamp_override
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 렌더 데이터 파일 경로 생성
            render_data_path = generate_render_data_filename(topic, timestamp)

            # 현재 시간 정보
            current_date = datetime.now().strftime("%Y-%m-%d")
            current_time = datetime.now().strftime("%H:%M:%S")

            # 저장할 렌더 데이터 구성 (template 모드에서 재사용 가능한 형태)
            render_data = {
                "newsletter_topic": state_data.get("newsletter_topic", topic),
                "generation_date": current_date,
                "generation_timestamp": current_time,
                "search_keywords": state_data.get("keywords", []),
                "domain": state_data.get("domain"),
                "template_style": state_data.get("template_style", "compact"),
                "news_period_days": state_data.get("news_period_days", 14),
                # 카테고리 요약 데이터를 sections로 변환
                "sections": [],
                # top_articles 추가
                "top_articles": [],
                # grouped_sections 추가 (compact 모드용)
                "grouped_sections": [],
                # definitions 추가
                "definitions": [],
                # food_for_thought 추가
                "food_for_thought": {},
                # 기본 메타데이터 - LLM 생성 내용이 있으면 우선 사용
                "recipient_greeting": "안녕하세요,",
                "closing_message": "다음 주에 더 유익한 정보로 찾아뵙겠습니다. 감사합니다.",
                "editor_signature": "편집자 드림",
                "company_name": "산업통상자원 R&D 전략기획단",
                "copyright_year": datetime.now().strftime("%Y"),
                "company_tagline": "최신 기술 동향을 한눈에",
                "footer_contact": "문의사항: hjjung2@osp.re.kr",
                "footer_disclaimer": "이 뉴스레터는 정보 제공을 목적으로 하며, 내용의 정확성을 보장하지 않습니다.",
                "editor_name": "Google Gemini",
                "editor_email": "hjjung2@osp.re.kr",
            }

            # category_summaries에서 구조화된 데이터 추출
            category_summaries = state_data.get("category_summaries", {})
            sections_from_state = state_data.get("sections", [])

            logger.info(
                f"[cyan]Debug: category_summaries type: {type(category_summaries)}[/cyan]"
            )
            logger.info(
                f"[cyan]Debug: sections from state: {len(sections_from_state)} sections[/cyan]"
            )

            # structured_data에서 완전한 정보 추출
            if isinstance(category_summaries, dict):
                # LLM이 생성한 내용들을 우선 사용
                for key in [
                    "newsletter_topic",
                    "generation_date",
                    "recipient_greeting",
                    "introduction_message",
                    "closing_message",
                    "editor_signature",
                    "company_name",
                ]:
                    if key in category_summaries:
                        render_data[key] = category_summaries[key]
                        logger.info(
                            f"[green]LLM 생성 내용 사용: {key} = {category_summaries[key][:100] if isinstance(category_summaries[key], str) and len(category_summaries[key]) > 100 else category_summaries[key]}[/green]"
                        )

                # food_for_thought 추출
                if "food_for_thought" in category_summaries:
                    render_data["food_for_thought"] = category_summaries[
                        "food_for_thought"
                    ]
                    logger.info(f"[green]Found food_for_thought[/green]")

                # top_articles 추출
                if "top_articles" in category_summaries:
                    render_data["top_articles"] = category_summaries["top_articles"]
                    logger.info(
                        f"[green]Found top_articles: {len(render_data['top_articles'])} articles[/green]"
                    )

                # grouped_sections 추출 (compact 모드)
                if "grouped_sections" in category_summaries:
                    render_data["grouped_sections"] = category_summaries[
                        "grouped_sections"
                    ]
                    logger.info(
                        f"[green]Found grouped_sections: {len(render_data['grouped_sections'])} groups[/green]"
                    )

                # definitions 추출
                if "definitions" in category_summaries:
                    render_data["definitions"] = category_summaries["definitions"]
                    logger.info(
                        f"[green]Found definitions: {len(render_data['definitions'])} definitions[/green]"
                    )

            # introduction_message가 없으면 주제 기반으로 생성
            if (
                "introduction_message" not in render_data
                or not render_data["introduction_message"]
            ):
                newsletter_topic = render_data.get("newsletter_topic", topic)
                render_data["introduction_message"] = (
                    f"이번 주 {newsletter_topic} 분야의 주요 동향과 기술 발전 현황을 정리하여 보내드립니다."
                )
                logger.info(
                    f"[yellow]기본 introduction_message 생성: {render_data['introduction_message']}[/yellow]"
                )

            # sections 데이터 우선순위: state의 sections > category_summaries의 sections
            if sections_from_state:
                # sections_from_state에서 완전한 정보 추출
                complete_sections = []
                for section in sections_from_state:
                    complete_section = {
                        "title": section.get("title", ""),
                        "summary_paragraphs": section.get("summary_paragraphs", []),
                        "definitions": section.get("definitions", []),
                        "news_links": section.get("news_links", []),
                    }

                    # intro 필드가 있으면 summary_paragraphs로 변환
                    if (
                        "intro" in section
                        and not complete_section["summary_paragraphs"]
                    ):
                        complete_section["summary_paragraphs"] = [section["intro"]]

                    # articles 필드가 있으면 news_links로 변환
                    if "articles" in section and not complete_section["news_links"]:
                        complete_section["news_links"] = [
                            {
                                "title": article.get("title", ""),
                                "url": article.get("url", "#"),
                                "source_and_date": article.get("source_and_date", ""),
                            }
                            for article in section.get("articles", [])
                        ]

                    complete_sections.append(complete_section)

                render_data["sections"] = complete_sections
                logger.info(
                    f"[green]Using sections from state: {len(complete_sections)} sections[/green]"
                )

                # sections에서 definitions도 추출 (아직 없는 경우)
                if not render_data["definitions"]:
                    all_definitions = []
                    for section in complete_sections:
                        all_definitions.extend(section.get("definitions", []))
                    render_data["definitions"] = all_definitions[:3]  # 최대 3개

            elif (
                isinstance(category_summaries, dict)
                and "sections" in category_summaries
            ):
                render_data["sections"] = category_summaries["sections"]
                logger.info(
                    f"[green]Found sections data in category_summaries: {len(render_data['sections'])} sections[/green]"
                )

            # 파일 저장
            try:
                with open(render_data_path, "w", encoding="utf-8") as f:
                    json.dump(render_data, f, ensure_ascii=False, indent=2)
                logger.info(
                    f"[green]Enhanced render data saved to {render_data_path}[/green]"
                )
                logger.info(
                    f"[cyan]Render data contains: {len(render_data['sections'])} sections, {len(render_data['top_articles'])} top articles, {len(render_data['definitions'])} definitions[/cyan]"
                )
                return render_data_path
            except Exception as e:
                logger.error(f"[red]Error saving render data: {e}[/red]")
                return None

        # 렌더 데이터 저장 실행
        render_data_path = save_render_data(state, newsletter_topic)

        step_times = state.get("step_times", {})
        step_times["compose_newsletter"] = time.time() - start_time
        return {
            **state,
            "newsletter_html": newsletter_html,
            "status": "complete",  # Final status
            "step_times": step_times,
        }
    except Exception as e:
        import traceback

        error_msg = f"뉴스레터 생성 중 오류가 발생했습니다: {str(e)}"
        logger.error(f"[bold red]Error in newsletter composition: {str(e)}[/bold red]")
        traceback.print_exc()
        step_times = state.get("step_times", {})
        step_times["compose_newsletter"] = time.time() - start_time
        return {
            **state,
            "error": error_msg,
            "status": "error",
            "step_times": step_times,
        }


def handle_error(state: NewsletterState) -> NewsletterState:
    """
    에러 처리 노드
    """
    logger.error(f"[오류] {state['error']}")
    return state


# 그래프 정의
def create_newsletter_graph() -> StateGraph:
    """
    뉴스레터 생성을 위한 LangGraph 워크플로우 그래프 생성
    """
    workflow = StateGraph(NewsletterState)

    # 노드 추가
    workflow.add_node("collect_articles", collect_articles_node)  # Use new name
    workflow.add_node("process_articles", process_articles_node)  # Add new node
    workflow.add_node("score_articles", score_articles_node)
    workflow.add_node("summarize_articles", summarize_articles_node)  # Use new name
    workflow.add_node(
        "compose_newsletter", compose_newsletter_node
    )  # Add new node for final composition
    workflow.add_node("handle_error", handle_error)

    # 엣지 추가 (노드 간 전환)
    workflow.add_conditional_edges(
        "collect_articles",
        lambda state: (
            "handle_error" if state.get("status") == "error" else "process_articles"
        ),  # Route to process_articles
    )
    workflow.add_conditional_edges(
        "process_articles",  # Edges from new node
        lambda state: (
            "handle_error"
            if state.get("status") == "error"
            else (
                "score_articles" if state.get("processed_articles") else "handle_error"
            )
        ),
    )
    workflow.add_conditional_edges(
        "score_articles",
        lambda state: (
            "handle_error" if state.get("status") == "error" else "summarize_articles"
        ),
    )
    workflow.add_conditional_edges(
        "summarize_articles",
        lambda state: (
            "handle_error" if state.get("status") == "error" else "compose_newsletter"
        ),
    )
    workflow.add_conditional_edges(
        "compose_newsletter",
        lambda state: "handle_error" if state.get("status") == "error" else END,
    )
    workflow.add_edge("handle_error", END)

    # 시작 노드 설정
    workflow.set_entry_point("collect_articles")

    return workflow.compile()


# 뉴스레터 생성 함수
def generate_newsletter(
    keywords: List[str],
    news_period_days: int = 14,
    domain: str = None,
    template_style: str = "compact",
    email_compatible: bool = False,
) -> Tuple[str, str]:
    """
    키워드를 기반으로 뉴스레터를 생성하는 메인 함수

    Args:
        keywords: 키워드 리스트
        news_period_days: 최신 뉴스 수집 기간(일 단위), 기본값 14일(2주)
        domain: 키워드를 생성한 도메인 (있는 경우)
        template_style: 뉴스레터 템플릿 스타일 ('compact' 또는 'detailed')
        email_compatible: 이메일 호환성 처리 적용 여부

    Returns:
        (뉴스레터 HTML, 상태)
    """
    from .cost_tracking import (
        clear_recent_callbacks,
        get_cost_summary,
        register_recent_callbacks,
    )

    clear_recent_callbacks()

    workflow_start = time.time()

    # 뉴스레터 주제 결정 (도메인, 단일 키워드, 또는 공통 주제)
    theme_start = time.time()
    newsletter_topic = ""
    if domain:
        newsletter_topic = domain  # 도메인이 있으면 도메인 사용
    elif len(keywords) == 1:
        newsletter_topic = keywords[0]  # 단일 키워드면 해당 키워드 사용
    else:
        # 여러 키워드의 공통 주제 추출
        from .tools import extract_common_theme_from_keywords

        callbacks = []
        if os.environ.get("ENABLE_COST_TRACKING") or os.environ.get(
            "LANGCHAIN_TRACING_V2"
        ):
            try:
                from .cost_tracking import get_tracking_callbacks

                callbacks = get_tracking_callbacks()
                register_recent_callbacks(callbacks)
            except Exception as e:
                logger.warning(
                    f"[yellow]Cost tracking setup error: {e}. Continuing without tracking.[/yellow]"
                )

        newsletter_topic = extract_common_theme_from_keywords(
            keywords, callbacks=callbacks
        )
    theme_time = time.time() - theme_start

    # 초기 상태 생성
    initial_state: NewsletterState = {
        "keywords": keywords,
        "news_period_days": news_period_days,
        "domain": domain,
        "template_style": template_style,
        "email_compatible": email_compatible,
        "newsletter_topic": newsletter_topic,
        "collected_articles": None,
        "processed_articles": None,
        "ranked_articles": None,
        "article_summaries": None,
        "category_summaries": None,
        "newsletter_html": None,
        "error": None,
        "status": "collecting",
        "start_time": workflow_start,
        "step_times": {"extract_theme": theme_time},
        "total_time": None,
    }

    # 그래프 생성 및 실행
    graph = create_newsletter_graph()
    final_state = graph.invoke(initial_state)  # type: ignore
    final_state["total_time"] = time.time() - workflow_start

    global _last_generation_info
    _last_generation_info = {
        "step_times": final_state.get("step_times", {}),
        "total_time": final_state.get("total_time"),
        "cost_summary": get_cost_summary(),
    }

    # 결과 반환
    if (
        final_state.get("status") == "complete"
        and final_state.get("newsletter_html") is not None
    ):
        return final_state["newsletter_html"], "success"  # type: ignore
    else:
        error_message = final_state.get("error", "알 수 없는 오류 발생")
        return (
            error_message if error_message is not None else "알 수 없는 오류 발생"
        ), "error"
