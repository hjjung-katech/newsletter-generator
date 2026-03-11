"""Pure helper functions extracted from the legacy newsletter.tools module."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

_MAX_SERPER_RESULTS = 20


@dataclass(frozen=True)
class SearchRequest:
    """Normalized search input for the legacy search tool wrapper."""

    keywords: tuple[str, ...]
    num_results: int


@dataclass(frozen=True)
class ParsedSerperResponse:
    """Parsed Serper response payload for the legacy search tool wrapper."""

    articles: list[dict[str, Any]]
    container_names: tuple[str, ...]
    container_count: int


def resolve_search_request(
    keywords: str,
    num_results: int,
    *,
    max_results: int = _MAX_SERPER_RESULTS,
) -> SearchRequest:
    """Normalize the legacy search request without changing its semantics."""

    capped_num_results = num_results if num_results <= max_results else max_results
    return SearchRequest(
        keywords=tuple(keyword.strip() for keyword in keywords.split(",")),
        num_results=capped_num_results,
    )


def build_serper_payload(keyword: str, num_results: int) -> str:
    """Build the legacy Serper news payload."""

    return json.dumps({"q": keyword, "gl": "kr", "num": num_results})


def _select_serper_containers(
    results: Mapping[str, Any]
) -> tuple[list[Any], tuple[str, ...]]:
    containers: list[Any] = []
    container_names: list[str] = []

    if "news" in results:
        container_names.append("news")
        containers.extend(results["news"])

    if "topStories" in results:
        container_names.append("topStories")
        containers.extend(results["topStories"])

    if "organic" in results and not containers:
        container_names.append("organic")
        containers.extend(results["organic"])

    return containers, tuple(container_names)


def shape_serper_article(item: Mapping[str, Any]) -> dict[str, Any]:
    """Convert a Serper item into the legacy article shape."""

    return {
        "title": item.get("title", "제목 없음"),
        "url": item.get("link", ""),
        "link": item.get("link", ""),
        "snippet": item.get("snippet") or item.get("description", "내용 없음"),
        "source": item.get("source", "출처 없음"),
        "date": item.get("date") or item.get("publishedAt") or "날짜 없음",
    }


def parse_serper_response(
    results: Mapping[str, Any],
    num_results: int,
) -> ParsedSerperResponse:
    """Parse the Serper response while preserving legacy container precedence."""

    containers, container_names = _select_serper_containers(results)
    articles = [
        shape_serper_article(cast(Mapping[str, Any], item))
        for item in containers[: min(num_results, len(containers))]
    ]
    return ParsedSerperResponse(
        articles=articles,
        container_names=container_names,
        container_count=len(containers),
    )


def parse_generated_keywords(response_content: str, count: int) -> list[str]:
    """Normalize generated keyword lines without touching search validation."""

    keywords: list[str] = []
    for line in response_content.split("\n"):
        if not line.strip():
            continue

        clean_line = re.sub(r"^\d+\.?\s*", "", line.strip())
        clean_line = re.sub(r"\*\*(.+?)\*\*", r"\1", clean_line)
        clean_line = re.sub(r"\s*\(.+?\)\s*$", "", clean_line)

        if clean_line:
            keywords.append(clean_line)

    final_keywords = keywords[:count]
    if len(final_keywords) < count and keywords:
        final_keywords = keywords

    if len(final_keywords) == 1 and "," in final_keywords[0]:
        final_keywords = [kw.strip() for kw in final_keywords[0].split(",")][:count]

    return final_keywords


def _normalize_theme_keywords(keywords: str | Sequence[str]) -> list[str]:
    if isinstance(keywords, str):
        return [keyword.strip() for keyword in keywords.split(",") if keyword.strip()]
    return list(keywords)


def extract_common_theme_fallback(keywords: str | Sequence[str]) -> str:
    """Use the legacy heuristic fallback for theme extraction."""

    normalized_keywords = _normalize_theme_keywords(keywords)

    if len(normalized_keywords) <= 1:
        return normalized_keywords[0] if normalized_keywords else ""

    if len(normalized_keywords) <= 3:
        return ", ".join(normalized_keywords)

    return f"{normalized_keywords[0]} 외 {len(normalized_keywords) - 1}개 분야"


def sanitize_filename(text: str | None) -> str:
    """Normalize a filename using the legacy rules."""

    if not text:
        return "unknown"

    invalid_chars = r'[\\/*?:"<>|]'
    sanitized = re.sub(invalid_chars, "", text)
    sanitized = re.sub(r"\(([^)]*)\)", r"\1", sanitized)
    sanitized = sanitized.replace(" ", "_")
    sanitized = sanitized.replace(",", "")
    sanitized = sanitized.replace(".", "")
    sanitized = re.sub(r"_{2,}", "_", sanitized)

    if len(sanitized) > 50:
        words = sanitized.split("_")
        if len(words) > 3:
            result = "_".join(words[:3]) + "_etc"
            if len(result) > 50:
                result = result[:46] + "_etc"
            return result
        return sanitized[:46] + "_etc"

    return sanitized


def resolve_filename_theme(
    keywords: Any,
    domain: str | None,
    *,
    theme_extractor: Callable[[Any], str],
) -> str:
    """Resolve the pre-sanitized theme name using the legacy branch order."""

    if domain:
        return domain

    if isinstance(keywords, list) and len(keywords) == 1:
        return keywords[0]

    if (isinstance(keywords, list) and len(keywords) > 1) or (
        isinstance(keywords, str) and "," in keywords
    ):
        return theme_extractor(keywords)

    return keywords if isinstance(keywords, str) else ""


__all__ = [
    "ParsedSerperResponse",
    "SearchRequest",
    "build_serper_payload",
    "extract_common_theme_fallback",
    "parse_generated_keywords",
    "parse_serper_response",
    "resolve_filename_theme",
    "resolve_search_request",
    "sanitize_filename",
    "shape_serper_article",
]
