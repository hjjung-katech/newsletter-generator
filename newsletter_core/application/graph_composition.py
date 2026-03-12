"""Invocation-adjacent composition helpers for the legacy newsletter graph."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from newsletter_core.application.graph_node_helpers import (
    build_summarize_success_state,
    resolve_compose_html,
    resolve_graph_domain_slug,
    resolve_graph_keywords_slug,
    resolve_summary_chain_style,
)
from newsletter_core.application.graph_workflow import (
    NewsletterState,
    build_newsletter_chain_payload,
    normalize_summary_chain_result,
)


class SummaryInvocationPlan(TypedDict):
    """Pure summary invocation inputs for the legacy summarize node."""

    template_style: str
    is_compact: bool
    article_count: int
    chain_payload: Dict[str, Any]


class ComposePersistPlan(TypedDict):
    """Pure compose persistence inputs for the legacy compose node."""

    final_html: str
    domain_slug: str
    keywords_slug: str
    file_stem: str


class ThemeResolutionPlan(TypedDict):
    """Pure theme selection decision for generate_newsletter()."""

    newsletter_topic: str
    requires_theme_extraction: bool


def build_summary_invocation_plan(
    state: NewsletterState,
    ranked_articles: List[Dict[str, Any]],
) -> SummaryInvocationPlan:
    """Assemble the summarize-node invocation inputs without invoking the chain."""
    template_style, is_compact = resolve_summary_chain_style(state)
    return {
        "template_style": template_style,
        "is_compact": is_compact,
        "article_count": len(ranked_articles),
        "chain_payload": build_newsletter_chain_payload(
            state, ranked_articles, template_style
        ),
    }


def build_summarize_result_state(
    state: NewsletterState,
    result: Any,
    *,
    plan: SummaryInvocationPlan,
    generated_at: datetime,
    elapsed: float,
) -> NewsletterState:
    """Convert a summary chain result into the legacy summarize-node state update."""
    (
        newsletter_html,
        category_summaries,
        newsletter_topic,
    ) = normalize_summary_chain_result(
        result,
        state=state,
        template_style=plan["template_style"],
        article_count=plan["article_count"],
        generated_at=generated_at,
    )
    return build_summarize_success_state(
        state,
        newsletter_html=newsletter_html,
        category_summaries=category_summaries,
        newsletter_topic=newsletter_topic,
        elapsed=elapsed,
    )


def build_compose_persist_plan(
    state: NewsletterState,
    newsletter_html: Optional[str],
) -> ComposePersistPlan:
    """Build the non-IO compose persistence inputs around the legacy file write."""
    template_style = state.get("template_style", "detailed")
    return {
        "final_html": resolve_compose_html(newsletter_html),
        "domain_slug": resolve_graph_domain_slug(state),
        "keywords_slug": resolve_graph_keywords_slug(state),
        "file_stem": f"newsletter_{template_style}",
    }


def build_theme_resolution_plan(
    keywords: List[str],
    domain: Optional[str],
) -> ThemeResolutionPlan:
    """Resolve whether generate_newsletter() needs theme extraction."""
    if domain:
        return {
            "newsletter_topic": domain,
            "requires_theme_extraction": False,
        }
    if len(keywords) == 1:
        return {
            "newsletter_topic": keywords[0],
            "requires_theme_extraction": False,
        }
    return {
        "newsletter_topic": "",
        "requires_theme_extraction": True,
    }
