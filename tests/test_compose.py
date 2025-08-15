# -*- coding: utf-8 -*-
"""
뉴스레터 생성(Composition) 기능 통합 테스트
- 상세(Detailed) 및 요약(Compact) 뉴스레터 생성 로직 검증
- 템플릿 렌더링 및 데이터 처리 검증
- 관련 유틸리티 함수(테마, 정의 추출 등) 검증
"""

import os
import sys
from unittest.mock import patch
import pytest
from newsletter.compose import (
    compose_newsletter_html,
    compose_compact_newsletter_html,
    extract_key_definitions_for_compact
)
from newsletter.tools import (
    extract_common_theme_fallback,
    get_filename_safe_theme
)

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# --- 테스트 데이터 및 설정 ---

@pytest.fixture
def detailed_style_data():
    """상세 스타일 뉴스레터 테스트를 위한 데이터"""
    return [
        {
            "title": "Test Article 1", "url": "http://example.com/1",
            "summary_text": "Summary 1", "source": "Test Source 1", "date": "2025-01-01",
        },
        {
            "title": "Test Article 2", "url": "http://example.com/2",
            "summary_text": "Summary 2", "source": "Test Source 2", "date": "2025-01-02",
        },
    ]

@pytest.fixture
def compact_style_data():
    """요약 스타일 뉴스레터 테스트를 위한 데이터"""
    return {
        "newsletter_title": "자율주행 주간 산업 동향 뉴스 클리핑",
        "tagline": "이번 주, 주요 산업 동향을 미리 만나보세요.",
        "generation_date": "2025-05-23",
        "top_articles": [{
            "title": "테스트 기사", "url": "https://example.com/test",
            "snippet": "테스트 내용입니다.", "source_and_date": "TestSource · 2025-05-23",
        }],
        "grouped_sections": [{
            "heading": "📊 테스트 섹션", "intro": "테스트 섹션 설명입니다.", "articles": [],
        }],
        "definitions": [{"term": "테스트용어", "explanation": "테스트를 위한 용어입니다."}],
        "food_for_thought": "테스트 질문입니다.",
        "company_name": "Test Company",
    }

@pytest.fixture
def template_dir():
    """템플릿 디렉토리 경로를 제공하는 Fixture"""
    return os.path.join(os.path.dirname(__file__), "..", "templates")

# --- 상세 스타일(Detailed) 뉴스레터 테스트 ---

def test_compose_detailed_newsletter_success(detailed_style_data, template_dir):
    """상세 스타일 뉴스레터가 성공적으로 생성되는지 테스트"""
    with patch.dict(os.environ, {"GENERATION_DATE": "2025-05-10", "GENERATION_TIMESTAMP": "12:34:56"}):
        html_content = compose_newsletter_html(detailed_style_data, template_dir, "newsletter_template.html")

    assert "Test Article 1" in html_content
    assert "http://example.com/1" in html_content
    assert "Test Source 1" in html_content
    assert "Summary 1" in html_content or "Summary 2" in html_content
    assert "2025-05-10" in html_content
    assert "12:34:56" in html_content

def test_compose_detailed_newsletter_empty_summaries(template_dir):
    """요약 데이터가 비어있을 때 상세 스타일 뉴스레터 생성 테스트"""
    with patch.dict(os.environ, {"GENERATION_DATE": "2025-05-10", "GENERATION_TIMESTAMP": "12:34:56"}):
        html_content = compose_newsletter_html([], template_dir, "newsletter_template.html")
    assert "2025-05-10" in html_content
    assert "12:34:56" in html_content
    assert "참고 뉴스 링크" not in html_content

def test_compose_detailed_template_not_found(detailed_style_data, template_dir):
    """상세 스타일 템플릿 파일이 없을 때 예외 발생 테스트"""
    with pytest.raises(Exception):
        compose_newsletter_html(detailed_style_data, template_dir, "non_existent_template.html")

# --- 요약 스타일(Compact) 뉴스레터 테스트 ---

def test_compose_compact_template_rendering(compact_style_data, template_dir):
    """요약 스타일 템플릿이 정상적으로 렌더링되는지 테스트"""
    html = compose_compact_newsletter_html(compact_style_data, template_dir, "newsletter_template_compact.html")

    assert html is not None and len(html) > 0
    assert "자율주행 주간 산업 동향 뉴스 클리핑" in html
    assert "📖 이런 뜻이에요" in html
    assert "테스트용어" in html
    assert "테스트를 위한 용어입니다" in html
    assert "이번 주, 주요 산업 동향을 미리 만나보세요" in html

def test_compact_definitions_extraction():
    """'이런 뜻이에요' 용어 정의 추출 기능 테스트"""
    test_sections = [
        {"title": "자율주행 기술 동향", "definitions": [{"term": "자율주행", "explanation": "운전자 개입 없이 스스로 주행하는 기술"}]},
        {"title": "로보택시 상용화", "definitions": [{"term": "로보택시", "explanation": "자율주행 기술 기반 택시 서비스"}]},
    ]
    definitions = extract_key_definitions_for_compact(test_sections)
    assert len(definitions) > 0
    assert len(definitions) <= 3
    for definition in definitions:
        assert "term" in definition and "explanation" in definition

def test_compact_definitions_extraction_edge_cases():
    """'이런 뜻이에요' 용어 정의 추출 엣지 케이스 테스트"""
    assert extract_key_definitions_for_compact([]) == []
    assert extract_key_definitions_for_compact([{"title": "Test"}]) == []
    assert extract_key_definitions_for_compact([{"title": "Test", "definitions": []}]) == []

# --- 테마 및 파일명 관련 유틸리티 테스트 ---

def test_extract_common_theme_fallback():
    """키워드 기반 테마 생성 폴백(Fallback) 함수 테스트"""
    assert extract_common_theme_fallback(["AI 기술"]) == "AI 기술"
    assert extract_common_theme_fallback([]) == ""
    assert extract_common_theme_fallback(["AI", "머신러닝", "딥러닝"]) == "AI, 머신러닝, 딥러닝"
    assert extract_common_theme_fallback(["AI", "머신러닝", "딥러닝", "자연어처리"]) == "AI 외 3개 분야"
    assert extract_common_theme_fallback("AI, 머신러닝, 딥러닝") == "AI, 머신러닝, 딥러닝"

@patch("newsletter.tools.extract_common_theme_from_keywords", return_value="인공지능 기술")
def test_get_filename_safe_theme(mock_extract):
    """파일 이름에 안전한 테마 문자열 생성 함수 테스트"""
    assert get_filename_safe_theme(["AI", "머신러닝"], domain="인공지능") == "인공지능"
    mock_extract.assert_not_called()

    assert get_filename_safe_theme(["AI 기술"]) == "AI_기술"
    mock_extract.assert_not_called()

    assert get_filename_safe_theme(["AI", "머신러닝"]) == "인공지능_기술"
    mock_extract.assert_called_once()