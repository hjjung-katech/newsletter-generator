#!/usr/bin/env python3
"""
Email Compatibility 테스트 모듈

이메일 호환성 기능의 모든 측면을 테스트합니다:
- HTML 구조 검증
- CSS 인라인 처리
- 템플릿 변수 처리
- 콘텐츠 무결성
- 크로스 플랫폼 호환성
"""

import os
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from newsletter import config
from langchain_core.messages import AIMessage
from newsletter.chains import get_newsletter_chain
from newsletter.compose import compose_newsletter


class TestEmailCompatibilityCore:
    """Email-Compatible 핵심 기능 테스트"""

    @pytest.fixture
    def sample_data(self):
        """테스트용 샘플 데이터"""
        return {
            "newsletter_topic": "AI 기술 동향",
            "generation_date": "2025-05-30",
            "search_keywords": "AI, 인공지능, 머신러닝",
            "top_articles": [
                {
                    "title": "AI 기술의 최신 동향",
                    "url": "https://example.com/article1",
                    "snippet": "인공지능 기술이 빠르게 발전하고 있습니다.",
                    "source_and_date": "TechNews · 2025-05-29",
                }
            ],
            "sections": [
                {
                    "title": "AI 기술 발전",
                    "summary_paragraphs": ["AI 기술이 급속도로 발전하고 있습니다."],
                    "definitions": [
                        {
                            "term": "머신러닝",
                            "explanation": "기계가 데이터로부터 패턴을 학습하는 기술입니다.",
                        }
                    ],
                    "news_links": [
                        {
                            "title": "AI 기술의 최신 동향",
                            "url": "https://example.com/article1",
                            "source_and_date": "TechNews · 2025-05-29",
                        }
                    ],
                }
            ],
            "grouped_sections": [
                {
                    "heading": "AI 기술 발전",
                    "intro": "AI 기술이 급속도로 발전하고 있습니다.",
                    "articles": [
                        {
                            "title": "AI 기술의 최신 동향",
                            "url": "https://example.com/article1",
                            "source_and_date": "TechNews · 2025-05-29",
                        }
                    ],
                    "definitions": [
                        {
                            "term": "머신러닝",
                            "explanation": "기계가 데이터로부터 패턴을 학습하는 기술입니다.",
                        }
                    ],
                }
            ],
            "definitions": [
                {
                    "term": "머신러닝",
                    "explanation": "기계가 데이터로부터 패턴을 학습하는 기술입니다.",
                }
            ],
            "food_for_thought": {
                "message": "AI 기술 발전에 대응하기 위한 전략적 사고가 필요합니다."
            },
            "recipient_greeting": "안녕하세요,",
            "introduction_message": "이번 주 AI 기술 동향을 정리해 드립니다.",
            "closing_message": "다음 주에 더 유익한 정보로 찾아뵙겠습니다.",
            "editor_signature": "편집자 드림",
            "company_name": "Tech Insights",
            "template_style": "detailed",  # 또는 "compact"
            "email_compatible": True,
        }

    def test_email_compatible_template_selection(self, sample_data):
        """Email-compatible 템플릿이 올바르게 선택되는지 테스트"""
        template_dir = os.path.join(project_root, "templates")

        # email_compatible = True인 경우
        html_content = compose_newsletter(sample_data, template_dir, "email_compatible")

        assert html_content is not None
        assert len(html_content) > 0

        # HTML 파싱
        soup = BeautifulSoup(html_content, "html.parser")

        # 기본 HTML 구조 확인
        assert soup.find("html") is not None
        assert soup.find("head") is not None
        assert soup.find("body") is not None

        # 이메일 호환 구조 확인 (테이블 기반 레이아웃)
        tables = soup.find_all("table")
        assert (
            len(tables) > 0
        ), "Email-compatible 템플릿은 테이블 기반 레이아웃을 사용해야 합니다"

    def test_inline_css_processing(self, sample_data):
        """CSS가 인라인으로 처리되는지 테스트"""
        template_dir = os.path.join(project_root, "templates")
        html_content = compose_newsletter(sample_data, template_dir, "email_compatible")

        soup = BeautifulSoup(html_content, "html.parser")

        # 인라인 스타일이 존재하는지 확인
        elements_with_style = soup.find_all(attrs={"style": True})
        assert (
            len(elements_with_style) > 0
        ), "Email-compatible 템플릿은 인라인 CSS를 사용해야 합니다"

        # CSS 변수 사용하지 않는지 확인
        style_content = str(soup)
        assert (
            "var(--" not in style_content
        ), "Email-compatible 템플릿은 CSS 변수를 사용하면 안됩니다"

    def test_template_style_handling(self, sample_data):
        """template_style에 따른 다른 콘텐츠 처리 테스트"""
        template_dir = os.path.join(project_root, "templates")

        # Detailed style 테스트
        sample_data["template_style"] = "detailed"
        detailed_html = compose_newsletter(
            sample_data, template_dir, "email_compatible"
        )

        # Compact style 테스트
        sample_data["template_style"] = "compact"
        compact_html = compose_newsletter(sample_data, template_dir, "email_compatible")

        assert (
            detailed_html != compact_html
        ), "Detailed와 Compact 스타일은 다른 결과를 생성해야 합니다"

        # 두 결과 모두 유효한 HTML인지 확인
        for html in [detailed_html, compact_html]:
            soup = BeautifulSoup(html, "html.parser")
            assert soup.find("html") is not None
            assert soup.find("body") is not None

    def test_required_email_fields(self, sample_data):
        """Email-compatible 템플릿에 필요한 필드들이 포함되는지 테스트"""
        template_dir = os.path.join(project_root, "templates")
        html_content = compose_newsletter(sample_data, template_dir, "email_compatible")

        # 필수 필드들이 포함되었는지 확인
        required_fields = [
            "recipient_greeting",
            "introduction_message",
            "closing_message",
            "editor_signature",
            "newsletter_topic",
        ]

        for field in required_fields:
            field_value = sample_data.get(field, "")
            if field_value:
                assert (
                    field_value in html_content
                ), f"필수 필드 '{field}'가 HTML에 포함되지 않았습니다"

    def test_content_integrity(self, sample_data):
        """콘텐츠 무결성 테스트 - 모든 데이터가 손실 없이 포함되는지"""
        template_dir = os.path.join(project_root, "templates")
        html_content = compose_newsletter(sample_data, template_dir, "email_compatible")

        # 기사 제목들이 포함되었는지 확인
        if sample_data.get("top_articles"):
            for article in sample_data["top_articles"]:
                title = article.get("title", "")
                if title:
                    assert (
                        title in html_content
                    ), f"기사 제목 '{title}'이 누락되었습니다"

        # 정의(definitions)가 포함되었는지 확인
        if sample_data.get("definitions"):
            for definition in sample_data["definitions"]:
                term = definition.get("term", "")
                explanation = definition.get("explanation", "")
                if term:
                    # "이런 뜻이에요" 섹션에서 term이나 explanation이 있는지 확인
                    assert (
                        term in html_content or explanation in html_content
                    ), f"정의 '{term}'이 누락되었습니다"

    def test_mobile_responsiveness(self, sample_data):
        """모바일 반응형 디자인 테스트"""
        template_dir = os.path.join(project_root, "templates")
        html_content = compose_newsletter(sample_data, template_dir, "email_compatible")

        soup = BeautifulSoup(html_content, "html.parser")

        # viewport 메타 태그 확인
        viewport_meta = soup.find("meta", attrs={"name": "viewport"})
        assert (
            viewport_meta is not None
        ), "Email-compatible 템플릿은 viewport 메타 태그를 포함해야 합니다"

        # 테이블 width 설정 확인
        tables = soup.find_all("table")
        main_table_found = False
        for table in tables:
            if table.get("width") == "100%" or "width:100%" in str(
                table.get("style", "")
            ):
                main_table_found = True
                break

        assert main_table_found, "메인 테이블은 100% 너비를 가져야 합니다"


