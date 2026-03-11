"""Runtime adapter helpers for the legacy newsletter.tools search boundary."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, cast

import requests  # type: ignore[import-untyped]

from newsletter_core.application.tools_search_flow import (
    SerperSearchPlan,
    SerperSearchRequestError,
    SerperSearchResponseDecodeError,
)

SerperRequestCallable = Callable[..., Any]


def build_serper_request_kwargs(search_plan: SerperSearchPlan) -> dict[str, Any]:
    """Preserve the legacy raw request shape for one Serper search plan."""

    return {
        "method": "POST",
        "url": search_plan.url,
        "headers": search_plan.headers,
        "data": search_plan.payload,
    }


def decode_serper_response_json(response: Any) -> dict[str, Any]:
    """Decode one Serper response body without changing legacy error semantics."""

    try:
        raw_results = response.json()
    except json.JSONDecodeError as exc:
        response_text = getattr(response, "text", "")
        raise SerperSearchResponseDecodeError(response_text) from exc

    return cast(dict[str, Any], raw_results)


def execute_serper_search_request(
    search_plan: SerperSearchPlan,
    *,
    request: SerperRequestCallable | None = None,
) -> dict[str, Any]:
    """Execute one Serper search plan through the infrastructure boundary."""

    request_callable = request or requests.request
    try:
        response = request_callable(**build_serper_request_kwargs(search_plan))
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise SerperSearchRequestError(str(exc)) from exc

    return decode_serper_response_json(response)


__all__ = [
    "SerperRequestCallable",
    "build_serper_request_kwargs",
    "decode_serper_response_json",
    "execute_serper_search_request",
]
