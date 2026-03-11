"""Unit and delegation tests for extracted graph node helpers."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

import newsletter.graph as graph_module
from newsletter_core.application import graph_node_helpers


def _make_state(**overrides):
    state = {
        "keywords": ["AI"],
        "news_period_days": 7,
        "domain": "AI",
        "template_style": "compact",
        "email_compatible": False,
        "collected_articles": None,
        "processed_articles": None,
        "ranked_articles": None,
        "article_summaries": None,
        "category_summaries": None,
        "newsletter_topic": "AI",
        "newsletter_html": None,
        "error": None,
        "status": "collecting",
        "start_time": 1.0,
        "step_times": {},
        "total_time": None,
    }
    state.update(overrides)
    return state


@pytest.mark.unit
def test_collect_query_and_slug_helpers_preserve_legacy_format() -> None:
    state = _make_state(domain="AI Mobility", keywords=["AI", "Battery"])

    assert (
        graph_node_helpers.build_collect_keyword_query(["AI", "Battery"])
        == "AI, Battery"
    )
    assert graph_node_helpers.resolve_graph_domain_slug(state) == "AI_Mobility"
    assert graph_node_helpers.resolve_graph_keywords_slug(state) == "AI_Battery"
    assert (
        graph_node_helpers.resolve_graph_domain_slug(_make_state(domain=None))
        == "general"
    )


@pytest.mark.unit
def test_filter_articles_for_processing_keeps_recent_missing_and_unparseable() -> None:
    current_time = datetime(2026, 3, 11, 12, 0, tzinfo=timezone.utc)
    filtered = graph_node_helpers.filter_articles_for_processing(
        [
            {"title": "recent", "date": "2026-03-10T10:00:00Z"},
            {"title": "old", "date": "2026-02-20T10:00:00Z"},
            {"title": "missing", "date": "날짜 없음"},
            {"title": "bad", "date": "not-a-date"},
        ],
        news_period_days=7,
        current_time=current_time,
    )

    assert [article["title"] for article in filtered] == ["recent", "missing", "bad"]


@pytest.mark.unit
def test_sort_articles_by_graph_date_desc_matches_legacy_ordering() -> None:
    sorted_articles = graph_node_helpers.sort_articles_by_graph_date_desc(
        [
            {"title": "older", "date": "2026-03-09T09:00:00Z"},
            {"title": "missing", "date": "날짜 없음"},
            {"title": "newer", "date": "2026-03-10T09:00:00Z"},
        ]
    )

    assert [article["title"] for article in sorted_articles] == [
        "newer",
        "older",
        "missing",
    ]


@pytest.mark.unit
def test_state_builders_preserve_node_status_and_step_times() -> None:
    collect_state = graph_node_helpers.build_collect_success_state(
        _make_state(), articles=[{"title": "A"}], elapsed=1.2
    )
    score_error_state = graph_node_helpers.build_score_error_state(
        _make_state(status="scoring"),
        error_message="broken",
        elapsed=2.5,
    )
    summarize_state = graph_node_helpers.build_summarize_success_state(
        _make_state(status="scoring_complete"),
        newsletter_html="<html>ok</html>",
        category_summaries={"sections": []},
        newsletter_topic="AI Weekly",
        elapsed=3.5,
    )
    compose_state = graph_node_helpers.build_compose_success_state(
        _make_state(status="summarizing_complete"),
        newsletter_html="<html>done</html>",
        elapsed=4.0,
    )

    assert collect_state["status"] == "processing"
    assert collect_state["step_times"]["collect_articles"] == 1.2
    assert score_error_state["status"] == "error"
    assert score_error_state["error"] == "broken"
    assert score_error_state["step_times"]["score_articles"] == 2.5
    assert summarize_state["status"] == "summarizing_complete"
    assert summarize_state["newsletter_topic"] == "AI Weekly"
    assert summarize_state["step_times"]["summarize"] == 3.5
    assert compose_state["status"] == "complete"
    assert compose_state["newsletter_html"] == "<html>done</html>"
    assert compose_state["step_times"]["compose"] == 4.0


@pytest.mark.unit
def test_summary_and_compose_resolution_helpers_match_legacy_defaults() -> None:
    assert graph_node_helpers.resolve_scoring_domain(_make_state(domain=None)) == "AI"
    assert graph_node_helpers.resolve_summary_chain_style(_make_state()) == (
        "compact",
        True,
    )
    assert graph_node_helpers.resolve_summary_chain_style(
        _make_state(template_style="detailed")
    ) == ("detailed", False)
    assert (
        graph_node_helpers.resolve_compose_html("<html>ok</html>") == "<html>ok</html>"
    )
    assert (
        graph_node_helpers.resolve_compose_html(None)
        == "<html><body>Newsletter generation failed</body></html>"
    )


@pytest.mark.unit
def test_collect_articles_node_delegates_keyword_and_state_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}
    fake_tools = ModuleType("newsletter.tools")
    fake_tools.search_news_articles = SimpleNamespace(
        invoke=lambda payload: [{"title": "A", "payload": payload}]
    )

    monkeypatch.setitem(sys.modules, "newsletter.tools", fake_tools)

    def _fake_keyword_query(keywords):
        captured["keywords"] = keywords
        return "AI"

    monkeypatch.setattr(
        graph_module, "build_collect_keyword_query", _fake_keyword_query
    )

    def _fake_collect_success(state, *, articles, elapsed):
        captured["articles"] = articles
        captured["elapsed"] = elapsed
        return _make_state(
            collected_articles=articles,
            status="processing",
            step_times={"collect_articles": elapsed},
        )

    monkeypatch.setattr(
        graph_module,
        "build_collect_success_state",
        _fake_collect_success,
    )

    result = graph_module.collect_articles_node(_make_state())

    assert captured["keywords"] == ["AI"]
    assert result["status"] == "processing"
    assert result["collected_articles"][0]["title"] == "A"


@pytest.mark.unit
def test_process_articles_node_delegates_filter_sort_and_state_helpers(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    captured = {}
    fake_article_filter = ModuleType("newsletter.article_filter")
    fake_article_filter.remove_duplicate_articles = lambda articles: articles

    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(sys.modules, "newsletter.article_filter", fake_article_filter)

    def _fake_filter(articles, *, news_period_days, current_time):
        captured["filter"] = (
            articles,
            news_period_days,
            current_time.tzinfo is not None,
        )
        return [{"title": "filtered", "date": "2026-03-10T09:00:00Z"}]

    def _fake_sort(articles):
        captured["sort"] = articles
        return [{"title": "sorted", "date": "2026-03-10T09:00:00Z"}]

    def _fake_success(state, *, processed_articles, elapsed):
        captured["success"] = (processed_articles, elapsed)
        return _make_state(
            processed_articles=processed_articles,
            status="scoring",
            step_times={"process_articles": elapsed},
        )

    monkeypatch.setattr(graph_module, "filter_articles_for_processing", _fake_filter)
    monkeypatch.setattr(graph_module, "sort_articles_by_graph_date_desc", _fake_sort)
    monkeypatch.setattr(graph_module, "build_process_success_state", _fake_success)

    result = graph_module.process_articles_node(
        _make_state(
            collected_articles=[{"title": "raw", "date": "2026-03-10T09:00:00Z"}]
        )
    )

    assert captured["filter"][1] == 7
    assert captured["filter"][2] is True
    assert captured["sort"] == [{"title": "filtered", "date": "2026-03-10T09:00:00Z"}]
    assert result["processed_articles"] == [
        {"title": "sorted", "date": "2026-03-10T09:00:00Z"}
    ]
    assert result["status"] == "scoring"


@pytest.mark.unit
def test_summarize_articles_node_delegates_style_and_success_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = {"html": "<html>ok</html>"}
    captured = {}

    def _fake_resolve_style(state):
        captured["style_state"] = state
        return ("compact", True)

    monkeypatch.setattr(
        graph_module, "resolve_summary_chain_style", _fake_resolve_style
    )
    monkeypatch.setattr(
        graph_module, "get_newsletter_chain", lambda is_compact: fake_chain
    )
    monkeypatch.setattr(
        graph_module,
        "normalize_summary_chain_result",
        lambda result, **kwargs: (
            "<html>ok</html>",
            {"sections": [], "structured_data": {}},
            "AI",
        ),
    )

    def _fake_success(
        state, *, newsletter_html, category_summaries, newsletter_topic, elapsed
    ):
        captured["success"] = (
            newsletter_html,
            category_summaries,
            newsletter_topic,
            elapsed,
        )
        return _make_state(
            newsletter_html=newsletter_html,
            category_summaries=category_summaries,
            newsletter_topic=newsletter_topic,
            status="summarizing_complete",
            step_times={"summarize": elapsed},
        )

    monkeypatch.setattr(graph_module, "build_summarize_success_state", _fake_success)

    result = graph_module.summarize_articles_node(
        _make_state(
            ranked_articles=[{"title": "A"}],
            status="scoring_complete",
        )
    )

    assert captured["style_state"]["template_style"] == "compact"
    assert result["newsletter_html"] == "<html>ok</html>"
    assert result["status"] == "summarizing_complete"