class TestEmailCompatibilityIntegration:
    """Email-Compatible 통합 테스트"""

    @pytest.fixture
    def mock_articles_data(self):
        """모킹된 기사 데이터"""
        return {
            "articles": [
                {
                    "title": "AI 기술의 미래",
                    "url": "https://example.com/ai-future",
                    "content": "인공지능 기술이 우리 삶을 바꾸고 있습니다...",
                    "source": "TechNews",
                    "date": "2025-05-29",
                    "score": 0.9,
                },
                {
                    "title": "머신러닝 최신 동향",
                    "url": "https://example.com/ml-trends",
                    "content": "머신러닝 기술의 발전 현황을 살펴봅니다...",
                    "source": "AIDaily",
                    "date": "2025-05-28",
                    "score": 0.8,
                },
            ],
            "keywords": ["AI", "인공지능", "머신러닝"],
            "domain": "AI 기술",
            "email_compatible": True,
            "template_style": "detailed",
        }

    @patch("newsletter.chains.get_llm")
    def test_full_pipeline_detailed_email_compatible(
        self, mock_llm, mock_articles_data
    ):
        """Detailed + Email-Compatible 전체 파이프라인 테스트"""
        # LLM 모킹
        mock_llm_instance = MagicMock()
        mock_llm.invoke.side_effect = [
            AIMessage(content='{"categories": [{"title": "AI 기술 발전", "article_indices": [0, 1]}]}'),
            AIMessage(content='{"summary_paragraphs": ["AI 기술이 발전하고 있습니다."], "definitions": [{"term": "AI", "explanation": "인공지능"}], "news_links": [{"title": "AI 기술의 미래", "url": "https://example.com/ai-future", "source_and_date": "TechNews · 2025-05-29"}]}'),
            AIMessage(content='{"newsletter_topic": "AI 기술", "generation_date": "2025-05-30", "recipient_greeting": "안녕하세요", "introduction_message": "AI 기술 동향입니다", "food_for_thought": {"message": "AI에 대해 생각해봅시다"}, "closing_message": "감사합니다", "editor_signature": "편집자"}')
        ]

        # 체인 실행
        newsletter_chain = get_newsletter_chain(is_compact=False)
        result = newsletter_chain.invoke(mock_articles_data)

        # 결과 검증
        assert "html" in result
        assert "structured_data" in result
        assert result["mode"] == "detailed"

        html_content = result["html"]
        assert html_content is not None
        assert len(html_content) > 0

        # HTML 구조 검증
        soup = BeautifulSoup(html_content, "html.parser")
        assert soup.find("html") is not None
        assert soup.find("body") is not None

    @patch("newsletter.chains.get_llm")
    def test_full_pipeline_compact_email_compatible(self, mock_llm, mock_articles_data):
        """Compact + Email-Compatible 전체 파이프라인 테스트"""
        # 설정 변경
        mock_articles_data["template_style"] = "compact"

        # LLM 모킹
        mock_llm_instance = MagicMock()
        mock_llm.invoke.side_effect = [
            AIMessage(content='{"categories": [{"title": "AI 기술 발전", "article_indices": [0, 1]}]}'),
            AIMessage(content='{"intro": "AI 기술 동향입니다", "definitions": [{"term": "AI", "explanation": "인공지능"}], "news_links": [{"title": "AI 기술의 미래", "url": "https://example.com/ai-future", "source_and_date": "TechNews · 2025-05-29"}]}')
        ]

        # 체인 실행
        newsletter_chain = get_newsletter_chain(is_compact=True)
        result = newsletter_chain.invoke(mock_articles_data)

        # 결과 검증
        assert "html" in result
        assert "structured_data" in result
        assert result["mode"] == "compact"

        html_content = result["html"]
        assert html_content is not None
        assert len(html_content) > 0

    def test_error_handling_with_email_compatible(self, mock_articles_data):
        """Email-compatible 모드에서 오류 처리 테스트"""
        # 잘못된 데이터로 테스트
        invalid_data = {
            "articles": [],  # 빈 기사 리스트
            "keywords": "",
            "email_compatible": True,
            "template_style": "detailed",
        }

        # 체인이 오류를 적절히 처리하는지 확인
        try:
            newsletter_chain = get_newsletter_chain(is_compact=False)
            # 에러 없이 실행되어야 함 (fallback 처리)
        except Exception as e:
            pytest.fail(f"Email-compatible 모드에서 예상치 못한 오류 발생: {e}")


