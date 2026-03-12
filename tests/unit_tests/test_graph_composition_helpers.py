"""Unit and delegation tests for extracted graph composition helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

import newsletter.cost_tracking as cost_tracking_module
import newsletter.graph as graph_module
from newsletter_core.application import graph_composition


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
def test_build_summary_invocation_plan_preserves_payload_contract() -> None:
    plan = graph_composition.build_summary_invocation_plan(
        _make_state(domain=None, email_compatible=True),
        [{"title": "A"}],
    )

    assert plan == {
        "template_style": "compact",
        "is_compact": True,
        "article_count": 1,
        "chain_payload": {
            "articles": [{"title": "A"}],
            "keywords": ["AI"],
            "domain": "",
            "email_compatible": True,
            "template_style": "compact",
        },
    }


@pytest.mark.unit
def test_build_summarize_result_state_delegates_normalization_and_state_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    def _fake_normalize(result, **kwargs):
        captured["normalize"] = (result, kwargs)
        return "<html>ok</html>", {"sections": []}, "AI Weekly"

    def _fake_success(
        state, *, newsletter_html, category_summaries, newsletter_topic, elapsed
    ):
        captured["success"] = (
            state,
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

    monkeypatch.setattr(
        graph_composition,
        "normalize_summary_chain_result",
        _fake_normalize,
    )
    monkeypatch.setattr(
        graph_composition,
        "build_summarize_success_state",
        _fake_success,
    )

    updated = graph_composition.build_summarize_result_state(
        _make_state(status="scoring_complete"),
        {"html": "<html>ok</html>"},
        plan={
            "template_style": "compact",
            "is_compact": True,
            "article_count": 2,
            "chain_payload": {"articles": []},
        },
        generated_at=datetime(2026, 3, 12, 9, 0, tzinfo=timezone.utc),
        elapsed=1.7,
    )

    assert captured["normalize"][1]["template_style"] == "compact"
    assert captured["normalize"][1]["article_count"] == 2
    assert captured["success"][1] == "<html>ok</html>"
    assert updated["newsletter_topic"] == "AI Weekly"


@pytest.mark.unit
def test_build_compose_persist_plan_preserves_legacy_filename_inputs() -> None:
    plan = graph_composition.build_compose_persist_plan(
        _make_state(
            domain="AI Mobility",
            keywords=["AI", "Battery"],
            template_style="detailed",
        ),
        None,
    )

    assert plan == {
        "final_html": "<html><body>Newsletter generation failed</body></html>",
        "domain_slug": "AI_Mobility",
        "keywords_slug": "AI_Battery",
        "file_stem": "newsletter_detailed",
    }


@pytest.mark.unit
@pytest.mark.parametrize(
    ("keywords", "domain", "expected"),
    [
        (
            ["AI"],
            "Mobility",
            {"newsletter_topic": "Mobility", "requires_theme_extraction": False},
        ),
        (["AI"], None, {"newsletter_topic": "AI", "requires_theme_extraction": False}),
        (
            ["AI", "Battery"],
            None,
            {"newsletter_topic": "", "requires_theme_extraction": True},
        ),
    ],
)
def test_build_theme_resolution_plan_matches_legacy_branching(
    keywords, domain, expected
) -> None:
    assert graph_composition.build_theme_resolution_plan(keywords, domain) == expected


@pytest.mark.unit
def test_summarize_articles_node_delegates_invocation_plan_and_result_handoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = {"html": "<html>ok</html>"}
    captured = {}
    summary_plan = {
        "template_style": "compact",
        "is_compact": True,
        "article_count": 1,
        "chain_payload": {"articles": [{"title": "A"}]},
    }

    monkeypatch.setattr(
        graph_module,
        "build_summary_invocation_plan",
        lambda state, ranked_articles: summary_plan,
    )
    monkeypatch.setattr(
        graph_module,
        "get_newsletter_chain",
        lambda is_compact: fake_chain,
    )

    def _fake_result_state(state, result, *, plan, generated_at, elapsed):
        captured["result"] = result
        captured["plan"] = plan
        captured["generated_at"] = generated_at
        captured["elapsed"] = elapsed
        return _make_state(
            newsletter_html="<html>ok</html>",
            category_summaries={"sections": []},
            newsletter_topic="AI",
            status="summarizing_complete",
            step_times={"summarize": elapsed},
        )

    monkeypatch.setattr(
        graph_module, "build_summarize_result_state", _fake_result_state
    )

    updated = graph_module.summarize_articles_node(
        _make_state(
            ranked_articles=[{"title": "A"}],
            status="scoring_complete",
        )
    )

    assert fake_chain.invoke.call_args.args[0] == {"articles": [{"title": "A"}]}
    assert captured["plan"] == summary_plan
    assert updated["newsletter_html"] == "<html>ok</html>"


@pytest.mark.unit
def test_compose_newsletter_node_delegates_compose_persist_plan(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    captured = {}
    output_path = tmp_path / "newsletter.html"

    def _fake_compose_plan(state, newsletter_html):
        captured["persist_input"] = (state, newsletter_html)
        return {
            "final_html": "<html>persisted</html>",
            "domain_slug": "AI",
            "keywords_slug": "AI",
            "file_stem": "newsletter_compact",
        }

    def _fake_success(state, *, newsletter_html, elapsed):
        captured["success"] = (newsletter_html, elapsed)
        return _make_state(
            newsletter_html=newsletter_html,
            status="complete",
            step_times={"compose": elapsed},
        )

    monkeypatch.setattr(graph_module, "build_compose_persist_plan", _fake_compose_plan)
    monkeypatch.setattr(
        graph_module,
        "generate_unified_newsletter_filename",
        lambda domain, label, keywords, extension: str(output_path),
    )
    monkeypatch.setattr(graph_module, "build_compose_success_state", _fake_success)

    updated = graph_module.compose_newsletter_node(
        _make_state(
            newsletter_html="<html>input</html>",
            category_summaries={"sections": []},
            status="summarizing_complete",
        )
    )

    assert captured["persist_input"][1] == "<html>input</html>"
    assert output_path.read_text(encoding="utf-8") == "<html>persisted</html>"
    assert updated["newsletter_html"] == "<html>persisted</html>"


@pytest.mark.unit
def test_generate_newsletter_delegates_theme_resolution_plan(
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
        cost_tracking_module, "get_cost_summary", lambda: {"total_cost": 0.2}
    )
    monkeypatch.setattr(
        graph_module,
        "build_theme_resolution_plan",
        lambda keywords, domain: {
            "newsletter_topic": "Delegated Topic",
            "requires_theme_extraction": False,
        },
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

    result = graph_module.generate_newsletter(["AI", "Battery"], news_period_days=3)

    assert captured["initial_kwargs"]["newsletter_topic"] == "Delegated Topic"
    assert result == ("<html>delegated</html>", "success")
