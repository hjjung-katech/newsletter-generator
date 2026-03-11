from __future__ import annotations

import newsletter.tools as tools_module
from newsletter import config
from newsletter_core.application.tools_search_flow import (
    SerperKeywordFailure,
    SerperKeywordReport,
    SerperLogMessage,
    SerperSearchPlan,
    SerperSearchRequestError,
    SerperSearchResponseDecodeError,
    SerperSearchSummary,
    build_serper_failure_log_messages,
    build_serper_keyword_log_messages,
    build_serper_search_plans,
    execute_serper_search_plan,
    summarize_serper_search_reports,
)
from newsletter_core.application.tools_support import (
    ParsedSerperResponse,
    SearchRequest,
)


def test_build_serper_search_plans_preserves_keyword_order_and_request_shape() -> None:
    plans = build_serper_search_plans(
        SearchRequest(keywords=("AI", "반도체"), num_results=3),
        api_key="dummy-serper-key",
    )

    assert [plan.keyword for plan in plans] == ["AI", "반도체"]
    assert plans[0].url == "https://google.serper.dev/news"
    assert plans[0].headers == {
        "X-API-KEY": "dummy-serper-key",
        "Content-Type": "application/json",
    }
    assert plans[0].payload == '{"q": "AI", "gl": "kr", "num": 3}'


def test_execute_serper_search_plan_returns_report_with_debug_entries() -> None:
    search_plan = SerperSearchPlan(
        keyword="AI",
        num_results=2,
        url="https://google.serper.dev/news",
        headers={"X-API-KEY": "dummy", "Content-Type": "application/json"},
        payload='{"q": "AI"}',
    )

    report = execute_serper_search_plan(
        search_plan,
        executor=lambda _: {
            "news": [
                {
                    "title": "AI 제목",
                    "link": "https://example.com/ai",
                    "snippet": "AI 요약",
                    "source": "AI Source",
                    "date": "2026-03-11",
                }
            ],
            "topStories": [],
            "organic": [],
        },
    )

    assert isinstance(report, SerperKeywordReport)
    assert report.keyword == "AI"
    assert report.container_names == ("news", "topStories")
    assert report.container_count == 1
    assert report.article_count == 1
    assert report.debug_entries[0].item_keys == (
        "title",
        "link",
        "snippet",
        "source",
        "date",
    )
    assert report.response_preview is not None
    assert '"title": "AI 제목"' in report.response_preview


def test_execute_serper_search_plan_returns_request_failure() -> None:
    search_plan = SerperSearchPlan(
        keyword="AI",
        num_results=2,
        url="https://google.serper.dev/news",
        headers={"X-API-KEY": "dummy", "Content-Type": "application/json"},
        payload='{"q": "AI"}',
    )

    failure = execute_serper_search_plan(
        search_plan,
        executor=lambda _: (_ for _ in ()).throw(
            SerperSearchRequestError("network boom")
        ),
    )

    assert failure == SerperKeywordFailure(
        keyword="AI",
        error_kind="request",
        message="network boom",
        response_text=None,
    )


def test_execute_serper_search_plan_returns_json_failure() -> None:
    search_plan = SerperSearchPlan(
        keyword="AI",
        num_results=2,
        url="https://google.serper.dev/news",
        headers={"X-API-KEY": "dummy", "Content-Type": "application/json"},
        payload='{"q": "AI"}',
    )

    failure = execute_serper_search_plan(
        search_plan,
        executor=lambda _: (_ for _ in ()).throw(
            SerperSearchResponseDecodeError("raw body")
        ),
    )

    assert failure == SerperKeywordFailure(
        keyword="AI",
        error_kind="json",
        message="Failed to decode Serper response JSON.",
        response_text="raw body",
    )


def test_summarize_serper_search_reports_aggregates_articles_and_counts() -> None:
    reports = (
        SerperKeywordReport(
            keyword="AI",
            parsed_response=ParsedSerperResponse(
                articles=[
                    {
                        "title": "AI 기사",
                        "url": "https://example.com/ai",
                        "link": "https://example.com/ai",
                        "snippet": "AI",
                        "source": "테스트",
                        "date": "2026-03-11",
                    }
                ],
                container_names=("news",),
                container_count=1,
            ),
            raw_keys=("news",),
            debug_entries=(),
            response_preview='{"news": []}',
        ),
        SerperKeywordReport(
            keyword="반도체",
            parsed_response=ParsedSerperResponse(
                articles=[],
                container_names=("news",),
                container_count=0,
            ),
            raw_keys=("news",),
            debug_entries=(),
            response_preview='{"news": []}',
        ),
    )

    summary = summarize_serper_search_reports(reports)

    assert summary == SerperSearchSummary(
        keyword_article_counts={"AI": 1, "반도체": 0},
        all_articles=[
            {
                "title": "AI 기사",
                "url": "https://example.com/ai",
                "link": "https://example.com/ai",
                "snippet": "AI",
                "source": "테스트",
                "date": "2026-03-11",
            }
        ],
    )


