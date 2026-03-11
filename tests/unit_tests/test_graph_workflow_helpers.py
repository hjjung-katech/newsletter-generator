"""Unit and delegation tests for extracted graph workflow helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

import newsletter.cost_tracking as cost_tracking_module
import newsletter.graph as graph_module
from newsletter_core.application import graph_workflow


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
def test_build_initial_graph_state_sets_expected_defaults() -> None:
    state = graph_workflow.build_initial_graph_state(
        keywords=["AI", "Semiconductor"],
        news_period_days=14,
        domain=None,
        template_style="compact",
        email_compatible=True,
        newsletter_topic="AI",
        workflow_start=10.0,
        theme_time=1.5,
    )

    assert state["keywords"] == ["AI", "Semiconductor"]
    assert state["domain"] is None
    assert state["status"] == "collecting"
    assert state["step_times"] == {"extract_theme": 1.5}
    assert state["newsletter_html"] is None


@pytest.mark.unit
@pytest.mark.parametrize(
    ("helper", "state_overrides", "expected"),
    [
        (
            graph_workflow.route_after_collect,
            {"status": "processing"},
            "process_articles",
        ),
        (graph_workflow.route_after_collect, {"status": "error"}, "handle_error"),
        (
            graph_workflow.route_after_process,
            {"status": "scoring", "processed_articles": [{"title": "ok"}]},
            "score_articles",
        ),
        (
            graph_workflow.route_after_process,
            {"status": "scoring", "processed_articles": []},
            "handle_error",
        ),
        (graph_workflow.route_after_process, {"status": "error"}, "handle_error"),
        (
            graph_workflow.route_after_score,
            {"status": "scoring_complete"},
            "summarize_articles",
        ),
        (
            graph_workflow.route_after_summarize,
            {"status": "summarizing_complete"},
            "compose_newsletter",
        ),
        (graph_workflow.route_after_compose, {"status": "complete"}, "complete"),
        (graph_workflow.route_after_compose, {"status": "error"}, "handle_error"),
    ],
)
def test_route_helpers_preserve_legacy_contract(
    helper, state_overrides, expected
) -> None:
    assert helper(_make_state(**state_overrides)) == expected


@pytest.mark.unit
def test_build_newsletter_chain_payload_uses_state_fields() -> None:
    payload = graph_workflow.build_newsletter_chain_payload(
        _make_state(domain=None, email_compatible=True),
        [{"title": "A"}],
        "detailed",
    )

    assert payload == {
        "articles": [{"title": "A"}],
        "keywords": ["AI"],
        "domain": "",
        "email_compatible": True,
        "template_style": "detailed",
    }


@pytest.mark.unit
def test_normalize_summary_chain_result_supports_legacy_html() -> None:
    generated_at = datetime(2026, 3, 11, 12, 0, tzinfo=timezone.utc)
    html, category_summaries, topic = graph_workflow.normalize_summary_chain_result(
        "<html>legacy</html>",
        state=_make_state(domain="Mobility"),
        template_style="compact",
        article_count=3,
        generated_at=generated_at,
    )

    assert html == "<html>legacy</html>"
    assert category_summaries["sections"] == []
    assert category_summaries["structured_data"]["generation_date"] == "2026-03-11"
    assert category_summaries["structured_data"]["articles_count"] == 3
    assert topic == "Mobility"


@pytest.mark.unit
def test_normalize_summary_chain_result_supports_structured_payload() -> None:
    generated_at = datetime(2026, 3, 11, 12, 30, tzinfo=timezone.utc)
    html, category_summaries, topic = graph_workflow.normalize_summary_chain_result(
        {
            "html": "<html>structured</html>",
            "sections": [{"title": "Top"}],
            "structured_data": {"newsletter_topic": "AI Weekly"},
        },
        state=_make_state(domain="AI", email_compatible=True),
        template_style="compact",
        article_count=2,
        generated_at=generated_at,
    )

    assert html == "<html>structured</html>"
    assert category_summaries["sections"] == [{"title": "Top"}]
    assert category_summaries["structured_data"]["domain"] == "AI"
    assert category_summaries["structured_data"]["email_compatible"] is True
    assert (
        category_summaries["structured_data"]["generation_timestamp"]
        == "2026-03-11T12:30:00+00:00"
    )
    assert topic == "AI Weekly"


@pytest.mark.unit
def test_build_generation_info_includes_cost_summary_when_present() -> None:
    info = graph_workflow.build_generation_info(
        _make_state(step_times={"collect": 1.0}, total_time=2.0),
        {"total_cost": 0.25},
    )

    assert info == {
        "step_times": {"collect": 1.0},
        "total_time": 2.0,
        "cost_summary": {"total_cost": 0.25},
    }


@pytest.mark.unit
@pytest.mark.parametrize(
    ("state_overrides", "expected"),
    [
        (
            {"status": "complete", "newsletter_html": "<html>ok</html>"},
            ("<html>ok</html>", "success"),
        ),
        ({"status": "error", "error": "broken"}, ("broken", "error")),
        ({"status": "error", "error": None}, ("알 수 없는 오류 발생", "error")),
    ],
)
def test_resolve_generation_result_matches_legacy_tuple_contract(
    state_overrides, expected
) -> None:
    assert (
        graph_workflow.resolve_generation_result(_make_state(**state_overrides))
        == expected
    )


@pytest.mark.unit
def test_summarize_articles_node_delegates_result_normalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = {"html": "<html>ok</html>"}
    called = {}

    def _fake_normalize(result, **kwargs):
        called["result"] = result
        called["kwargs"] = kwargs
        return ("<html>ok</html>", {"sections": [], "structured_data": {}}, "AI")

    monkeypatch.setattr(
        graph_module, "get_newsletter_chain", lambda is_compact: fake_chain
    )
    monkeypatch.setattr(graph_module, "normalize_summary_chain_result", _fake_normalize)

    updated = graph_module.summarize_articles_node(
        _make_state(
            ranked_articles=[{"title": "A"}],
            step_times={},
            status="scoring_complete",
        )
    )

    assert called["result"] == {"html": "<html>ok</html>"}
    assert called["kwargs"]["article_count"] == 1
    assert updated["newsletter_html"] == "<html>ok</html>"
    assert updated["status"] == "summarizing_complete"


@pytest.mark.unit
def test_generate_newsletter_delegates_state_build_and_result_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel_initial_state = _make_state(status="collecting")
    sentinel_final_state = _make_state(
        status="complete",
        newsletter_html="<html>delegated</html>",
        step_times={"collect": 0.1},
        total_time=0.5,
    )
    captured = {}

    class _FakeGraph:
        def invoke(self, state):
            assert state is sentinel_initial_state
            return sentinel_final_state

    monkeypatch.setattr(cost_tracking_module, "clear_recent_callbacks", lambda: None)
    monkeypatch.setattr(
        cost_tracking_module, "get_cost_summary", lambda: {"total_cost": 0.1}
    )

    def _fake_build_initial_graph_state(**kwargs):
        captured["initial_kwargs"] = kwargs
        return sentinel_initial_state

    monkeypatch.setattr(
        graph_module,
        "build_initial_graph_state",
        _fake_build_initial_graph_state,
    )
    monkeypatch.setattr(graph_module, "create_newsletter_graph", lambda: _FakeGraph())
    monkeypatch.setattr(
        graph_module,
        "build_generation_info",
        lambda final_state, cost_summary: {
            "step_times": final_state.get("step_times", {}),
            "total_time": final_state.get("total_time"),
            "cost_summary": cost_summary,
        },
    )
    monkeypatch.setattr(
        graph_module,
        "resolve_generation_result",
        lambda final_state: ("<html>delegated</html>", "success"),
    )

    result = graph_module.generate_newsletter(
        ["AI"], news_period_days=3, template_style="compact"
    )

    assert captured["initial_kwargs"]["newsletter_topic"] == "AI"
    assert result == ("<html>delegated</html>", "success")
    assert graph_module.get_last_generation_info()["cost_summary"] == {
        "total_cost": 0.1
    }
