"""Stable public API for newsletter generation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict, Union

from newsletter import graph, tools


class NewsletterGenerationError(Exception):
    """Raised when newsletter generation cannot produce a successful result."""


class GenerationStats(TypedDict, total=False):
    step_times: Dict[str, float]
    total_time: float
    cost_summary: Dict[str, Any]


class NewsletterResult(TypedDict):
    status: str
    html_content: str
    title: str
    generation_stats: GenerationStats
    input_params: Dict[str, Any]
    error: Optional[str]


@dataclass
class GenerateNewsletterRequest:
    keywords: Optional[Union[str, List[str]]] = None
    domain: Optional[str] = None
    template_style: str = "compact"
    email_compatible: bool = False
    period: int = 14
    suggest_count: int = 10


def _normalize_keywords(raw: Optional[Union[str, List[str]]]) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [item.strip() for item in raw.split(",") if item.strip()]
    return [str(item).strip() for item in raw if str(item).strip()]


def _extract_title(html_content: str, fallback: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html_content, flags=re.IGNORECASE)
    if match and match.group(1).strip():
        return match.group(1).strip()
    return fallback


def _resolve_keywords(request: GenerateNewsletterRequest) -> List[str]:
    keywords = _normalize_keywords(request.keywords)
    if keywords:
        return keywords

    if request.domain:
        generated = tools.generate_keywords_with_gemini(
            request.domain,
            count=max(1, int(request.suggest_count)),
        )
        normalized = _normalize_keywords(generated)
        if normalized:
            return normalized
        raise NewsletterGenerationError(
            f"Failed to generate keywords from domain: {request.domain}"
        )

    raise NewsletterGenerationError("Either keywords or domain must be provided")


def generate_newsletter(request: GenerateNewsletterRequest) -> NewsletterResult:
    """Generate newsletter HTML and return a stable response schema."""
    keywords = _resolve_keywords(request)

    try:
        html_or_error, status = graph.generate_newsletter(
            keywords,
            news_period_days=request.period,
            domain=request.domain,
            template_style=request.template_style,
            email_compatible=request.email_compatible,
        )
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise NewsletterGenerationError(str(exc)) from exc

    info = graph.get_last_generation_info() or {}
    stats: GenerationStats = {
        "step_times": info.get("step_times", {}),
        "total_time": info.get("total_time", 0.0),
    }
    if info.get("cost_summary"):
        stats["cost_summary"] = info["cost_summary"]

    input_params: Dict[str, Any] = {
        "keywords": keywords,
        "domain": request.domain,
        "template_style": request.template_style,
        "email_compatible": request.email_compatible,
        "period": request.period,
        "suggest_count": request.suggest_count,
    }

    if status != "success":
        message = str(html_or_error)
        raise NewsletterGenerationError(message)

    title_fallback = (
        f"Newsletter: {request.domain}"
        if request.domain
        else f"Newsletter: {', '.join(keywords[:3])}"
    )
    title = _extract_title(str(html_or_error), title_fallback)

    return {
        "status": "success",
        "html_content": str(html_or_error),
        "title": title,
        "generation_stats": stats,
        "input_params": input_params,
        "error": None,
    }


def suggest_keywords(domain: str, count: int = 10) -> List[str]:
    """Suggest keywords for a domain via stable public facade."""
    return tools.generate_keywords_with_gemini(domain, count=count)


__all__ = [
    "GenerateNewsletterRequest",
    "GenerationStats",
    "NewsletterGenerationError",
    "NewsletterResult",
    "generate_newsletter",
    "suggest_keywords",
]