def test_build_serper_keyword_log_messages_preserves_legacy_strings() -> None:
    report = SerperKeywordReport(
        keyword="AI",
        parsed_response=ParsedSerperResponse(
            articles=[],
            container_names=("news",),
            container_count=0,
        ),
        raw_keys=("news", "topStories"),
        debug_entries=(),
        response_preview='{"news": [], "topStories": []}',
    )

    messages = build_serper_keyword_log_messages(report)

    assert messages == (
        SerperLogMessage(
            level="info",
            message="Found 'news' results for keyword 'AI'",
        ),
        SerperLogMessage(
            level="info",
            message="Total container items found: 0",
        ),
        SerperLogMessage(
            level="warning",
            message="Warning: No result containers found. Available keys: ['news', 'topStories']",
        ),
        SerperLogMessage(
            level="warning",
            message='Response structure: {"news": [], "topStories": []}...',
        ),
        SerperLogMessage(
            level="warning",
            message="No articles could be parsed for keyword 'AI'.",
        ),
        SerperLogMessage(
            level="info",
            message="Found 0 articles for keyword: 'AI'",
        ),
    )


def test_build_serper_failure_log_messages_preserves_error_path() -> None:
    assert build_serper_failure_log_messages(
        SerperKeywordFailure(
            keyword="AI",
            error_kind="json",
            message="Failed to decode Serper response JSON.",
            response_text="raw body",
        )
    ) == (
        SerperLogMessage(
            level="error",
            message=(
                "Error decoding JSON response for keyword "
                "'AI' from Serper.dev. Response: raw body"
            ),
        ),
    )


def test_legacy_search_news_articles_delegates_to_core_search_flow(
    monkeypatch,
) -> None:
    calls: dict[str, object] = {}

    monkeypatch.setattr(config, "SERPER_API_KEY", "dummy-tools-key")

    def fake_resolve_search_request(keywords: str, num_results: int) -> SearchRequest:
        calls["raw_request"] = (keywords, num_results)
        return SearchRequest(keywords=("정제된 키워드",), num_results=3)

    def fake_build_serper_search_plans(
        search_request: SearchRequest, *, api_key: str
    ) -> tuple[SerperSearchPlan, ...]:
        calls["search_request"] = search_request
        calls["api_key"] = api_key
        return (
            SerperSearchPlan(
                keyword="정제된 키워드",
                num_results=3,
                url="https://example.com/serper",
                headers={"X-API-KEY": api_key},
                payload='{"q": "정제된 키워드"}',
            ),
        )

    def fake_execute_serper_search_plan(
        search_plan: SerperSearchPlan,
        *,
        executor,
    ) -> SerperKeywordReport:
        calls["search_plan"] = search_plan
        calls["executor"] = executor
        return SerperKeywordReport(
            keyword="정제된 키워드",
            parsed_response=ParsedSerperResponse(
                articles=[
                    {
                        "title": "정제된 기사",
                        "url": "https://example.com/article",
                        "link": "https://example.com/article",
                        "snippet": "요약",
                        "source": "테스트 소스",
                        "date": "2026-03-11",
                    }
                ],
                container_names=("news",),
                container_count=1,
            ),
            raw_keys=("news",),
            debug_entries=(),
            response_preview='{"news": [{"title": "정제된 기사"}]}',
        )

    def fake_summarize_serper_search_reports(
        reports: tuple[SerperKeywordReport, ...] | list[SerperKeywordReport],
    ) -> SerperSearchSummary:
        calls["reports"] = list(reports)
        return SerperSearchSummary(
            keyword_article_counts={"정제된 키워드": 1},
            all_articles=[
                {
                    "title": "정제된 기사",
                    "url": "https://example.com/article",
                    "link": "https://example.com/article",
                    "snippet": "요약",
                    "source": "테스트 소스",
                    "date": "2026-03-11",
                }
            ],
        )

    monkeypatch.setattr(
        tools_module, "resolve_search_request", fake_resolve_search_request
    )
    monkeypatch.setattr(
        tools_module, "build_serper_search_plans", fake_build_serper_search_plans
    )
    monkeypatch.setattr(
        tools_module, "execute_serper_search_plan", fake_execute_serper_search_plan
    )
    monkeypatch.setattr(
        tools_module,
        "summarize_serper_search_reports",
        fake_summarize_serper_search_reports,
    )

    result = tools_module.search_news_articles.invoke(
        {"keywords": "원본 키워드", "num_results": 99}
    )

    assert calls["raw_request"] == ("원본 키워드", 99)
    assert calls["search_request"] == SearchRequest(
        keywords=("정제된 키워드",), num_results=3
    )
    assert calls["api_key"] == "dummy-tools-key"
    assert calls["search_plan"] == SerperSearchPlan(
        keyword="정제된 키워드",
        num_results=3,
        url="https://example.com/serper",
        headers={"X-API-KEY": "dummy-tools-key"},
        payload='{"q": "정제된 키워드"}',
    )
    assert calls["executor"] is tools_module.execute_serper_search_request
    assert calls["reports"] == [
        SerperKeywordReport(
            keyword="정제된 키워드",
            parsed_response=ParsedSerperResponse(
                articles=[
                    {
                        "title": "정제된 기사",
                        "url": "https://example.com/article",
                        "link": "https://example.com/article",
                        "snippet": "요약",
                        "source": "테스트 소스",
                        "date": "2026-03-11",
                    }
                ],
                container_names=("news",),
                container_count=1,
            ),
            raw_keys=("news",),
            debug_entries=(),
            response_preview='{"news": [{"title": "정제된 기사"}]}',
        )
    ]
    assert result == [
        {
            "title": "정제된 기사",
            "url": "https://example.com/article",
            "link": "https://example.com/article",
            "snippet": "요약",
            "source": "테스트 소스",
            "date": "2026-03-11",
        }
    ]
