"""Search orchestration helpers extracted from the legacy newsletter.tools module."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final, Literal, cast

from newsletter_core.application.tools_support import (
    ParsedSerperResponse,
    SearchRequest,
    build_serper_payload,
    parse_serper_response,
    select_serper_containers,
)

_SERPER_NEWS_URL: Final[str] = "https://google.serper.dev/news"


@dataclass(frozen=True)
class SerperSearchPlan:
    """Precomputed request data for one legacy Serper keyword search."""

    keyword: str
    num_results: int
    url: str
    headers: dict[str, str]
    payload: str


@dataclass(frozen=True)
class SerperDebugEntry:
    """Raw-response debug details preserved for legacy logging."""

    index: int
    item_keys: tuple[str, ...]
    raw_date: Any
    raw_published_at: Any


@dataclass(frozen=True)
class SerperKeywordReport:
    """Structured success payload for one keyword search."""

    keyword: str
    parsed_response: ParsedSerperResponse
    raw_keys: tuple[str, ...]
    debug_entries: tuple[SerperDebugEntry, ...]
    response_preview: str | None

    @property
    def articles(self) -> list[dict[str, Any]]:
        return self.parsed_response.articles

    @property
    def article_count(self) -> int:
        return len(self.parsed_response.articles)

    @property
    def container_names(self) -> tuple[str, ...]:
        return self.parsed_response.container_names

    @property
    def container_count(self) -> int:
        return self.parsed_response.container_count


@dataclass(frozen=True)
class SerperKeywordFailure:
    """Structured failure payload for one keyword search."""

    keyword: str
    error_kind: Literal["request", "json"]
    message: str
    response_text: str | None = None


@dataclass(frozen=True)
class SerperLogMessage:
    """Structured log message for the legacy wrapper."""

    level: Literal["info", "warning", "debug", "error"]
    message: str


@dataclass(frozen=True)
class SerperSearchSummary:
    """Aggregated search results for the legacy wrapper."""

    keyword_article_counts: dict[str, int]
    all_articles: list[dict[str, Any]]


class SerperSearchRequestError(Exception):
    """Raised when the legacy wrapper cannot execute the HTTP request."""


class SerperSearchResponseDecodeError(Exception):
    """Raised when the legacy wrapper cannot decode the JSON response."""

    def __init__(self, response_text: str) -> None:
        super().__init__("Failed to decode Serper response JSON.")
        self.response_text = response_text


SerperSearchExecutor = Callable[[SerperSearchPlan], Mapping[str, Any]]


def build_serper_search_plans(
    search_request: SearchRequest,
    *,
    api_key: str,
) -> tuple[SerperSearchPlan, ...]:
    """Build stable per-keyword request plans for the legacy wrapper."""

    return tuple(
        SerperSearchPlan(
            keyword=keyword,
            num_results=search_request.num_results,
            url=_SERPER_NEWS_URL,
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
            payload=build_serper_payload(keyword, search_request.num_results),
        )
        for keyword in search_request.keywords
    )


def _build_debug_entries(
    results: Mapping[str, Any],
) -> tuple[SerperDebugEntry, ...]:
    container_items, _ = select_serper_containers(results)
    debug_entries: list[SerperDebugEntry] = []

    for index, raw_item in enumerate(container_items[:3]):
        if not isinstance(raw_item, Mapping):
            continue

        item = cast(Mapping[str, Any], raw_item)
        debug_entries.append(
            SerperDebugEntry(
                index=index,
                item_keys=tuple(str(key) for key in item.keys()),
                raw_date=item.get("date"),
                raw_published_at=item.get("publishedAt"),
            )
        )

    return tuple(debug_entries)


def execute_serper_search_plan(
    search_plan: SerperSearchPlan,
    *,
    executor: SerperSearchExecutor,
) -> SerperKeywordReport | SerperKeywordFailure:
    """Execute one keyword plan via an injected legacy HTTP executor."""

    try:
        results = executor(search_plan)
    except SerperSearchRequestError as exc:
        return SerperKeywordFailure(
            keyword=search_plan.keyword,
            error_kind="request",
            message=str(exc),
        )
    except SerperSearchResponseDecodeError as exc:
        return SerperKeywordFailure(
            keyword=search_plan.keyword,
            error_kind="json",
            message=str(exc),
            response_text=exc.response_text,
        )

    return SerperKeywordReport(
        keyword=search_plan.keyword,
        parsed_response=parse_serper_response(results, search_plan.num_results),
        raw_keys=tuple(str(key) for key in results.keys()),
        debug_entries=_build_debug_entries(results),
        response_preview=(
            json.dumps(results, ensure_ascii=False)[:300]
            if len(results.keys()) <= 3
            else None
        ),
    )


def summarize_serper_search_reports(
    reports: Sequence[SerperKeywordReport],
) -> SerperSearchSummary:
    """Aggregate per-keyword reports for the legacy wrapper."""

    keyword_article_counts = {
        report.keyword: report.article_count for report in reports
    }
    all_articles = [article for report in reports for article in report.articles]

    return SerperSearchSummary(
        keyword_article_counts=keyword_article_counts,
        all_articles=all_articles,
    )


def build_serper_keyword_log_messages(
    search_report: SerperKeywordReport,
) -> tuple[SerperLogMessage, ...]:
    """Preserve legacy logging messages without keeping formatting in the wrapper."""

    messages: list[SerperLogMessage] = [
        SerperLogMessage(
            level="info",
            message=(
                f"Found '{container_name}' results for keyword "
                f"'{search_report.keyword}'"
            ),
        )
        for container_name in search_report.container_names
    ]
    messages.append(
        SerperLogMessage(
            level="info",
            message=f"Total container items found: {search_report.container_count}",
        )
    )

    if not search_report.container_count and search_report.raw_keys:
        messages.append(
            SerperLogMessage(
                level="warning",
                message=(
                    "Warning: No result containers found. Available keys: "
                    f"{list(search_report.raw_keys)}"
                ),
            )
        )
        if search_report.response_preview is not None:
            messages.append(
                SerperLogMessage(
                    level="warning",
                    message=f"Response structure: {search_report.response_preview}...",
                )
            )

    for debug_entry in search_report.debug_entries:
        messages.append(
            SerperLogMessage(
                level="debug",
                message=(
                    f"Debug: Item keys (index: {debug_entry.index}): "
                    f"{list(debug_entry.item_keys)}"
                ),
            )
        )
        messages.append(
            SerperLogMessage(
                level="debug",
                message=(
                    "Debug: Date value: "
                    f"'{debug_entry.raw_date}' / PublishedAt: "
                    f"'{debug_entry.raw_published_at}'"
                ),
            )
        )

    if not search_report.articles:
        messages.append(
            SerperLogMessage(
                level="warning",
                message=(
                    "No articles could be parsed for keyword "
                    f"'{search_report.keyword}'."
                ),
            )
        )

    messages.append(
        SerperLogMessage(
            level="info",
            message=(
                f"Found {search_report.article_count} articles for keyword: "
                f"'{search_report.keyword}'"
            ),
        )
    )
    return tuple(messages)


def build_serper_failure_log_messages(
    search_failure: SerperKeywordFailure,
) -> tuple[SerperLogMessage, ...]:
    """Preserve legacy Serper error logging without reintroducing side effects."""

    if search_failure.error_kind == "request":
        return (
            SerperLogMessage(
                level="error",
                message=(
                    "Error fetching articles for keyword "
                    f"'{search_failure.keyword}' from Serper.dev: "
                    f"{search_failure.message}"
                ),
            ),
        )

    response_text = search_failure.response_text or ""
    return (
        SerperLogMessage(
            level="error",
            message=(
                "Error decoding JSON response for keyword "
                f"'{search_failure.keyword}' from Serper.dev. Response: "
                f"{response_text}"
            ),
        ),
    )


__all__ = [
    "SerperDebugEntry",
    "SerperKeywordFailure",
    "SerperKeywordReport",
    "SerperLogMessage",
    "SerperSearchExecutor",
    "SerperSearchPlan",
    "SerperSearchRequestError",
    "SerperSearchResponseDecodeError",
    "SerperSearchSummary",
    "build_serper_failure_log_messages",
    "build_serper_keyword_log_messages",
    "build_serper_search_plans",
    "execute_serper_search_plan",
    "summarize_serper_search_reports",
]
