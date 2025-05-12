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


# State 정의
class NewsletterState(TypedDict):
    """뉴스레터 생성 과정의 상태를 정의하는 클래스"""

    # 입력 값
    keywords: List[str]
    news_period_days: int  # Configurable days for news recency filter
    # 중간 결과물
    collected_articles: Optional[List[Dict]]  # Made Optional
    processed_articles: Optional[List[Dict]]  # New field
    article_summaries: Optional[Dict]  # Made Optional
    # 최종 결과물
    newsletter_html: Optional[str]  # Made Optional
    # 제어 및 메타데이터
    error: Optional[str]  # Made Optional
    status: str  # 'collecting', 'processing', 'summarizing', 'composing', 'complete', 'error'


# Helper function to parse article dates
def parse_article_date_for_graph(
    date_str: Any,
) -> Optional[datetime]:  # Changed type hint for initial check
    if not isinstance(date_str, str) or not date_str.strip() or date_str == "날짜 없음":
        return None

    date_str = date_str.strip()
    now = datetime.now(timezone.utc)  # Use timezone-aware now for relative dates

    # 1. Handle relative Korean dates
    if isinstance(
        date_str, str
    ):  # Check if date_str is a string before calling .endswith()
        if date_str.endswith("일 전"):  # "X일 전"
            try:
                days_ago = int(date_str.split("일")[0].strip())
                return now - timedelta(days=days_ago)
            except ValueError:
                pass  # Fall through to other formats
        elif date_str.endswith("시간 전"):  # "X시간 전"
            try:
                hours_ago = int(date_str.split("시간")[0].strip())
                return now - timedelta(hours=hours_ago)
            except ValueError:
                pass
        elif date_str.endswith("분 전"):  # "X분 전"
            try:
                minutes_ago = int(date_str.split("분")[0].strip())
                return now - timedelta(minutes=minutes_ago)
            except ValueError:
                pass
        elif date_str == "어제":
            return now - timedelta(days=1)
        elif date_str == "오늘":  # Less common for articles, but good to have
            return now  # 2. Handle relative English dates (e.g., "X minutes ago", "X hours ago", "X days ago")
    if isinstance(
        date_str, str
    ):  # Ensure it's a string for regex        # Handle both "X minute ago" (단수형) 및 "X minutes ago" (복수형)
        match_minutes = re.match(r"(\d+)\s+minutes?\s+ago", date_str, re.IGNORECASE)
        if match_minutes:
            try:
                minutes_ago = int(match_minutes.group(1))
                return now - timedelta(minutes=minutes_ago)
            except ValueError:
                pass

        # 영어 단수형 처리 - "X minute ago"
        match_minute = re.match(r"(\d+)\s+minute\s+ago", date_str, re.IGNORECASE)
        if match_minute:
            try:
                minutes_ago = int(match_minute.group(1))
                return now - timedelta(minutes=minutes_ago)
            except ValueError:
                pass

        match_hours = re.match(r"(\d+)\s+hours?\s+ago", date_str, re.IGNORECASE)
        if match_hours:
            try:
                hours_ago = int(match_hours.group(1))
                return now - timedelta(hours=hours_ago)
            except ValueError:
                pass

        match_days = re.match(r"(\d+)\s+days?\s+ago", date_str, re.IGNORECASE)
        if match_days:
            try:
                days_ago = int(match_days.group(1))
                return now - timedelta(days=days_ago)
            except ValueError:
                pass

        match_weeks = re.match(r"(\d+)\s+weeks?\s+ago", date_str, re.IGNORECASE)
        if match_weeks:
            try:
                weeks_ago = int(match_weeks.group(1))
                return now - timedelta(weeks=weeks_ago)
            except ValueError:
                pass

        match_months = re.match(r"(\d+)\s+months?\s+ago", date_str, re.IGNORECASE)
        if match_months:
            try:
                months_ago = int(match_months.group(1))
                # timedelta doesn't directly support months, approximate as 30 days
                return now - timedelta(days=months_ago * 30)
            except ValueError:
                pass

    # 3. ISO 8601 format (with or without 'Z')
    try:
        if date_str.endswith("Z") and len(date_str) > 1:
            dt = datetime.fromisoformat(date_str[:-1] + "+00:00")
        else:
            dt = datetime.fromisoformat(date_str)
        # If parsed successfully but naive, make it timezone-aware (assume UTC)
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        # 3. Try other common formats
        common_formats = [
            "%Y-%m-%dT%H:%M:%S.%f%z",  # ISO with microseconds and timezone
            "%Y-%m-%dT%H:%M:%S%z",  # ISO with timezone
            "%Y-%m-%dT%H:%M:%S",  # ISO without timezone
            "%Y-%m-%d %H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y.%m.%d. %H:%M:%S",  # Added dot after day, space before H:M:S
            "%Y.%m.%d %H:%M:%S",  # Original
            "%Y.%m.%d.",  # Format like "2024. 7. 3." (with trailing dot)
            "%Y. %m. %d.",  # Format like "2024. 7. 3." (with spaces and trailing dot) - Primary target for Serper
            "%Y.%m.%d",  # Original
            "%Y-%m-%d",
            "%Y년 %m월 %d일",  # Korean format "YYYY년 MM월 DD일"
            # English formats
            "%b %d, %Y",  # e.g., Apr 16, 2025
            "%B %d, %Y",  # e.g., April 16, 2025
            "%m/%d/%Y",  # e.g., 04/16/2025
            "%d %b %Y",  # e.g., 16 Apr 2025
            "%d %B %Y",  # e.g., 16 April 2025
        ]
        for fmt in common_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # If parsed successfully but naive, make it timezone-aware (assume UTC)
                if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue

        # 4. Try to parse YYYY.MM.DD or YYYY.M.D without strict padding (more robust)
        # This is a bit more complex, might need regex if strptime fails for unpadded single digits with spaces
        # For now, relying on '%Y. %m. %d.' which should handle spaces if month/day are single/double digits.
        # Let's test if '%Y. %m. %d.' correctly handles '2024. 7. 3.' and '2024. 12. 10.'

        print(f"Warning: Could not parse date: '{date_str}' with any known format.")
        return None


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
        with open(raw_output_path, "w", encoding="utf-8") as f:
            json.dump(collected_articles, f, ensure_ascii=False, indent=4)
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
        with open(processed_output_path, "w", encoding="utf-8") as f:
            json.dump(processed_articles_sorted, f, ensure_ascii=False, indent=4)
        print(f"Saved processed articles to {processed_output_path}")
    except Exception as e:
        print(f"[red]Error saving processed articles: {e}[/red]")

    return {
        **state,
        "processed_articles": processed_articles_sorted,
        "status": "summarizing",  # Next status is summarizing
    }


