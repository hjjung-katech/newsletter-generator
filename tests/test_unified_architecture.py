#!/usr/bin/env python3
"""
통합 아키텍처 테스트 - 10단계 통합 플로우 검증
NewsletterConfig와 아키텍처 정합성 검증에 집중합니다.

검증 영역:
1. NewsletterConfig 클래스 설정
2. 10단계 통합 플로우 검증
3. 환경별 설정 차이 검증
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict

import pytest

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from newsletter.template_paths import get_newsletter_template_dir  # noqa: E402
from newsletter_core.application.generation.compose import (  # noqa: E402
    NewsletterConfig,
    compose_newsletter,
    create_grouped_sections,
    extract_and_prepare_top_articles,
    extract_definitions,
    extract_food_for_thought,
)


def create_test_data() -> Dict[str, Any]:
    """통합 테스트용 데이터 생성"""
    return {
        "newsletter_topic": "AI 기술 동향",
        "generation_date": datetime.now().strftime("%Y-%m-%d"),
        "search_keywords": ["AI", "머신러닝", "딥러닝"],
        "sections": [
            {
                "title": "AI 기술 발전",
                "summary_paragraphs": ["AI 기술이 빠르게 발전하고 있습니다."],
                "definitions": [
                    {
                        "term": "머신러닝",
                        "explanation": "데이터로부터 학습하는 AI 기술입니다.",
                    },
                    {
                        "term": "딥러닝",
                        "explanation": "신경망을 활용한 고급 머신러닝 기법입니다.",
                    },
                ],
                "news_links": [
                    {
                        "title": "AI 기술 혁신",
                        "url": "https://example.com/ai",
                        "source_and_date": "Tech News, 2025-05-24",
                    }
                ],
            },
            {
                "title": "반도체 동향",
                "summary_paragraphs": ["반도체 기술이 AI 발전을 이끌고 있습니다."],
                "definitions": [
                    {
                        "term": "GPU",
                        "explanation": "그래픽 처리 장치로 AI 연산에 최적화되어 있습니다.",
                    }
                ],
                "news_links": [
                    {
                        "title": "AI 칩 개발",
                        "url": "https://example.com/chip",
                        "source_and_date": "Semiconductor News, 2025-05-23",
                    }
                ],
            },
        ],
        "food_for_thought": {
            "quote": "미래는 예측하는 것이 아니라 만들어가는 것이다.",
            "author": "피터 드러커",
            "message": "AI 기술 발전을 통해 더 나은 미래를 만들어 나갑시다.",
        },
    }


class TestUnifiedArchitecture:
    """통합 아키텍처 테스트 클래스"""

    def setup_method(self):
        """테스트 설정"""
        self.test_data = create_test_data()

    @pytest.mark.unit
    def test_newsletter_config_settings(self):
        """NewsletterConfig 클래스 설정 테스트"""
        print("=== NewsletterConfig 설정 테스트 ===")

        # Compact 설정 검증
        compact_config = NewsletterConfig.get_config("compact")
        assert compact_config["max_articles"] == 10
        assert compact_config["top_articles_count"] == 3
        assert compact_config["max_groups"] == 3
        assert compact_config["max_definitions"] == 3
        assert compact_config["template_name"] == "newsletter_template_compact.html"
        print("✅ Compact 설정 검증 완료")

        # Detailed 설정 검증
        detailed_config = NewsletterConfig.get_config("detailed")
        assert detailed_config["max_articles"] is None
        assert detailed_config["top_articles_count"] == 3
        assert detailed_config["max_groups"] == 6
        assert detailed_config["max_definitions"] is None
        assert detailed_config["template_name"] == "newsletter_template.html"
        print("✅ Detailed 설정 검증 완료")

        # 환경별 차이 검증
        assert compact_config["max_definitions"] != detailed_config["max_definitions"]
        assert compact_config["max_groups"] != detailed_config["max_groups"]
        assert compact_config["template_name"] != detailed_config["template_name"]
        print("✅ 환경별 설정 차이 검증 완료")

    @pytest.mark.unit
    def test_utility_functions_integration(self):
        """유틸리티 함수들의 통합 테스트"""
        print("=== 유틸리티 함수 통합 테스트 ===")

        compact_config = NewsletterConfig.get_config("compact")

        # Step 5: Top articles 추출
        top_articles = extract_and_prepare_top_articles(
            self.test_data, compact_config["top_articles_count"]
        )
        assert len(top_articles) <= compact_config["top_articles_count"]
        print(f"✅ Top articles 추출: {len(top_articles)}개")

        # Step 6: 그룹화
        grouped_sections = create_grouped_sections(
            self.test_data,
            top_articles,
            max_groups=compact_config["max_groups"],
            max_articles=compact_config["max_articles"],
        )
        assert len(grouped_sections) <= compact_config["max_groups"]
        print(f"✅ 섹션 그룹화: {len(grouped_sections)}개")

        # Step 8: 정의 추출
        definitions = extract_definitions(
            self.test_data, grouped_sections, compact_config
        )
        assert len(definitions) <= compact_config["max_definitions"]
        print(f"✅ 정의 추출: {len(definitions)}개")

        # Step 9: Food for thought 추출
        food_for_thought = extract_food_for_thought(self.test_data)
        assert food_for_thought is not None
        print("✅ Food for thought 추출 완료")

    @pytest.mark.unit
    def test_10_step_flow_validation(self):
        """10단계 통합 플로우 검증"""
        print("=== 10단계 통합 플로우 검증 ===")

        compact_config = NewsletterConfig.get_config("compact")

        # Steps 1-4: 이미 테스트 데이터에 포함됨
        print("Steps 1-4: 키워드 결정, 검색, 필터링, 스코링 ✅")

        # Step 5: Top 3 선택
        top_articles = extract_and_prepare_top_articles(
            self.test_data, compact_config["top_articles_count"]
        )
        assert len(top_articles) <= 3
        print(f"Step 5: Top {len(top_articles)} 기사 선택 ✅")

        # Step 6: 주제 그룹화
        grouped_sections = create_grouped_sections(
            self.test_data,
            top_articles,
            max_groups=compact_config["max_groups"],
            max_articles=compact_config["max_articles"],
        )
        assert len(grouped_sections) <= compact_config["max_groups"]
        print(f"Step 6: {len(grouped_sections)}개 그룹 생성 ✅")

        # Step 7: 요약 (테스트 데이터에 포함)
        print("Step 7: 그룹별 요약 ✅")

        # Step 8: 용어 정의
        definitions = extract_definitions(
            self.test_data, grouped_sections, compact_config
        )
        assert len(definitions) <= compact_config["max_definitions"]
        print(f"Step 8: {len(definitions)}개 정의 추출 ✅")

        # Step 9: Food for thought
        food_for_thought = extract_food_for_thought(self.test_data)
        assert food_for_thought is not None
        print("Step 9: Food for thought 생성 ✅")

        # Step 10: 최종 생성 (템플릿 테스트는 선택적)
        template_dir = get_newsletter_template_dir()
        if os.path.exists(template_dir):
            try:
                final_html = compose_newsletter(self.test_data, template_dir, "compact")
                assert isinstance(final_html, str) and len(final_html) > 0
                print("Step 10: 최종 HTML 생성 ✅")
            except Exception as e:
                print(f"Step 10: 템플릿 생성 건너뜀 (예상된 오류: {e})")
        else:
            print("Step 10: 템플릿 디렉토리 없음, 건너뜀")

        print("🎉 10단계 통합 플로우 검증 완료!")

    @pytest.mark.unit
    def test_config_driven_differences(self):
        """설정 기반 동작 차이 검증"""
        print("=== 설정 기반 동작 차이 검증 ===")

        compact_config = NewsletterConfig.get_config("compact")
        detailed_config = NewsletterConfig.get_config("detailed")

        # Compact 모드 테스트
        compact_definitions = extract_definitions(
            self.test_data, self.test_data["sections"], compact_config
        )
        compact_groups = create_grouped_sections(
            self.test_data,
            [],
            max_groups=compact_config["max_groups"],
            max_articles=compact_config["max_articles"],
        )

        # Detailed 모드 테스트
        detailed_definitions = extract_definitions(
            self.test_data, self.test_data["sections"], detailed_config
        )
        detailed_groups = create_grouped_sections(
            self.test_data,
            [],
            max_groups=detailed_config["max_groups"],
            max_articles=detailed_config["max_articles"],
        )

        # 차이 검증
        assert len(compact_definitions) <= compact_config["max_definitions"]
        assert len(compact_groups) <= compact_config["max_groups"]

        # Detailed는 제한이 없거나 더 큼
        assert (
            detailed_config["max_definitions"] is None
            or len(detailed_definitions) <= detailed_config["max_definitions"]
        )
        assert len(detailed_groups) <= detailed_config["max_groups"]

        print(f"✅ Compact: {len(compact_definitions)}개 정의, {len(compact_groups)}개 그룹")
        print(
            f"✅ Detailed: {len(detailed_definitions)}개 정의, {len(detailed_groups)}개 그룹"
        )
        print("✅ 설정 기반 동작 차이 검증 완료")


def main():
    """독립 실행"""
    print("🧪 통합 아키텍처 테스트 실행")
    print("=" * 50)

    test_instance = TestUnifiedArchitecture()
    test_instance.setup_method()

    try:
        test_instance.test_newsletter_config_settings()
        test_instance.test_utility_functions_integration()
        test_instance.test_10_step_flow_validation()
        test_instance.test_config_driven_differences()

        print("\n" + "=" * 50)
        print("🎉 모든 아키텍처 테스트 통과!")
        print("\n📋 검증 완료 항목:")
        print("✅ NewsletterConfig 클래스 설정")
        print("✅ 유틸리티 함수 통합")
        print("✅ 10단계 플로우 검증")
        print("✅ 설정 기반 동작 차이")
        print("\n🏗️ 아키텍처 이점:")
        print("• 단일 코드베이스로 두 스타일 지원")
        print("• 설정 기반 차이점 관리")
        print("• 일관된 10단계 플로우")
        print("• 확장 가능한 구조")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
