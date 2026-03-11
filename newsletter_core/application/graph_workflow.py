"""Pure and semi-pure helpers for the legacy newsletter graph workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, TypedDict

from newsletter.date_utils import parse_date_string


class NewsletterState(TypedDict):
    """Shared workflow state for newsletter generation."""

    keywords: List[str]
    news_period_days: int
    domain: Optional[str]
    template_style: str
    email_compatible: bool
    collected_articles: Optional[List[Dict[str, Any]]]
    processed_articles: Optional[List[Dict[str, Any]]]
    ranked_articles: Optional[List[Dict[str, Any]]]
    article_summaries: Optional[Dict[str, Any]]
    category_summaries: Optional[Dict[str, Any]]
    newsletter_topic: Optional[str]
    newsletter_html: Optional[str]
    error: Optional[str]
    status: str
    start_time: float
    step_times: Dict[str, float]
    total_time: Optional[float]


def parse_graph_article_date(date_str: Any) -> Optional[datetime]:
    """Parse graph article dates through the shared date parser."""
    parsed_date = parse_date_string(date_str)
    if parsed_date is None or isinstance(parsed_date, datetime):
        return parsed_date
    raise TypeError(f"Unexpected parsed date type: {type(parsed_date)}")


def route_after_collect(
    state: NewsletterState,
) -> Literal["handle_error", "process_articles"]:
    """Route after collection without embedding inline lambdas in the legacy graph."""
    return "handle_error" if state.get("status") == "error" else "process_articles"


def route_after_process(
    state: NewsletterState,
) -> Literal["handle_error", "score_articles"]:
    """Route after processing based on processed article availability."""
    if state.get("status") == "error":
        return "handle_error"
    return "score_articles" if state.get("processed_articles") else "handle_error"


def route_after_score(
    state: NewsletterState,
) -> Literal["handle_error", "summarize_articles"]:
    """Route after scoring while preserving the legacy status contract."""
    return "handle_error" if state.get("status") == "error" else "summarize_articles"


def route_after_summarize(
    state: NewsletterState,
) -> Literal["handle_error", "compose_newsletter"]:
    """Route after summarization while preserving the legacy status contract."""
    return "handle_error" if state.get("status") == "error" else "compose_newsletter"


def route_after_compose(
    state: NewsletterState,
) -> Literal["handle_error", "complete"]:
    """Return a stable symbolic route after composition."""
    return "handle_error" if state.get("status") == "error" else "complete"


def build_initial_graph_state(
    *,
    keywords: List[str],
    news_period_days: int,
    domain: Optional[str],
    template_style: str,
    email_compatible: bool,
    newsletter_topic: str,
    workflow_start: float,
    theme_time: float,
) -> NewsletterState:
    """Create the initial workflow state for the legacy graph runtime."""
    return {
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


def build_newsletter_chain_payload(
    state: NewsletterState,
    ranked_articles: List[Dict[str, Any]],
    template_style: str,
) -> Dict[str, Any]:
    """Build chain input payload without coupling the helper to the chain runtime."""
    return {
        "articles": ranked_articles,
        "keywords": state.get("keywords", []),
        "domain": state.get("domain", "") or "",
        "email_compatible": state.get("email_compatible", False),
        "template_style": template_style,
    }


def normalize_summary_chain_result(
    result: Any,
    *,
    state: NewsletterState,
    template_style: str,
    article_count: int,
    generated_at: datetime,
) -> tuple[str, Dict[str, Any], str]:
    """Normalize legacy and structured chain results into graph state payloads."""
    if isinstance(result, str):
        newsletter_html = result
        sections: List[Dict[str, Any]] = []
        structured_data: Dict[str, Any] = {
            "newsletter_topic": state.get("domain", "") or "",
            "keywords": state.get("keywords", []),
            "generation_date": generated_at.strftime("%Y-%m-%d"),
            "articles_count": article_count,
        }
    elif isinstance(result, dict):
        newsletter_html = str(result.get("html", ""))
        raw_structured_data = result.get("structured_data") or {}
        structured_data = (
            dict(raw_structured_data) if isinstance(raw_structured_data, dict) else {}
        )
        raw_sections = result.get("sections") or []
        sections = list(raw_sections) if isinstance(raw_sections, list) else []
        structured_data.update(
            {
                "keywords": state.get("keywords", []),
                "domain": state.get("domain", "") or "",
                "template_style": template_style,
                "email_compatible": state.get("email_compatible", False),
                "articles_count": article_count,
                "generation_timestamp": generated_at.isoformat(),
            }
        )
    else:
        raise ValueError(
            f"Unexpected result type from newsletter chain: {type(result)}"
        )

    newsletter_topic = str(
        structured_data.get("newsletter_topic", state.get("domain", "") or "")
        or state.get("domain", "")
        or ""
    )

    return (
        newsletter_html,
        {
            "sections": sections,
            "structured_data": structured_data,
        },
        newsletter_topic,
    )


def build_generation_info(
    final_state: NewsletterState,
    cost_summary: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build stable generation metrics for the public inspection hook."""
    generation_info: Dict[str, Any] = {
        "step_times": final_state.get("step_times", {}),
        "total_time": final_state.get("total_time"),
    }
    if cost_summary:
        generation_info["cost_summary"] = cost_summary
    return generation_info


def resolve_generation_result(final_state: NewsletterState) -> tuple[str, str]:
    """Resolve the final workflow state into the legacy public return tuple."""
    if (
        final_state.get("status") == "complete"
        and final_state.get("newsletter_html") is not None
    ):
        return str(final_state["newsletter_html"]), "success"

    error_message = final_state.get("error", "알 수 없는 오류 발생")
    return str(error_message if error_message is not None else "알 수 없는 오류 발생"), "error"
