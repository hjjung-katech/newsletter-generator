"""
Newsletter Generator - LangGraph Workflow
이 모듈은 LangGraph를 사용하여 뉴스레터 생성 워크플로우를 정의합니다.
"""

from typing import Dict, List, Any, Tuple, TypedDict, Annotated, Literal, Optional
from langgraph.graph import StateGraph, END
from pydantic.v1 import BaseModel, Field  # Updated import for Pydantic v1 compatibility
from langchain_core.messages import HumanMessage
import json
import os  # Added import
import re  # Added import for regex date parsing
from datetime import datetime, timedelta, timezone  # Added imports
from .date_utils import parse_date_string


# State 정의
class NewsletterState(TypedDict):
    """뉴스레터 생성 과정의 상태를 정의하는 클래스"""

    # 입력 값
    keywords: List[str]
    news_period_days: int  # Configurable days for news recency filter
    domain: str  # Added domain field
    template_style: str  # Template style: 'compact' or 'detailed'
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

    print("\n[cyan]Step: Collecting articles...[/cyan]")

    try:
        keyword_str = ", ".join(state["keywords"])
        articles = search_news_articles.invoke(
            {"keywords": keyword_str, "num_results": 10}
        )

        return {
            **state,
            "collected_articles": articles,
            "status": "processing",  # Next status is processing
        }
    except Exception as e:
        print(f"[red]Error during article collection: {e}[/red]")
        return {
            **state,
            "collected_articles": [],  # Ensure it's an empty list on error
            "error": f"기사 수집 중 오류 발생: {str(e)}",
            "status": "error",
        }


