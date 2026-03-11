from __future__ import annotations

import json
from typing import Any

import pytest
import requests

import newsletter_core.infrastructure.tools_search_runtime as runtime_adapters
from newsletter_core.application.tools_search_flow import SerperSearchPlan


class _FakeResponse:
    def __init__(
        self,
        *,
        payload: Any = None,
        text: str = "",
        status_error: Exception | None = None,
    ) -> None:
        self.payload = payload
        self.text = text
        self.status_error = status_error

    def raise_for_status(self) -> None:
        if self.status_error is not None:
            raise self.status_error

    def json(self) -> Any:
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def test_build_serper_request_kwargs_preserves_legacy_request_shape() -> None:
    search_plan = SerperSearchPlan(
        keyword="AI",
        num_results=3,
        url="https://google.serper.dev/news",
        headers={"X-API-KEY": "dummy", "Content-Type": "application/json"},
        payload='{"q": "AI", "gl": "kr", "num": 3}',
    )

    assert runtime_adapters.build_serper_request_kwargs(search_plan) == {
        "method": "POST",
        "url": "https://google.serper.dev/news",
        "headers": {
            "X-API-KEY": "dummy",
            "Content-Type": "application/json",
        },
        "data": '{"q": "AI", "gl": "kr", "num": 3}',
    }


def test_execute_serper_search_request_calls_request_and_decodes_json() -> None:
    calls: dict[str, Any] = {}
    search_plan = SerperSearchPlan(
        keyword="AI",
        num_results=3,
        url="https://google.serper.dev/news",
        headers={"X-API-KEY": "dummy", "Content-Type": "application/json"},
        payload='{"q": "AI", "gl": "kr", "num": 3}',
    )

    def fake_request(**kwargs: Any) -> _FakeResponse:
        calls.update(kwargs)
        return _FakeResponse(payload={"news": [{"title": "AI"}]})

    results = runtime_adapters.execute_serper_search_request(
        search_plan,
        request=fake_request,
    )

    assert calls == {
        "method": "POST",
        "url": "https://google.serper.dev/news",
        "headers": {
            "X-API-KEY": "dummy",
            "Content-Type": "application/json",
        },
        "data": '{"q": "AI", "gl": "kr", "num": 3}',
    }
    assert results == {"news": [{"title": "AI"}]}


def test_execute_serper_search_request_normalizes_request_errors() -> None:
    search_plan = SerperSearchPlan(
        keyword="AI",
        num_results=3,
        url="https://google.serper.dev/news",
        headers={"X-API-KEY": "dummy", "Content-Type": "application/json"},
        payload='{"q": "AI"}',
    )

    with pytest.raises(Exception) as exc_info:
        runtime_adapters.execute_serper_search_request(
            search_plan,
            request=lambda **_kwargs: (_ for _ in ()).throw(
                requests.exceptions.Timeout("timed out")
            ),
        )

    assert type(exc_info.value).__name__ == "SerperSearchRequestError"
    assert str(exc_info.value) == "timed out"


def test_execute_serper_search_request_normalizes_http_status_errors() -> None:
    search_plan = SerperSearchPlan(
        keyword="AI",
        num_results=3,
        url="https://google.serper.dev/news",
        headers={"X-API-KEY": "dummy", "Content-Type": "application/json"},
        payload='{"q": "AI"}',
    )

    with pytest.raises(Exception) as exc_info:
        runtime_adapters.execute_serper_search_request(
            search_plan,
            request=lambda **_kwargs: _FakeResponse(
                status_error=requests.exceptions.HTTPError("503 server error")
            ),
        )

    assert type(exc_info.value).__name__ == "SerperSearchRequestError"
    assert str(exc_info.value) == "503 server error"


def test_decode_serper_response_json_normalizes_json_error() -> None:
    response = _FakeResponse(
        payload=json.JSONDecodeError("bad json", "{}", 0),
        text="not-json",
    )

    with pytest.raises(Exception) as exc_info:
        runtime_adapters.decode_serper_response_json(response)

    assert type(exc_info.value).__name__ == "SerperSearchResponseDecodeError"
    assert str(exc_info.value) == "Failed to decode Serper response JSON."
    assert exc_info.value.response_text == "not-json"
