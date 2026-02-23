"""Contract tests for newsletter.chains orchestration behavior."""

from __future__ import annotations

from typing import Any

import pytest

from newsletter import chains, chains_llm_utils, chains_prompts

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


class _StubRunnable:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.calls: list[Any] = []

    def invoke(self, payload: Any) -> Any:
        self.calls.append(payload)
        return self.result


def test_public_re_exports_remain_stable() -> None:
    assert chains.COMPOSITION_PROMPT == chains_prompts.COMPOSITION_PROMPT
    assert chains.HTML_TEMPLATE == chains_prompts.HTML_TEMPLATE
    assert chains.SYSTEM_PROMPT == chains_prompts.SYSTEM_PROMPT
    assert chains.load_html_template is chains_prompts.load_html_template
    assert chains.get_llm is chains_llm_utils.get_llm


def test_get_newsletter_chain_compact_skips_detailed_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    categories_data = {"categories": [{"name": "industry"}]}
    sections_data = {"sections": [{"category": "industry"}]}
    compact_result = {"mode": "compact", "html": "<html>compact</html>"}

    categorization_chain = _StubRunnable(categories_data)
    summarization_chain = _StubRunnable(sections_data)

    monkeypatch.setattr(
        chains,
        "create_categorization_chain",
        lambda is_compact=False: categorization_chain,
    )
    monkeypatch.setattr(
        chains,
        "create_summarization_chain",
        lambda is_compact=False: summarization_chain,
    )
    monkeypatch.setattr(
        chains,
        "create_composition_chain",
        lambda: (_ for _ in ()).throw(
            AssertionError("compact flow must not build composition chain")
        ),
    )
    monkeypatch.setattr(
        chains,
        "create_rendering_chain",
        lambda: (_ for _ in ()).throw(
            AssertionError("compact flow must not build rendering chain")
        ),
    )
    monkeypatch.setattr(
        chains,
        "build_compact_newsletter_result",
        lambda data, sections: compact_result,
    )

    payload = {"articles": [{"title": "A"}], "keywords": "AI"}
    result = chains.get_newsletter_chain(is_compact=True).invoke(payload)

    assert result == compact_result
    assert categorization_chain.calls == [payload]
    assert summarization_chain.calls == [
        {"categories_data": categories_data, "articles_data": payload}
    ]


def test_get_newsletter_chain_detailed_runs_composition_and_rendering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    categories_data = {"categories": [{"name": "mobility"}]}
    sections_data = {"sections": [{"category": "mobility"}]}
    composition_data = {"title": "Detailed Contract"}
    rendering_output = (
        "<html><body><h1>Detailed Contract</h1></body></html>",
        {"title": "Detailed Contract"},
    )

    categorization_chain = _StubRunnable(categories_data)
    summarization_chain = _StubRunnable(sections_data)
    composition_chain = _StubRunnable(composition_data)
    rendering_chain = _StubRunnable(rendering_output)

    monkeypatch.setattr(
        chains,
        "create_categorization_chain",
        lambda is_compact=False: categorization_chain,
    )
    monkeypatch.setattr(
        chains,
        "create_summarization_chain",
        lambda is_compact=False: summarization_chain,
    )
    monkeypatch.setattr(chains, "create_composition_chain", lambda: composition_chain)
    monkeypatch.setattr(chains, "create_rendering_chain", lambda: rendering_chain)

    payload = {
        "articles": [{"title": "A"}],
        "keywords": "AI",
        "domain": "example.com",
        "ranked_articles": [{"title": "A"}],
        "processed_articles": [{"title": "A"}],
        "email_compatible": True,
        "template_style": "detailed",
    }
    result = chains.get_newsletter_chain(is_compact=False).invoke(payload)

    assert result["mode"] == "detailed"
    assert result["html"] == rendering_output[0]
    assert result["structured_data"] == rendering_output[1]
    assert result["sections"] == sections_data["sections"]
    assert composition_chain.calls == [
        {"sections_data": sections_data, "articles_data": payload}
    ]
    assert rendering_chain.calls == [
        {
            "composition": composition_data,
            "sections_data": sections_data,
            "keywords": "AI",
            "domain": "example.com",
            "ranked_articles": payload["ranked_articles"],
            "processed_articles": payload["processed_articles"],
            "email_compatible": True,
            "template_style": "detailed",
        }
    ]


def test_get_newsletter_chain_no_articles_uses_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    categorization_chain = _StubRunnable({"categories": []})
    summarization_chain = _StubRunnable({"sections": []})
    composition_chain = _StubRunnable({"title": "unused"})
    rendering_chain = _StubRunnable(("<html>unused</html>", {"title": "unused"}))

    monkeypatch.setattr(
        chains,
        "create_categorization_chain",
        lambda is_compact=False: categorization_chain,
    )
    monkeypatch.setattr(
        chains,
        "create_summarization_chain",
        lambda is_compact=False: summarization_chain,
    )
    monkeypatch.setattr(chains, "create_composition_chain", lambda: composition_chain)
    monkeypatch.setattr(chains, "create_rendering_chain", lambda: rendering_chain)
    monkeypatch.setattr(
        chains,
        "handle_no_articles_scenario",
        lambda data, is_compact: {"mode": "detailed", "reason": "no-articles"},
    )

    result = chains.get_newsletter_chain(is_compact=False).invoke(
        {"articles": [], "keywords": "AI"}
    )

    assert result == {"mode": "detailed", "reason": "no-articles"}
    assert categorization_chain.calls == []
    assert summarization_chain.calls == []
    assert composition_chain.calls == []
    assert rendering_chain.calls == []


def test_get_newsletter_chain_requires_articles_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        chains,
        "create_categorization_chain",
        lambda is_compact=False: _StubRunnable({"categories": []}),
    )
    monkeypatch.setattr(
        chains,
        "create_summarization_chain",
        lambda is_compact=False: _StubRunnable({"sections": []}),
    )
    monkeypatch.setattr(chains, "create_composition_chain", lambda: _StubRunnable({}))
    monkeypatch.setattr(
        chains,
        "create_rendering_chain",
        lambda: _StubRunnable(("<html></html>", {})),
    )

    with pytest.raises(ValueError, match="articles"):
        chains.get_newsletter_chain(is_compact=False).invoke({"keywords": "AI"})