# New node for processing articles
def process_articles_node(state: NewsletterState) -> NewsletterState:
    print(
        "\n[cyan]Step: Processing collected articles (filtering, sorting, deduplicating)...[/cyan]"
    )
    collected_articles = state.get("collected_articles")

    if not collected_articles or not isinstance(collected_articles, list):
        print(
            "[yellow]Warning: No articles collected or 'collected_articles' is not a list. Skipping processing.[/yellow]"
        )
        return {
            **state,
            "processed_articles": [],
            "error": "수집된 기사가 없거나 형식이 잘못되어 처리할 수 없습니다.",
            "status": "error",
        }

    print(f"Total articles received for processing: {len(collected_articles)}")

    output_dir = os.path.join(os.getcwd(), "output", "intermediate_processing")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_output_filename = f"{timestamp}_collected_articles_raw.json"
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
        print(f"Saved raw collected articles to {raw_output_path}")
    except Exception as e:
        print(f"[red]Error saving raw articles: {e}[/red]")
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
            print(
                f"Warning: Skipping non-dictionary item in collected_articles: {article}"
            )
            continue

        article_title_for_log = article.get("title", "N/A")  # For cleaner logs
        article_date_str = article.get("date")

        if not article_date_str or str(article_date_str).strip() == "날짜 없음":
            articles_missing_date += 1
            print(
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
                print(
                    f"Debug: Article too old: '{article_title_for_log}', Date: {article_date_obj.isoformat()}. Discarding."
                )
        else:
            # article_date_str was present, but parse_article_date_for_graph returned None
            articles_unparseable_date += 1
            print(
                f"Debug: Article with unparseable date: '{article_title_for_log}', Date string: '{article_date_str}'. Including by default."
            )
            recent_articles.append(article)
            articles_kept_unparseable_date += 1

    print(f"\nArticle date processing summary:")
    print(f"  Total collected articles: {len(collected_articles)}")
    print(
        f"  Articles with a date string provided: {articles_with_date + articles_unparseable_date}"
    )
    print(f"    Successfully parsed dates: {articles_with_date}")
    print(f"    Unparseable date strings: {articles_unparseable_date}")
    print(f"  Articles with missing date string (initially): {articles_missing_date}")
    print(
        f"  Total articles included for further processing (recent_articles): {len(recent_articles)}"
    )
    print(f"    Kept (recent with valid date): {articles_kept_recent_date}")
    print(f"    Kept (due to missing date): {articles_kept_missing_date}")
    print(f"    Kept (due to unparseable date): {articles_kept_unparseable_date}")
    print(
        f"  Articles discarded (parseable but too old): {articles_discarded_old_date}\n"
    )

    if not recent_articles:
        print("[yellow]Warning: No articles retained after recency filter.[/yellow]")
        # Optionally, save an empty processed file or skip
        processed_output_filename = (
            f"{timestamp}_collected_articles_processed_EMPTY.json"
        )
        processed_output_path = os.path.join(output_dir, processed_output_filename)
        try:
            with open(processed_output_path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=4)
            print(f"Saved empty processed articles list to {processed_output_path}")
        except Exception as e:
            print(f"[red]Error saving empty processed articles list: {e}[/red]")

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
                print(
                    f"Debug: Deduplicated article (URL already seen): {article.get('title', 'N/A')}, URL: {url}"
                )
        else:
            print(
                f"Warning: Article missing URL or URL is not a string, cannot deduplicate: {article.get('title', 'N/A')}"
            )
            # Decide how to handle articles without URLs: include them, or skip them for deduplication.
            # For now, let's include them if they passed the date filter, but they won't be part of URL-based deduplication.
            # To ensure they are added if no URL, generate a unique key or handle separately.
            # A simple way: if no URL, use a unique ID if available, or just add it (might lead to duplicates if content is same but no URL)
            # For this implementation, if no valid URL, it won't be added to unique_articles_dict, effectively skipping it from deduplicated list.
            # If you want to keep them, you'd need a different strategy.

    deduplicated_articles = list(unique_articles_dict.values())
    print(f"Retained {len(deduplicated_articles)} articles after deduplication.")

    if not deduplicated_articles:
        print("[yellow]Warning: No articles retained after deduplication.[/yellow]")
        # Optionally, save an empty processed file or skip
        processed_output_filename = (
            f"{timestamp}_collected_articles_processed_EMPTY_DEDUP.json"
        )
        processed_output_path = os.path.join(output_dir, processed_output_filename)
        try:
            with open(processed_output_path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=4)
            print(
                f"Saved empty processed articles list (post-dedup) to {processed_output_path}"
            )
        except Exception as e:
            print(f"[red]Error saving empty processed articles list: {e}[/red]")

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
    print(f"Sorted {len(processed_articles_sorted)} articles by date.")

    processed_output_filename = f"{timestamp}_collected_articles_processed.json"
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
        print(f"Saved processed articles with metadata to {processed_output_path}")
    except Exception as e:
        print(f"[red]Error saving processed articles: {e}[/red]")

    return {
        **state,
        "processed_articles": processed_articles_sorted,
        "status": "scoring",  # Next step is scoring
    }


def score_articles_node(state: NewsletterState) -> NewsletterState:
    """Score articles using LLM to rank priority."""
    from .scoring import score_articles

    print("\n[cyan]Step: Scoring articles...[/cyan]")

    processed = state.get("processed_articles") or []
    if not processed:
        print("[yellow]No articles to score.[/yellow]")
        return {
            **state,
            "error": "기사 점수를 매길 데이터가 없습니다.",
            "status": "error",
        }

    domain = state.get("domain", "")
    keywords = state.get("keywords", [])
    news_period_days = state.get("news_period_days", 14)

    # Get full ranked list for saving; top 10 will be passed forward
    ranked = score_articles(processed, domain, top_n=None)

    output_dir = os.path.join(os.getcwd(), "output", "intermediate_processing")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scored_path = os.path.join(output_dir, f"{timestamp}_scored_articles.json")
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
        print(f"Saved scored articles to {scored_path}")
    except Exception as e:
        print(f"[red]Error saving scored articles: {e}[/red]")

    return {
        **state,
        "ranked_articles": ranked[:10],
        "status": "summarizing",
    }


def summarize_articles_node(
    state: NewsletterState,
) -> NewsletterState:  # Renamed for clarity
    """
    수집된 기사를 요약하는 노드
    """
    from .chains import get_newsletter_chain
    import os

    print("\n[cyan]Step: Summarizing articles...[/cyan]")

    articles_for_summary = state.get("ranked_articles") or state.get(
        "processed_articles"
    )
    if not articles_for_summary:
        print("[yellow]No articles to summarize.[/yellow]")
        return {
            **state,
            "error": "요약할 기사가 없습니다.",
            "status": "error",
        }

    template_style = state.get("template_style", "compact")

    try:
        # 비용 추적 설정 (ENABLE_COST_TRACKING 환경 변수 설정된 경우에만)
        callbacks = []

        if os.environ.get("ENABLE_COST_TRACKING") or os.environ.get(
            "LANGCHAIN_TRACING_V2"
        ):
            try:
                from .cost_tracking import get_tracking_callbacks

                callbacks = get_tracking_callbacks()
            except Exception as e:
                print(
                    f"[yellow]Cost tracking setup error: {e}. Continuing without tracking.[/yellow]"
                )

        # template_style에 따라 compact 또는 detailed 체인 사용
        is_compact = template_style == "compact"

        if is_compact:
            print(
                "[cyan]Using compact processing - running compact newsletter chain...[/cyan]"
            )
        else:
            print(
                "[cyan]Using detailed processing - running full summarization chain...[/cyan]"
            )

        # 통합된 체인 가져오기 및 실행
        newsletter_chain = get_newsletter_chain(is_compact=is_compact)

        # 데이터 형식 맞추기: processed_articles를 'articles' 키를 가진 딕셔너리로 감싸기
        input_data = {
            "articles": articles_for_summary,
            "keywords": state.get("keywords", ""),
        }

        category_summaries = newsletter_chain.invoke(input_data)

        if not category_summaries:
            return {
                **state,
                "error": "카테고리 요약 생성에 실패했습니다.",
                "status": "error",
            }

        # 결과 상태 업데이트 및 반환
        return {
            **state,
            "category_summaries": category_summaries,
            "status": "composing",  # Changed to composing to indicate next step
        }
    except Exception as e:
        import traceback

        error_msg = f"기사 요약 중 오류가 발생했습니다: {str(e)}"
        print(f"[bold red]Error in summarization: {str(e)}[/bold red]")
        traceback.print_exc()
        return {
            **state,
            "error": error_msg,
            "status": "error",
        }


def compose_newsletter_node(
    state: NewsletterState,
) -> NewsletterState:
    """
    카테고리 요약에서 최종 뉴스레터 HTML을 생성하는 노드
    """
    from .compose import compose_newsletter
    import os
    from datetime import datetime  # Import datetime for timestamp

    print("\n[cyan]Step: Composing final newsletter...[/cyan]")

    category_summaries = state.get("category_summaries")
    if not category_summaries:
        print("[yellow]No category summaries to compose newsletter.[/yellow]")
        return {
            **state,
            "error": "카테고리 요약이 없어 뉴스레터를 생성할 수 없습니다.",
            "status": "error",
        }

    try:
        template_style = state.get("template_style", "compact")

        # category_summaries is the full newsletter data structure created by the rendering chain
        if isinstance(category_summaries, str):
            # If it's already HTML, just use it
            newsletter_html = category_summaries
        else:
            # If it's structured data, render with appropriate template using unified function
            template_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "templates"
            )

            print(f"[cyan]Using {template_style} newsletter template...[/cyan]")
            newsletter_html = compose_newsletter(
                category_summaries, template_dir, template_style
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
            # 주제에서 파일명 생성
            from .tools import sanitize_filename

            filename_base = sanitize_filename(topic)

            # 폴더가 없으면 생성
            output_dir = os.path.join(os.getcwd(), "output")
            os.makedirs(output_dir, exist_ok=True)

            # 날짜와 시간을 파일명에 추가
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename_base}_{style}_{timestamp}.html"
            file_path = os.path.join(output_dir, filename)

            # 파일 저장
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            print(f"[green]Newsletter saved to {file_path}[/green]")
            return file_path

        # 뉴스레터 저장
        newsletter_topic = state.get("newsletter_topic", "뉴스레터")
        save_path = save_newsletter_html(
            newsletter_html, newsletter_topic, template_style
        )

        # 결과 상태 업데이트 및 반환
        return {
            **state,
            "newsletter_html": newsletter_html,
            "status": "complete",  # Final status
        }
    except Exception as e:
        import traceback

        error_msg = f"뉴스레터 생성 중 오류가 발생했습니다: {str(e)}"
        print(f"[bold red]Error in newsletter composition: {str(e)}[/bold red]")
        traceback.print_exc()
        return {
            **state,
            "error": error_msg,
            "status": "error",
        }