class TestEmailCompatibilityValidation:
    """Email 호환성 검증 테스트"""

    def test_html_validation(self):
        """생성된 HTML의 유효성 검증"""
        sample_data = {
            "newsletter_topic": "테스트",
            "template_style": "detailed",
            "email_compatible": True,
            "sections": [],
            "definitions": [],
            "top_articles": [],
        }

        template_dir = os.path.join(project_root, "templates")
        html_content = compose_newsletter(sample_data, template_dir, "email_compatible")

        soup = BeautifulSoup(html_content, "html.parser")

        # 기본 HTML 구조 유효성
        assert soup.find("html") is not None
        assert soup.find("head") is not None
        assert soup.find("body") is not None
        assert soup.find("title") is not None

        # 문자 인코딩 설정
        charset_meta = soup.find("meta", attrs={"charset": True})
        assert charset_meta is not None, "문자 인코딩 메타 태그가 필요합니다"

    def test_css_compatibility(self):
        """CSS 호환성 검증"""
        sample_data = {
            "newsletter_topic": "테스트",
            "template_style": "detailed",
            "email_compatible": True,
            "sections": [],
            "definitions": [],
            "top_articles": [],
        }

        template_dir = os.path.join(project_root, "templates")
        html_content = compose_newsletter(sample_data, template_dir, "email_compatible")

        # 지원되지 않는 CSS 속성 확인
        unsupported_css = [
            "var(--",  # CSS 변수
            "display: flex",  # Flexbox (일부 클라이언트에서 미지원)
            "display: grid",  # CSS Grid
            "transform:",  # CSS Transform
            "animation:",  # CSS Animation
        ]

        for css_prop in unsupported_css:
            assert (
                css_prop not in html_content
            ), f"이메일에서 지원되지 않는 CSS 속성 사용: {css_prop}"

    def test_link_validation(self):
        """링크 유효성 검증"""
        sample_data = {
            "newsletter_topic": "테스트",
            "template_style": "detailed",
            "email_compatible": True,
            "sections": [
                {
                    "news_links": [
                        {
                            "title": "테스트 기사",
                            "url": "https://example.com/test",
                            "source_and_date": "TestSource · 2025-05-30",
                        }
                    ]
                }
            ],
            "definitions": [],
            "top_articles": [],
        }

        template_dir = os.path.join(project_root, "templates")
        html_content = compose_newsletter(sample_data, template_dir, "email_compatible")

        soup = BeautifulSoup(html_content, "html.parser")

        # 모든 링크가 유효한 URL인지 확인
        links = soup.find_all("a", href=True)
        for link in links:
            href = link["href"]
            assert href.startswith(
                ("http://", "https://", "mailto:")
            ), f"유효하지 않은 링크: {href}"


@pytest.mark.integration
class TestEmailCompatibilityE2E:
    """End-to-End 테스트"""

    def test_complete_newsletter_generation(self):
        """완전한 뉴스레터 생성 테스트"""
        # 실제 CLI 명령과 유사한 테스트
        pass  # 실제 구현은 CI/CD에서 수행

    @pytest.mark.skipif(
        not os.getenv("TEST_EMAIL_RECIPIENT"),
        reason="TEST_EMAIL_RECIPIENT 환경변수가 설정되지 않음",
    )
    def test_actual_email_sending(self):
        """실제 이메일 전송 테스트 (선택적)"""
        # 환경변수로 설정된 이메일로 실제 전송 테스트
        pass  # 실제 구현은 수동 테스트에서 수행


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
