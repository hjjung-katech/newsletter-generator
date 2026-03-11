from __future__ import annotations

import newsletter.tools as tools_module
from newsletter_core.application.tools_support import (
    SearchRequest,
    extract_common_theme_fallback,
    parse_generated_keywords,
    parse_serper_response,
    resolve_filename_theme,
    resolve_search_request,
    sanitize_filename,
)


def test_resolve_search_request_caps_results_and_preserves_split_order() -> None:
    request = resolve_search_request("AI, 머신러닝, ", 25)

    assert request == SearchRequest(keywords=("AI", "머신러닝", ""), num_results=20)


def test_parse_serper_response_combines_news_and_topstories() -> None:
    parsed = parse_serper_response(
        {
            "news": [
                {
                    "title": "AI Title",
                    "link": "https://example.com/ai",
                    "snippet": "AI snippet",
                    "source": "AI Source",
                    "date": "2026-03-11",
                }
            ],
            "topStories": [
                {
                    "title": "Top Story",
                    "link": "https://example.com/top",
                    "description": "Top description",
                    "source": "Top Source",
                    "publishedAt": "2026-03-10",
                }
            ],
            "organic": [
                {
                    "title": "Organic Fallback",
                    "link": "https://example.com/organic",
                }
            ],
        },
        num_results=5,
    )

    assert parsed.container_names == ("news", "topStories")
    assert parsed.container_count == 2
    assert parsed.articles == [
        {
            "title": "AI Title",
            "url": "https://example.com/ai",
            "link": "https://example.com/ai",
            "snippet": "AI snippet",
            "source": "AI Source",
            "date": "2026-03-11",
        },
        {
            "title": "Top Story",
            "url": "https://example.com/top",
            "link": "https://example.com/top",
            "snippet": "Top description",
            "source": "Top Source",
            "date": "2026-03-10",
        },
    ]


def test_parse_serper_response_uses_organic_when_primary_containers_are_empty() -> None:
    parsed = parse_serper_response(
        {
            "news": [],
            "organic": [
                {
                    "title": "Organic Only",
                    "link": "https://example.com/organic",
                }
            ],
        },
        num_results=5,
    )

    assert parsed.container_names == ("news", "organic")
    assert parsed.container_count == 1
    assert parsed.articles[0]["title"] == "Organic Only"


def test_parse_generated_keywords_normalizes_lines_and_inline_markup() -> None:
    parsed = parse_generated_keywords(
        """
        1. **AI 반도체**
        2. 생성형 AI (Generative AI)

        """,
        count=2,
    )

    assert parsed == ["AI 반도체", "생성형 AI"]


def test_extract_common_theme_fallback_and_sanitize_filename_are_pure() -> None:
    assert extract_common_theme_fallback("AI, 머신러닝, 딥러닝") == "AI, 머신러닝, 딥러닝"
    assert sanitize_filename("AI(인공지능), 산업. 동향") == "AI인공지능_산업_동향"


def test_resolve_filename_theme_uses_extractor_only_for_multi_keyword_inputs() -> None:
    calls: list[object] = []

    def fake_theme_extractor(value: object) -> str:
        calls.append(value)
        return "추출된 테마"

    assert (
        resolve_filename_theme(["AI"], None, theme_extractor=fake_theme_extractor)
        == "AI"
    )
    assert (
        resolve_filename_theme(
            ["AI", "반도체"], None, theme_extractor=fake_theme_extractor
        )
        == "추출된 테마"
    )
    assert (
        resolve_filename_theme("AI, 반도체", None, theme_extractor=fake_theme_extractor)
        == "추출된 테마"
    )
    assert (
        resolve_filename_theme(
            ["AI", "반도체"], "직접도메인", theme_extractor=fake_theme_extractor
        )
        == "직접도메인"
    )
    assert calls == [["AI", "반도체"], "AI, 반도체"]


def test_legacy_get_filename_safe_theme_delegates_to_core_helpers(
    monkeypatch,
) -> None:
    calls: dict[str, object] = {}

    def fake_resolve_filename_theme(
        keywords: object,
        domain: str | None,
        *,
        theme_extractor,
    ) -> str:
        calls["keywords"] = keywords
        calls["domain"] = domain
        calls["theme_extractor"] = theme_extractor
        return "반도체 기술"

    def fake_sanitize_filename(value: str) -> str:
        calls["sanitized_input"] = value
        return "반도체_기술"

    monkeypatch.setattr(
        tools_module, "resolve_filename_theme", fake_resolve_filename_theme
    )
    monkeypatch.setattr(tools_module, "sanitize_filename", fake_sanitize_filename)

    result = tools_module.get_filename_safe_theme(["AI", "반도체"])

    assert result == "반도체_기술"
    assert calls["keywords"] == ["AI", "반도체"]
    assert calls["domain"] is None
    assert calls["theme_extractor"] is tools_module.extract_common_theme_from_keywords
    assert calls["sanitized_input"] == "반도체 기술"