def summarize_articles_node(
    state: NewsletterState,
) -> NewsletterState:  # Renamed for clarity
    """
    수집된 기사를 요약하는 노드
    """
    from .chains import get_summarization_chain

    print("\n[cyan]Step: Summarizing articles...[/cyan]")

    processed_articles = state.get("processed_articles")
    if not processed_articles:  # Check processed_articles
        print("[yellow]No processed articles to summarize.[/yellow]")
        return {
            **state,
            "error": "처리된 기사가 없어 요약을 진행할 수 없습니다.",  # More specific error
            "status": "error",
        }

    try:
        summarization_chain = get_summarization_chain()
        keyword_str = ", ".join(state["keywords"])
        chain_input = {
            "keywords": keyword_str,
            "articles": processed_articles,  # Use processed_articles
        }

        result = summarization_chain.invoke(chain_input)

        return {**state, "newsletter_html": result, "status": "complete"}
    except Exception as e:
        print(f"[red]Error during article summarization: {e}[/red]")
        return {
            **state,
            "error": f"기사 요약 중 오류 발생: {str(e)}",
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
    workflow.add_node("summarize_articles", summarize_articles_node)  # Use new name
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
                "summarize_articles"
                if state.get("processed_articles")
                else "handle_error"
            )
        ),
    )
    workflow.add_conditional_edges(
        "summarize_articles",
        lambda state: "handle_error" if state.get("status") == "error" else END,
    )
    workflow.add_edge("handle_error", END)

    # 시작 노드 설정
    workflow.set_entry_point("collect_articles")

    return workflow.compile()


# 뉴스레터 생성 함수
def generate_newsletter(
    keywords: List[str], news_period_days: int = 14
) -> Tuple[str, str]:
    """
    키워드를 기반으로 뉴스레터를 생성하는 메인 함수

    Args:
        keywords: 키워드 리스트
        news_period_days: 최신 뉴스 수집 기간(일 단위), 기본값 14일(2주)

    Returns:
        (뉴스레터 HTML, 상태)
    """
    # 초기 상태 생성
    initial_state: NewsletterState = {  # Added type hint for clarity
        "keywords": keywords,
        "news_period_days": news_period_days,  # Propagate configurable period to state
        "collected_articles": None,  # Initialize as None
        "processed_articles": None,  # Initialize as None
        "article_summaries": None,  # Initialize as None
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
