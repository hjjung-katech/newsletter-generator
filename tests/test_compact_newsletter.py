#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compact 뉴스레터 단위 테스트
외부 API를 사용하지 않는 순수 단위 테스트들
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from newsletter.chains import get_newsletter_chain
from newsletter.compose import (
    compose_compact_newsletter_html,
    extract_key_definitions_for_compact,
)


class TestCompactNewsletterUnit:
    """Compact 뉴스레터 단위 테스트 클래스 (API 미사용)"""

    def setup_method(self):
        """각 테스트 메서드 실행 전 설정"""
        self.test_articles = [
            {
                "title": "테슬라 로보택시 출시 발표",
                "url": "https://example.com/tesla-robotaxi",
                "snippet": "테슬라가 완전자율주행 로보택시 서비스를 6월 출시한다고 발표했습니다.",
                "source": "TechNews",
                "date": "2025-05-23",
                "content": "테슬라 CEO 일론 머스크가 완전자율주행 기술을 탑재한 로보택시 서비스를 올해 6월부터 시범 운영한다고 발표했습니다.",
            },
            {
                "title": "자율주행 규제 완화 동향",
                "url": "https://example.com/autonomous-regulation",
                "snippet": "미국과 중국에서 자율주행 관련 규제가 완화되고 있습니다.",
                "source": "AutoTech",
                "date": "2025-05-22",
                "content": "미국과 중국 정부가 자율주행 기술 상용화를 위한 규제 완화 정책을 발표했습니다.",
            },
            {
                "title": "현대차 자율주행 전략 변화",
                "url": "https://example.com/hyundai-strategy",
                "snippet": "현대차가 자율주행 기술 개발 전략을 수정했습니다.",
                "source": "CarNews",
                "date": "2025-05-21",
                "content": "현대차그룹이 자율주행 기술 개발 방향을 기존 레벨 4에서 레벨 3 중심으로 전환했습니다.",
            },
        ]

        self.test_data = {
            "articles": self.test_articles,
            "keywords": ["자율주행"],
        }

    @pytest.mark.unit
    def test_compact_chain_creation(self):
        """Compact 체인 생성 테스트 (API 호출 없음)"""
        try:
            # Compact 체인 생성만 테스트
            chain = get_newsletter_chain(is_compact=True)
            assert chain is not None, "Compact 체인 생성 실패"

            # 체인의 기본 속성 확인
            assert hasattr(chain, "invoke"), "체인에 invoke 메서드가 없습니다"

            print("✅ Compact 체인 생성 테스트 통과!")

        except Exception as e:
            pytest.fail(f"Compact 체인 생성 테스트 실패: {e}")

    @pytest.mark.unit
    def test_compact_definitions_generation(self):
        """Definitions 생성 기능 단위 테스트"""
        # 테스트용 섹션 데이터
        test_sections = [
            {
                "title": "자율주행 기술 동향",
                "definitions": [
                    {
                        "term": "자율주행",
                        "explanation": "운전자 개입 없이 스스로 주행하는 기술",
                    },
                    {"term": "레벨4", "explanation": "완전 자율주행 수준"},
                ],
            },
            {
                "title": "로보택시 상용화",
                "definitions": [
                    {
                        "term": "로보택시",
                        "explanation": "자율주행 기술 기반 택시 서비스",
                    }
                ],
            },
        ]

        definitions = extract_key_definitions_for_compact(test_sections)

        # 검증
        assert len(definitions) > 0, "정의가 생성되지 않았습니다"
        assert len(definitions) <= 3, "정의가 3개를 초과했습니다"

        for definition in definitions:
            assert "term" in definition, "용어 필드가 누락되었습니다"
            assert "explanation" in definition, "설명 필드가 누락되었습니다"
            assert len(definition["term"]) > 0, "용어가 비어있습니다"
            assert len(definition["explanation"]) > 0, "설명이 비어있습니다"

        print(f"✅ Definitions 생성 테스트 통과! 생성된 정의 수: {len(definitions)}")

    @pytest.mark.unit
    def test_compact_template_rendering(self):
        """Compact 템플릿 렌더링 단위 테스트"""
        # 테스트용 데이터
        test_data = {
            "newsletter_title": "자율주행 주간 브리프",
            "tagline": "이번 주, 주요 산업 동향을 미리 만나보세요.",
            "generation_date": "2025-05-23",
            "top_articles": [
                {
                    "title": "테스트 기사",
                    "url": "https://example.com/test",
                    "snippet": "테스트 내용입니다.",
                    "source_and_date": "TestSource · 2025-05-23",
                }
            ],
            "grouped_sections": [
                {
                    "heading": "📊 테스트 섹션",
                    "intro": "테스트 섹션 설명입니다.",
                    "articles": [],
                }
            ],
            "definitions": [
                {"term": "테스트용어", "explanation": "테스트를 위한 용어입니다."}
            ],
            "food_for_thought": "테스트 질문입니다.",
            "company_name": "Test Company",
        }

        template_dir = os.path.join(project_root, "templates")
        html = compose_compact_newsletter_html(
            test_data, template_dir, "newsletter_template_compact.html"
        )

        # 검증 - 실제 렌더링되는 제목으로 수정
        assert html is not None and len(html) > 0, "HTML이 생성되지 않았습니다"
        assert "자율주행 주간 브리프" in html, "제목이 렌더링되지 않았습니다"
        assert "💡 이런 뜻이에요" in html, "정의 섹션이 렌더링되지 않았습니다"
        assert "테스트용어" in html, "용어가 렌더링되지 않았습니다"
        assert "테스트를 위한 용어입니다" in html, "용어 설명이 렌더링되지 않았습니다"
        assert (
            "이번 주, 주요 산업 동향을 미리 만나보세요" in html
        ), "태그라인이 렌더링되지 않았습니다"

        print("✅ Compact 템플릿 렌더링 테스트 통과!")

    @pytest.mark.unit
    def test_definitions_extraction_edge_cases(self):
        """Definitions 추출 엣지 케이스 테스트"""

        # 빈 섹션 테스트
        empty_sections = []
        definitions = extract_key_definitions_for_compact(empty_sections)
        assert definitions == [], "빈 섹션에서 정의가 생성되었습니다"

        # definitions 필드가 없는 섹션 테스트
        no_definitions_sections = [{"title": "테스트 섹션", "articles": []}]
        definitions = extract_key_definitions_for_compact(no_definitions_sections)
        assert (
            definitions == []
        ), "definitions 필드가 없는 섹션에서 정의가 생성되었습니다"

        # 빈 definitions 필드가 있는 섹션 테스트
        empty_definitions_sections = [{"title": "테스트 섹션", "definitions": []}]
        definitions = extract_key_definitions_for_compact(empty_definitions_sections)
        assert definitions == [], "빈 definitions 필드에서 정의가 생성되었습니다"

        print("✅ Definitions 추출 엣지 케이스 테스트 통과!")

    @pytest.mark.unit
    def test_template_data_validation(self):
        """템플릿 데이터 검증 테스트"""

        # 필수 필드가 누락된 데이터 테스트
        minimal_data = {
            "newsletter_topic": "테스트 뉴스레터",  # newsletter_title 대신 newsletter_topic 사용
            "generation_date": "2025-05-23",
            "definitions": [],
        }

        template_dir = os.path.join(project_root, "templates")

        try:
            html = compose_compact_newsletter_html(
                minimal_data, template_dir, "newsletter_template_compact.html"
            )

            # 기본 HTML 구조는 생성되어야 함
            assert (
                html is not None and len(html) > 0
            ), "최소 데이터로 HTML이 생성되지 않았습니다"
            assert "<!DOCTYPE html>" in html, "유효한 HTML 형식이 아닙니다"
            # compose_compact_newsletter_html은 newsletter_topic을 newsletter_title로 매핑함
            assert "테스트 뉴스레터" in html, "제목이 렌더링되지 않았습니다"
            assert (
                "이번 주, 주요 산업 동향을 미리 만나보세요" in html
            ), "태그라인이 렌더링되지 않았습니다"

            print("✅ 템플릿 데이터 검증 테스트 통과!")

        except Exception as e:
            pytest.fail(f"템플릿 데이터 검증 테스트 실패: {e}")

    @pytest.mark.unit
    def test_error_handling_unit(self):
        """단위 테스트 레벨 에러 처리"""

        # 잘못된 템플릿 파일 경로
        test_data = {
            "newsletter_topic": "테스트",
            "generation_date": "2025-05-23",
            "definitions": [],
        }

        template_dir = os.path.join(project_root, "templates")

        try:
            # 존재하지 않는 템플릿 파일 - 이제 예외가 발생해야 함
            with pytest.raises(Exception):  # Jinja2 TemplateNotFound 예외 예상
                html = compose_compact_newsletter_html(
                    test_data, template_dir, "non_existent_template.html"
                )
            print("✅ 에러 처리 테스트 통과!")

        except Exception as e:
            pytest.fail(f"에러 처리 테스트 실패: {e}")

    @pytest.mark.unit
    def test_definitions_content_validation(self):
        """Definitions 내용 검증 테스트"""

        test_sections = [
            {
                "title": "AI 기술 동향",
                "definitions": [
                    {
                        "term": "GPT",
                        "explanation": "Generative Pre-trained Transformer의 약자",
                    },
                    {
                        "term": "LLM",
                        "explanation": "Large Language Model, 대규모 언어 모델",
                    },
                    {"term": "RAG", "explanation": "Retrieval-Augmented Generation"},
                    {"term": "MLOps", "explanation": "Machine Learning Operations"},
                ],
            }
        ]

        definitions = extract_key_definitions_for_compact(test_sections)

        # 최대 3개로 제한되는지 확인
        assert len(definitions) <= 3, f"정의가 3개를 초과했습니다: {len(definitions)}개"

        # 각 정의의 품질 확인
        for definition in definitions:
            term = definition.get("term", "")
            explanation = definition.get("explanation", "")

            assert len(term) <= 50, f"용어가 너무 깁니다: {term}"
            assert len(explanation) <= 200, f"설명이 너무 깁니다: {explanation}"
            assert term.strip() == term, "용어에 불필요한 공백이 있습니다"
            assert explanation.strip() == explanation, "설명에 불필요한 공백이 있습니다"

        print(
            f"✅ Definitions 내용 검증 테스트 통과! 선택된 정의: {[d['term'] for d in definitions]}"
        )


def test_compact_newsletter_unit_standalone():
    """독립 실행 가능한 간단한 단위 테스트"""
    print("=== Compact 뉴스레터 단위 테스트 (독립 실행) ===")

    try:
        # 간단한 체인 생성 테스트
        chain = get_newsletter_chain(is_compact=True)
        assert chain is not None, "체인 생성 실패"

        print("✅ 독립 단위 테스트 통과: Compact 체인이 정상적으로 생성되었습니다!")

    except Exception as e:
        print(f"❌ 독립 단위 테스트 실패: {e}")
        pytest.fail(f"독립 단위 테스트 실패: {e}")


if __name__ == "__main__":
    # 독립 실행 시 간단한 테스트 수행
    try:
        # 간단한 체인 생성 테스트
        chain = get_newsletter_chain(is_compact=True)
        assert chain is not None, "체인 생성 실패"

        print("\n🎉 모든 독립 단위 테스트가 통과했습니다!")
        print(
            "전체 단위 테스트를 실행하려면: python -m pytest tests/test_compact_newsletter.py -v"
        )
    except Exception as e:
        print(f"\n❌ 일부 단위 테스트가 실패했습니다: {e}")
        sys.exit(1)