def handle_error(state: NewsletterState) -> NewsletterState:
    """
    에러 처리 노드
    """
    print(f"[오류] {state['error']}")
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
) -> Tuple[str, str]:
    """
    키워드를 기반으로 뉴스레터를 생성하는 메인 함수

    Args:
        keywords: 키워드 리스트
        news_period_days: 최신 뉴스 수집 기간(일 단위), 기본값 14일(2주)
        domain: 키워드를 생성한 도메인 (있는 경우)
        template_style: 뉴스레터 템플릿 스타일 ('compact' 또는 'detailed')

    Returns:
        (뉴스레터 HTML, 상태)
    """
    # 뉴스레터 주제 결정 (도메인, 단일 키워드, 또는 공통 주제)
    newsletter_topic = ""
    if domain:
        newsletter_topic = domain  # 도메인이 있으면 도메인 사용
    elif len(keywords) == 1:
        newsletter_topic = keywords[0]  # 단일 키워드면 해당 키워드 사용
    else:
        # 여러 키워드의 공통 주제 추출
        from .tools import extract_common_theme_from_keywords

        newsletter_topic = extract_common_theme_from_keywords(keywords)

    # 초기 상태 생성
    initial_state: NewsletterState = {  # Added type hint for clarity
        "keywords": keywords,
        "news_period_days": news_period_days,  # Propagate configurable period to state
        "domain": domain,  # 도메인 정보 추가
        "template_style": template_style,  # Add template_style to state
        "newsletter_topic": newsletter_topic,  # 뉴스레터 주제 추가
        "collected_articles": None,  # Initialize as None
        "processed_articles": None,  # Initialize as None
        "ranked_articles": None,  # Initialize as None
        "article_summaries": None,  # Initialize as None
        "category_summaries": None,  # Initialize as None
        "newsletter_html": None,  # Initialize as None
        "error": None,  # Initialize as None
        "status": "collecting",
    }

    # 그래프 생성 및 실행
    graph = create_newsletter_graph()
    final_state = graph.invoke(initial_state)  # type: ignore

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
