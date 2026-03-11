"""
Newsletter Generator - LangGraph Workflow
이 모듈은 LangGraph를 사용하여 뉴스레터 생성 워크플로우를 정의합니다.
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, cast

from langgraph.graph import END, StateGraph

from newsletter_core.application.graph_workflow import (
    NewsletterState,
    build_generation_info,
    build_initial_graph_state,
    build_newsletter_chain_payload,
    normalize_summary_chain_result,
    parse_graph_article_date,
    resolve_generation_result,
    route_after_collect,
    route_after_compose,
    route_after_process,
    route_after_score,
    route_after_summarize,
)

from .chains import get_newsletter_chain
from .utils.file_naming import generate_unified_newsletter_filename
from .utils.logger import get_logger, step_brief

# 로거 초기화
logger = get_logger()


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
    return cast(Optional[datetime], parse_graph_article_date(date_str))


# 노드 함수 정의
def collect_articles_node(
    state: NewsletterState,
) -> NewsletterState:  # Renamed for clarity
    """
    키워드를 기반으로 기사를 수집하는 노드
    기존 Serper API를 사용하여 뉴스 수집
    """
    from .tools import search_news_articles

    step_brief("뉴스 기사 수집 중")
    start_time = time.time()

    try:
        # 기존 Serper API 방식 사용
        keyword_str = ", ".join(state["keywords"])
        articles = search_news_articles.invoke(
            {"keywords": keyword_str, "num_results": 10}
        )

        logger.info(f"Serper API에서 {len(articles)}개 기사 수집 완료")

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
    """
    수집된 기사들을 처리하는 노드 (날짜 필터링, 중복 제거, 정렬)
    """
    from .utils.logger import show_filter_brief, step_brief, step_result

    step_brief("기사 처리 중")
    start_time = time.time()

    collected_articles = state.get("collected_articles", [])
    if not collected_articles:
        logger.warning(
            "[yellow]Warning: No articles found to process. Check if collection was successful.[/yellow]"
        )
        return {
            **state,
            "processed_articles": [],
            "status": "error",
            "error": "수집된 기사가 없습니다.",
        }

    logger.info(
        f"Processing {len(collected_articles)} articles with {state.get('news_period_days', 7)} day filter..."
    )

    # Save raw articles with unified naming
    try:
        domain_str = (
            state["domain"].replace(" ", "_") if state.get("domain") else "general"
        )

        # 중간 파일용 파일명 생성 (단순히 타임스탬프 + 설명적 이름 사용)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{domain_str}_raw_articles.json"
        raw_output_path = os.path.join("output", "intermediate_processing", filename)
        os.makedirs(os.path.dirname(raw_output_path), exist_ok=True)

        with open(raw_output_path, "w", encoding="utf-8") as f:
            json.dump(collected_articles, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved raw collected articles to {raw_output_path}")
    except Exception as e:
        logger.warning(f"Warning: Failed to save raw articles: {e}")

    # 1. 날짜 기반 필터링
    articles_within_date_range = []
    articles_with_missing_date = []
    articles_with_unparseable_date = []
    articles_with_date = 0
    articles_unparseable_date = 0
    cutoff_date = datetime.now(timezone.utc) - timedelta(
        days=state.get("news_period_days", 7)
    )

    initial_count = len(collected_articles)

    for article in collected_articles:
        date_str = article.get("date")
        if not date_str or date_str == "날짜 없음":
            articles_with_missing_date.append(article)
            continue

        parsed_date = parse_article_date_for_graph(date_str)
        if parsed_date is None:
            articles_unparseable_date += 1
            articles_with_unparseable_date.append(article)
            continue

        articles_with_date += 1
        if parsed_date >= cutoff_date:
            articles_within_date_range.append(article)

    # Combine kept articles (recent + missing + unparseable dates)
    filtered_articles = (
        articles_within_date_range
        + articles_with_missing_date
        + articles_with_unparseable_date
    )

    show_filter_brief(initial_count, len(filtered_articles), "날짜 필터링")

    # 2. 중복 제거
    if not filtered_articles:
        logger.warning(
            "[yellow]No articles remaining after date filtering. Proceeding with empty list.[/yellow]"
        )
        deduplicated_articles = []
    else:
        from . import article_filter

        deduplicated_articles = article_filter.remove_duplicate_articles(
            filtered_articles
        )

    show_filter_brief(len(filtered_articles), len(deduplicated_articles), "중복 제거")

    # 3. 날짜순 정렬
    if not deduplicated_articles:
        logger.warning(
            "[yellow]No articles remaining after deduplication. Proceeding with empty list.[/yellow]"
        )
        processed_articles_sorted = []
    else:
        # Article sorting
        processed_articles_sorted = sorted(
            deduplicated_articles,
            key=lambda x: parse_article_date_for_graph(x.get("date", ""))
            or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

    step_result("기사 처리 완료", len(processed_articles_sorted))

    step_times = state.get("step_times", {})
    step_times["process_articles"] = time.time() - start_time
    return {
        **state,
        "processed_articles": processed_articles_sorted,
        "status": "scoring",  # Next step is scoring
        "step_times": step_times,
    }


def score_articles_node(state: NewsletterState) -> NewsletterState:
    """
    기사들에 점수를 매기고 순위를 매기는 노드
    """
    from .utils.logger import step_brief, step_result

    step_brief("기사 스코어링 중")
    start_time = time.time()

    processed_articles = state.get("processed_articles", [])
    if not processed_articles:
        logger.warning("[yellow]No articles to score.[/yellow]")
        step_times = state.get("step_times", {})
        step_times["score_articles"] = time.time() - start_time
        return {
            **state,
            "ranked_articles": [],
            "status": "error",
            "error": "스코어링할 기사가 없습니다.",
            "step_times": step_times,
        }

    try:
        from . import scoring

        # 스코어링 가중치 로드
        scoring_weights = scoring.load_scoring_weights_from_config()
        logger.info(f"[cyan]Using scoring weights: {scoring_weights}[/cyan]")

        # 도메인/주제 결정
        domain = state.get("domain", "") or ", ".join(state.get("keywords", []))

        # 기사 스코어링
        ranked_articles = scoring.score_articles(
            processed_articles, domain, top_n=None, weights=scoring_weights
        )

        step_result("기사 스코어링 완료", len(ranked_articles))

        # 파일 저장
        try:
            domain_str = (
                state["domain"].replace(" ", "_") if state.get("domain") else "general"
            )

            # 중간 파일용 파일명 생성 (단순히 타임스탬프 + 설명적 이름 사용)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{domain_str}_scored_articles.json"
            scored_path = os.path.join("output", "intermediate_processing", filename)
            os.makedirs(os.path.dirname(scored_path), exist_ok=True)

            with open(scored_path, "w", encoding="utf-8") as f:
                json.dump(ranked_articles, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved scored articles to {scored_path}")
        except Exception as e:
            logger.warning(f"Warning: Failed to save scored articles: {e}")

        step_times = state.get("step_times", {})
        step_times["score_articles"] = time.time() - start_time

        return {
            **state,
            "ranked_articles": ranked_articles,
            "status": "scoring_complete",
            "step_times": step_times,
        }

    except Exception as e:
        logger.error(f"Error during article scoring: {e}")
        step_times = state.get("step_times", {})
        step_times["score_articles"] = time.time() - start_time
        return {
            **state,
            "ranked_articles": [],
            "status": "error",
            "error": f"기사 스코어링 중 오류: {str(e)}",
            "step_times": step_times,
        }


def summarize_articles_node(state: NewsletterState) -> NewsletterState:
    """
    기사들을 요약하여 뉴스레터를 생성하는 노드
    """
    from .utils.logger import show_final_brief, step_brief

    step_brief("뉴스레터 생성 중")
    start_time = time.time()

    ranked_articles = state.get("ranked_articles", [])
    if not ranked_articles:
        logger.warning("[yellow]No articles to summarize.[/yellow]")
        step_times = state.get("step_times", {})
        step_times["summarize"] = time.time() - start_time
        return {
            **state,
            "newsletter_html": None,
            "status": "error",
            "error": "요약할 기사가 없습니다.",
            "step_times": step_times,
        }

    try:
        # 사용할 체인 결정
        template_style = state.get("template_style", "detailed")
        is_compact = template_style == "compact"
        newsletter_chain = get_newsletter_chain(is_compact=is_compact)

        # 체인 실행을 위한 데이터 준비
        chain_data = build_newsletter_chain_payload(
            state, ranked_articles, template_style
        )

        logger.info(
            f"Generating newsletter using {template_style} style for {len(ranked_articles)} articles"
        )

        # 최종 활용 기사 수 표시
        show_final_brief(len(ranked_articles))

        # 체인 실행
        result = newsletter_chain.invoke(chain_data)

        if isinstance(result, str):
            logger.info("[yellow]Received HTML string (legacy format)[/yellow]")

        (
            newsletter_html,
            category_summaries,
            newsletter_topic,
        ) = normalize_summary_chain_result(
            result,
            state=state,
            template_style=template_style,
            article_count=len(ranked_articles),
            generated_at=datetime.now(),
        )

        step_times = state.get("step_times", {})
        step_times["summarize"] = time.time() - start_time

        return {
            **state,
            "newsletter_html": newsletter_html,
            "category_summaries": category_summaries,
            "newsletter_topic": newsletter_topic,
            "status": "summarizing_complete",
            "step_times": step_times,
        }

    except Exception as e:
        logger.error(f"Error during article summarization: {e}")
        import traceback

        logger.debug(f"Traceback: {traceback.format_exc()}")

        step_times = state.get("step_times", {})
        step_times["summarize"] = time.time() - start_time
        return {
            **state,
            "newsletter_html": None,
            "status": "error",
            "error": f"기사 요약 중 오류: {str(e)}",
            "step_times": step_times,
        }


def compose_newsletter_node(state: NewsletterState) -> NewsletterState:
    """
    최종 뉴스레터를 구성하고 파일로 저장하는 노드
    """
    from .utils.logger import step_brief, step_result

    step_brief("뉴스레터 구성 중")
    start_time = time.time()

    category_summaries = state.get("category_summaries")
    newsletter_html = state.get("newsletter_html")

    if not category_summaries and not newsletter_html:
        logger.warning("[yellow]No category summaries to compose newsletter.[/yellow]")
        step_times = state.get("step_times", {})
        step_times["compose"] = time.time() - start_time
        return {
            **state,
            "status": "error",
            "error": "구성할 뉴스레터 데이터가 없습니다.",
            "step_times": step_times,
        }

    try:
        # 이미 체인에서 HTML이 생성된 경우 그대로 사용
        if newsletter_html:
            logger.info("[cyan]Using pre-generated HTML from chains[/cyan]")
            final_html = newsletter_html
        else:
            # Fallback: 기존 로직으로 HTML 생성 (현재는 체인이 담당)
            final_html = "<html><body>Newsletter generation failed</body></html>"

        # 파일 저장
        try:
            keywords_str = (
                "_".join(state["keywords"]) if state["keywords"] else "unknown"
            )
            domain_str = (
                state["domain"].replace(" ", "_") if state.get("domain") else "general"
            )
            template_style = state.get("template_style", "detailed")

            # generate_unified_newsletter_filename이 이미 전체 경로를 반환함
            file_path = generate_unified_newsletter_filename(
                domain_str, f"newsletter_{template_style}", keywords_str, "html"
            )

            # 디렉토리 존재 확인 (파일 경로에서 디렉토리 부분 추출)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(final_html)

            step_result("뉴스레터 저장 완료")
            logger.info(f"[green]Newsletter saved to {file_path}[/green]")

        except Exception as e:
            logger.error(f"Error saving newsletter: {e}")

        step_times = state.get("step_times", {})
        step_times["compose"] = time.time() - start_time

        return {
            **state,
            "newsletter_html": final_html,
            "status": "complete",
            "step_times": step_times,
        }

    except Exception as e:
        logger.error(f"Error composing newsletter: {e}")
        step_times = state.get("step_times", {})
        step_times["compose"] = time.time() - start_time
        return {
            **state,
            "status": "error",
            "error": f"뉴스레터 구성 중 오류: {str(e)}",
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
    workflow.add_conditional_edges("collect_articles", route_after_collect)
    workflow.add_conditional_edges("process_articles", route_after_process)
    workflow.add_conditional_edges("score_articles", route_after_score)
    workflow.add_conditional_edges("summarize_articles", route_after_summarize)
    workflow.add_conditional_edges(
        "compose_newsletter",
        route_after_compose,
        {"handle_error": "handle_error", "complete": END},
    )
    workflow.add_edge("handle_error", END)

    # 시작 노드 설정
    workflow.set_entry_point("collect_articles")

    return workflow.compile()


# 뉴스레터 생성 함수
def generate_newsletter(
    keywords: List[str],
    news_period_days: int = 14,
    domain: Optional[str] = None,
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
    initial_state = build_initial_graph_state(
        keywords=keywords,
        news_period_days=news_period_days,
        domain=domain,
        template_style=template_style,
        email_compatible=email_compatible,
        newsletter_topic=newsletter_topic,
        workflow_start=workflow_start,
        theme_time=theme_time,
    )

    # 그래프 생성 및 실행
    graph = create_newsletter_graph()
    final_state = cast(NewsletterState, graph.invoke(initial_state))
    final_state["total_time"] = time.time() - workflow_start

    global _last_generation_info
    _last_generation_info = build_generation_info(final_state, get_cost_summary())

    return cast(Tuple[str, str], resolve_generation_result(final_state))
