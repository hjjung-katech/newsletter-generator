"""Node-level transformation helpers for the legacy newsletter graph."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, cast

from newsletter_core.application.graph_workflow import (
    NewsletterState,
    parse_graph_article_date,
)

ArticleRecord = Dict[str, Any]

_COMPOSE_FALLBACK_HTML = "<html><body>Newsletter generation failed</body></html>"


def _with_step_time(
    state: NewsletterState,
    *,
    step_name: str,
    elapsed: float,
    updates: Dict[str, Any],
) -> NewsletterState:
    step_times = dict(state.get("step_times", {}))
    step_times[step_name] = elapsed

    updated_state = dict(state)
    updated_state.update(updates)
    updated_state["step_times"] = step_times
    return cast(NewsletterState, updated_state)


def build_collect_keyword_query(keywords: List[str]) -> str:
    """Build the legacy Serper query string from graph keywords."""
    return ", ".join(keywords)


def resolve_graph_domain_slug(state: NewsletterState) -> str:
    """Resolve a stable domain slug for legacy intermediate output names."""
    domain_value = state.get("domain")
    if isinstance(domain_value, str) and domain_value:
        return domain_value.replace(" ", "_")
    return "general"


def resolve_graph_keywords_slug(state: NewsletterState) -> str:
    """Resolve a stable keyword slug for legacy output names."""
    keywords = state.get("keywords", [])
    return "_".join(keywords) if keywords else "unknown"


def build_collect_success_state(
    state: NewsletterState,
    *,
    articles: List[ArticleRecord],
    elapsed: float,
) -> NewsletterState:
    """Update graph state after successful article collection."""
    return _with_step_time(
        state,
        step_name="collect_articles",
        elapsed=elapsed,
        updates={
            "collected_articles": articles,
            "status": "processing",
        },
    )


def build_collect_error_state(
    state: NewsletterState,
    *,
    error_message: str,
    elapsed: float,
) -> NewsletterState:
    """Update graph state after collection failure."""
    return _with_step_time(
        state,
        step_name="collect_articles",
        elapsed=elapsed,
        updates={
            "collected_articles": [],
            "error": error_message,
            "status": "error",
        },
    )


def filter_articles_for_processing(
    collected_articles: List[ArticleRecord],
    *,
    news_period_days: int,
    current_time: datetime,
) -> List[ArticleRecord]:
    """Keep recent articles while preserving legacy missing-date fallbacks."""
    articles_within_date_range: List[ArticleRecord] = []
    articles_with_missing_date: List[ArticleRecord] = []
    articles_with_unparseable_date: List[ArticleRecord] = []
    cutoff_date = current_time - timedelta(days=news_period_days)

    for article in collected_articles:
        date_str = article.get("date")
        if not date_str or date_str == "날짜 없음":
            articles_with_missing_date.append(article)
            continue

        parsed_date = parse_graph_article_date(date_str)
        if parsed_date is None:
            articles_with_unparseable_date.append(article)
            continue

        if parsed_date >= cutoff_date:
            articles_within_date_range.append(article)

    return (
        articles_within_date_range
        + articles_with_missing_date
        + articles_with_unparseable_date
    )


def sort_articles_by_graph_date_desc(
    articles: List[ArticleRecord],
) -> List[ArticleRecord]:
    """Sort articles by parsed graph date, newest first."""
    return sorted(
        articles,
        key=lambda article: parse_graph_article_date(article.get("date", ""))
        or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )


def build_process_missing_articles_state(state: NewsletterState) -> NewsletterState:
    """Preserve the legacy early error state when no articles were collected."""
    return cast(
        NewsletterState,
        {
            **state,
            "processed_articles": [],
            "status": "error",
            "error": "수집된 기사가 없습니다.",
        },
    )


def build_process_success_state(
    state: NewsletterState,
    *,
    processed_articles: List[ArticleRecord],
    elapsed: float,
) -> NewsletterState:
    """Update graph state after processing completes."""
    return _with_step_time(
        state,
        step_name="process_articles",
        elapsed=elapsed,
        updates={
            "processed_articles": processed_articles,
            "status": "scoring",
        },
    )


def build_score_missing_articles_state(
    state: NewsletterState,
    *,
    elapsed: float,
) -> NewsletterState:
    """Update graph state when scoring has no input articles."""
    return _with_step_time(
        state,
        step_name="score_articles",
        elapsed=elapsed,
        updates={
            "ranked_articles": [],
            "status": "error",
            "error": "스코어링할 기사가 없습니다.",
        },
    )


def resolve_scoring_domain(state: NewsletterState) -> str:
    """Resolve the effective scoring domain without touching runtime wiring."""
    return state.get("domain", "") or ", ".join(state.get("keywords", []))


def build_score_success_state(
    state: NewsletterState,
    *,
    ranked_articles: List[ArticleRecord],
    elapsed: float,
) -> NewsletterState:
    """Update graph state after scoring completes."""
    return _with_step_time(
        state,
        step_name="score_articles",
        elapsed=elapsed,
        updates={
            "ranked_articles": ranked_articles,
            "status": "scoring_complete",
        },
    )


def build_score_error_state(
    state: NewsletterState,
    *,
    error_message: str,
    elapsed: float,
) -> NewsletterState:
    """Update graph state after scoring failure."""
    return _with_step_time(
        state,
        step_name="score_articles",
        elapsed=elapsed,
        updates={
            "ranked_articles": [],
            "status": "error",
            "error": error_message,
        },
    )


def resolve_summary_chain_style(state: NewsletterState) -> tuple[str, bool]:
    """Resolve the template style and compact-mode flag for the summary node."""
    template_style = state.get("template_style", "detailed")
    return template_style, template_style == "compact"


def build_summarize_missing_articles_state(
    state: NewsletterState,
    *,
    elapsed: float,
) -> NewsletterState:
    """Update graph state when summarize has no ranked articles."""
    return _with_step_time(
        state,
        step_name="summarize",
        elapsed=elapsed,
        updates={
            "newsletter_html": None,
            "status": "error",
            "error": "요약할 기사가 없습니다.",
        },
    )


def build_summarize_success_state(
    state: NewsletterState,
    *,
    newsletter_html: str,
    category_summaries: Dict[str, Any],
    newsletter_topic: str,
    elapsed: float,
) -> NewsletterState:
    """Update graph state after summary generation succeeds."""
    return _with_step_time(
        state,
        step_name="summarize",
        elapsed=elapsed,
        updates={
            "newsletter_html": newsletter_html,
            "category_summaries": category_summaries,
            "newsletter_topic": newsletter_topic,
            "status": "summarizing_complete",
        },
    )


def build_summarize_error_state(
    state: NewsletterState,
    *,
    error_message: str,
    elapsed: float,
) -> NewsletterState:
    """Update graph state after summary generation fails."""
    return _with_step_time(
        state,
        step_name="summarize",
        elapsed=elapsed,
        updates={
            "newsletter_html": None,
            "status": "error",
            "error": error_message,
        },
    )


def resolve_compose_html(newsletter_html: Optional[str]) -> str:
    """Resolve the final compose HTML while preserving the legacy fallback."""
    return newsletter_html or _COMPOSE_FALLBACK_HTML


def build_compose_missing_data_state(
    state: NewsletterState,
    *,
    elapsed: float,
) -> NewsletterState:
    """Update graph state when compose has no HTML or summaries to use."""
    return _with_step_time(
        state,
        step_name="compose",
        elapsed=elapsed,
        updates={
            "status": "error",
            "error": "구성할 뉴스레터 데이터가 없습니다.",
        },
    )


def build_compose_success_state(
    state: NewsletterState,
    *,
    newsletter_html: str,
    elapsed: float,
) -> NewsletterState:
    """Update graph state after compose succeeds."""
    return _with_step_time(
        state,
        step_name="compose",
        elapsed=elapsed,
        updates={
            "newsletter_html": newsletter_html,
            "status": "complete",
        },
    )


def build_compose_error_state(
    state: NewsletterState,
    *,
    error_message: str,
    elapsed: float,
) -> NewsletterState:
    """Update graph state after compose fails."""
    return _with_step_time(
        state,
        step_name="compose",
        elapsed=elapsed,
        updates={
            "status": "error",
            "error": error_message,
        },
    )
