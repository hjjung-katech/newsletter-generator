from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from newsletter.compose import (
    compose_compact_newsletter_html,
    compose_newsletter,
    compose_newsletter_html,
    extract_key_definitions_for_compact,
    process_compact_newsletter_data,
)
from newsletter_core.application.generation.compose import (
    compose_compact_newsletter_html as core_compose_compact_newsletter_html,
)
from newsletter_core.application.generation.compose import (
    compose_newsletter as core_compose_newsletter,
)
from newsletter_core.application.generation.compose import (
    compose_newsletter_html as core_compose_newsletter_html,
)
from newsletter_core.application.generation.compose import (
    extract_key_definitions_for_compact as core_extract_key_definitions_for_compact,
)
from newsletter_core.application.generation.compose import (
    process_compact_newsletter_data as core_process_compact_newsletter_data,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = str(PROJECT_ROOT / "templates")


@pytest.fixture
def sample_newsletter_data():
    return {
        "newsletter_topic": "AI 기술 동향",
        "domain": "AI",
        "generation_date": "2026-03-09",
        "generation_timestamp": "09:30:00",
        "search_keywords": ["AI", "머신러닝", "반도체"],
        "sections": [
            {
                "title": "AI 기술 발전",
                "summary_paragraphs": ["AI 기술이 빠르게 발전하고 있습니다."],
                "definitions": [
                    {
                        "term": "머신러닝",
                        "explanation": "데이터에서 패턴을 학습하는 기술입니다.",
                    }
                ],
                "news_links": [
                    {
                        "title": "AI 기술 혁신",
                        "url": "https://example.com/ai",
                        "source_and_date": "Tech News, 2026-03-08",
                    }
                ],
            },
            {
                "title": "반도체 시장",
                "summary_paragraphs": ["AI 수요가 반도체 시장을 이끌고 있습니다."],
                "definitions": [
                    {
                        "term": "NPU",
                        "explanation": "신경망 연산에 특화된 처리 장치입니다.",
                    }
                ],
                "news_links": [
                    {
                        "title": "AI 칩 수요 증가",
                        "url": "https://example.com/chips",
                        "source_and_date": "Market Watch, 2026-03-07",
                    }
                ],
            },
        ],
        "food_for_thought": {"message": "기술 변화 속도에 맞는 포트폴리오 재정렬이 필요합니다."},
        "recipient_greeting": "안녕하세요,",
        "introduction_message": "이번 주 주요 산업 동향을 정리했습니다.",
        "closing_message": "다음 주에 다시 찾아뵙겠습니다.",
        "editor_signature": "편집팀 드림",
        "company_name": "Tech Insights",
    }


def test_compose_shim_exposes_core_entrypoints():
    assert compose_newsletter is core_compose_newsletter
    assert compose_newsletter_html is core_compose_newsletter_html
    assert compose_compact_newsletter_html is core_compose_compact_newsletter_html


def test_compose_shim_exposes_helper_exports():
    assert (
        extract_key_definitions_for_compact is core_extract_key_definitions_for_compact
    )
    assert process_compact_newsletter_data is core_process_compact_newsletter_data


def test_detailed_wrapper_matches_default_compose_output(sample_newsletter_data):
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("GENERATION_DATE", "2026-03-09")
        monkeypatch.setenv("GENERATION_TIMESTAMP", "09:30:00")

        wrapper_html = compose_newsletter_html(
            deepcopy(sample_newsletter_data),
            TEMPLATE_DIR,
            "newsletter_template.html",
        )
        direct_html = compose_newsletter(
            deepcopy(sample_newsletter_data),
            TEMPLATE_DIR,
            "detailed",
        )

    assert wrapper_html == direct_html
    assert "검색 키워드: AI, 머신러닝, 반도체" in wrapper_html


def test_compact_wrapper_matches_default_compose_output(sample_newsletter_data):
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("GENERATION_DATE", "2026-03-09")
        monkeypatch.setenv("GENERATION_TIMESTAMP", "09:30:00")

        wrapper_html = compose_compact_newsletter_html(
            deepcopy(sample_newsletter_data),
            TEMPLATE_DIR,
            "newsletter_template_compact.html",
        )
        direct_html = compose_newsletter(
            deepcopy(sample_newsletter_data),
            TEMPLATE_DIR,
            "compact",
        )

    assert wrapper_html == direct_html
    assert "AI 기술 혁신" in wrapper_html


def test_compose_normalizes_list_input_into_detailed_html():
    articles = [
        {
            "title": "첫 번째 기사",
            "url": "https://example.com/first",
            "summary_text": "첫 번째 기사 요약입니다.",
            "source": "Example Source",
            "date": "2026-03-08",
        },
        {
            "title": "두 번째 기사",
            "url": "https://example.com/second",
            "content": "두 번째 기사 본문입니다.",
            "source": "Another Source",
            "date": "2026-03-07",
        },
    ]

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("GENERATION_DATE", "2026-03-09")
        monkeypatch.setenv("GENERATION_TIMESTAMP", "09:30:00")
        html = compose_newsletter(articles, TEMPLATE_DIR, "detailed")

    assert "첫 번째 기사" in html
    assert "https://example.com/first" in html
    assert "두 번째 기사" in html
    assert "2026-03-09" in html
    assert "09:30:00" in html


def test_email_compatible_preserves_explicit_title_and_keyword_rendering(
    sample_newsletter_data,
):
    data = {
        **sample_newsletter_data,
        "newsletter_title": "맞춤 제목",
        "template_style": "detailed",
    }

    html = compose_newsletter(data, TEMPLATE_DIR, "email_compatible")

    assert "맞춤 제목" in html
    assert "검색 키워드: AI, 머신러닝, 반도체" in html
    assert "안녕하세요," in html


def test_compose_derives_domain_title_when_explicit_title_is_missing(
    sample_newsletter_data,
):
    data = {
        key: value
        for key, value in sample_newsletter_data.items()
        if key != "newsletter_title"
    }

    html = compose_newsletter(data, TEMPLATE_DIR, "detailed")

    assert "AI 주간 산업동향 뉴스 클리핑" in html
