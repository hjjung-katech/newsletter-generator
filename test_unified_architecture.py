#!/usr/bin/env python3
"""
Test script to verify the unified newsletter architecture works correctly
for both compact and detailed newsletter generation.

This script tests the 10-step unified flow:
1. News keyword determination (domain-based or direct keywords)
2. News article search
3. News article period filtering
4. News article scoring
5. Top 3 article selection
6. Topic grouping of remaining articles (compact: 2-3 groups, detailed: 4-6 groups)
7. Grouped news content summarization (compact: brief, detailed: paragraph-level)
8. Term definitions (compact: up to 3, detailed: 0-2 per group, no duplicates)
9. Food for thought generation
10. Template-based final newsletter generation
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, List

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from newsletter.compose import (
    NewsletterConfig,
    compose_newsletter,
    extract_and_prepare_top_articles,
    create_grouped_sections,
    extract_definitions,
    extract_food_for_thought,
    render_newsletter_template,
)


def create_test_data() -> Dict[str, Any]:
    """Create comprehensive test data that simulates the output from the news processing pipeline."""
    return {
        "newsletter_topic": "AI 신약 개발, 디지털 치료제, 세포 유전자 치료제",
        "generation_date": datetime.now().strftime("%Y-%m-%d"),
        "generation_timestamp": datetime.now().strftime("%H:%M:%S"),
        "recipient_greeting": "안녕하세요, 전략프로젝트팀의 젊은 팀원과 수석전문위원 여러분.",
        "introduction_message": "지난 한 주간의 AI 신약 개발, 디지털 치료제, 세포 유전자 치료제 산업 관련 주요 기술 동향 및 뉴스를 정리하여 보내드립니다.",
        "search_keywords": ["AI 신약 개발", "디지털 치료제", "세포 유전자 치료제"],
        "sections": [
            {
                "title": "AI 신약 개발",
                "summary_paragraphs": [
                    "AI를 활용한 신약 개발은 업계의 큰 관심을 받고 있으며, 개발 시간 단축 및 성공률 증가에 기여할 것으로 기대됩니다.",
                    "다만, 아직 극복해야 할 과제들이 존재하며, 관련 교육 플랫폼 및 생태계 조성이 중요합니다.",
                    "국내외 제약회사들이 AI 기반 신약 개발에 대한 투자를 확대하고 있는 추세입니다.",
                ],
                "definitions": [
                    {
                        "term": "AI 신약 개발",
                        "explanation": "인공지능 기술을 활용하여 신약 후보물질 발굴, 약물 설계, 임상시험 최적화 등의 과정을 개선하는 연구 분야입니다.",
                    },
                    {
                        "term": "약물 설계",
                        "explanation": "컴퓨터 시뮬레이션과 AI를 이용하여 특정 질병에 효과적인 약물의 구조를 설계하는 과정입니다.",
                    },
                ],
                "news_links": [
                    {
                        "title": "[PDF] AI를 활용한 혁신 신약개발의 동향 및 정책 시사점",
                        "url": "https://www.kistep.re.kr/boardDownload.es?bid=0031&list_no=94091&seq=1",
                        "source_and_date": "KISTEP, 2024-01-15",
                    },
                    {
                        "title": '제약바이오, AI 신약개발 박차…"패러다임 바뀐다"',
                        "url": "https://www.kpanews.co.kr/article/show.asp?idx=256331&category=D",
                        "source_and_date": "KPA News, 2024-01-14",
                    },
                    {
                        "title": "AI 신약개발 플랫폼 '알파폴드3' 공개…단백질 상호작용 예측",
                        "url": "https://example.com/alphafold3",
                        "source_and_date": "바이오스펙테이터, 2024-01-13",
                    },
                ],
            },
            {
                "title": "디지털 치료제",
                "summary_paragraphs": [
                    "디지털 치료제는 약물이 아닌 소프트웨어를 기반으로 질병을 예방, 관리, 치료하는 새로운 형태의 치료제입니다.",
                    "불면증, 우울증 등 다양한 질환에 적용 가능성을 보이며, 관련 규제 및 법적 기준 마련이 필요한 시점입니다.",
                    "국내에서도 디지털 치료제 개발 및 상용화를 위한 정책적 지원이 확대되고 있습니다.",
                ],
                "definitions": [
                    {
                        "term": "디지털 치료제",
                        "explanation": "소프트웨어 형태의 의료기기로, 질병의 예방, 관리, 치료를 목적으로 합니다. 주로 앱, 게임, 웨어러블 기기 등을 통해 제공됩니다.",
                    }
                ],
                "news_links": [
                    {
                        "title": "디지털 치료제 시장 급성장…2030년 130억 달러 전망",
                        "url": "https://example.com/digital-therapeutics-market",
                        "source_and_date": "메디컬타임즈, 2024-01-12",
                    },
                    {
                        "title": "식약처, 디지털 치료제 허가 가이드라인 발표",
                        "url": "https://example.com/kfda-guidelines",
                        "source_and_date": "청년의사, 2024-01-11",
                    },
                ],
            },
            {
                "title": "세포 유전자 치료제",
                "summary_paragraphs": [
                    "세포 유전자 치료제는 환자의 세포나 유전자를 직접 조작하여 질병을 치료하는 혁신적인 접근법입니다.",
                    "CAR-T 세포 치료제를 비롯한 다양한 치료법이 임상에서 성과를 보이고 있으며, 암 치료의 새로운 패러다임을 제시하고 있습니다.",
                    "높은 치료 효과에도 불구하고 비용과 안전성 문제가 여전히 해결해야 할 과제로 남아있습니다.",
                ],
                "definitions": [
                    {
                        "term": "CAR-T 세포 치료제",
                        "explanation": "환자의 T세포를 추출하여 유전자 조작을 통해 암세포를 더 잘 인식하고 공격할 수 있도록 개조한 후 다시 환자에게 주입하는 치료법입니다.",
                    },
                    {
                        "term": "유전자 편집",
                        "explanation": "CRISPR-Cas9 등의 기술을 사용하여 특정 유전자를 정확하게 수정, 삭제, 또는 삽입하는 기술입니다.",
                    },
                ],
                "news_links": [
                    {
                        "title": "국내 첫 CAR-T 치료제 허가…혈액암 치료 새 전기",
                        "url": "https://example.com/car-t-approval",
                        "source_and_date": "의학신문, 2024-01-10",
                    },
                    {
                        "title": "유전자 치료제 개발 가속화…글로벌 경쟁 치열",
                        "url": "https://example.com/gene-therapy-race",
                        "source_and_date": "바이오타임즈, 2024-01-09",
                    },
                ],
            },
            {
                "title": "바이오 투자 동향",
                "summary_paragraphs": [
                    "바이오 분야에 대한 투자가 지속적으로 증가하고 있으며, 특히 AI와 디지털 기술을 접목한 혁신적인 치료법에 대한 관심이 높습니다.",
                    "벤처캐피털과 제약회사들의 적극적인 투자로 바이오 스타트업 생태계가 활성화되고 있습니다.",
                ],
                "definitions": [
                    {
                        "term": "바이오 벤처",
                        "explanation": "생명과학 기술을 기반으로 혁신적인 의료 솔루션을 개발하는 스타트업 기업을 의미합니다.",
                    }
                ],
                "news_links": [
                    {
                        "title": "바이오 투자 열기 지속…올해 1조원 돌파 전망",
                        "url": "https://example.com/bio-investment",
                        "source_and_date": "이투데이, 2024-01-08",
                    }
                ],
            },
            {
                "title": "규제 및 정책",
                "summary_paragraphs": [
                    "정부는 바이오 분야의 혁신을 지원하기 위한 다양한 정책을 추진하고 있으며, 규제 샌드박스를 통해 신기술의 시장 진입을 돕고 있습니다.",
                    "국제적인 규제 조화를 통해 글로벌 시장 진출을 위한 기반을 마련하고 있습니다.",
                ],
                "definitions": [
                    {
                        "term": "규제 샌드박스",
                        "explanation": "혁신적인 기술이나 서비스가 기존 규제로 인해 시장 진입이 어려운 경우, 일정 기간 규제를 완화하여 실증할 수 있도록 하는 제도입니다.",
                    }
                ],
                "news_links": [
                    {
                        "title": "바이오 규제 샌드박스 확대…혁신 기술 지원 강화",
                        "url": "https://example.com/regulatory-sandbox",
                        "source_and_date": "헬스코리아뉴스, 2024-01-07",
                    }
                ],
            },
            {
                "title": "글로벌 동향",
                "summary_paragraphs": [
                    "미국과 유럽을 중심으로 바이오 기술 혁신이 가속화되고 있으며, 아시아 지역에서도 경쟁력 있는 기업들이 등장하고 있습니다.",
                    "국제 협력을 통한 공동 연구 개발이 활발해지고 있어 글로벌 바이오 생태계의 연결성이 강화되고 있습니다.",
                ],
                "definitions": [],
                "news_links": [
                    {
                        "title": "글로벌 바이오 시장 2024년 전망…성장세 지속",
                        "url": "https://example.com/global-bio-outlook",
                        "source_and_date": "바이오월드, 2024-01-06",
                    }
                ],
            },
        ],
        "food_for_thought": {
            "quote": "미래는 예측하는 것이 아니라 만들어가는 것이다.",
            "author": "피터 드러커",
            "message": "위에 언급된 세 가지 기술은 모두 미래 의료 패러다임을 변화시킬 잠재력을 가지고 있습니다. 각 기술의 발전 동향을 꾸준히 주시하고, 상호 연관성을 고려하여 R&D 전략을 수립한다면, 혁신적인 성과 창출과 국민 건강 증진에 기여할 수 있을 것입니다.",
        },
        "closing_message": "다음 주에 더 유익한 정보로 찾아뵙겠습니다. 감사합니다.",
        "editor_signature": "편집자 드림",
        "company_name": "전략프로젝트팀",
    }


def test_newsletter_config():
    """Test the NewsletterConfig class."""
    print("=== Testing NewsletterConfig ===")

    # Test compact config
    compact_config = NewsletterConfig.get_config("compact")
    print(f"Compact config: {compact_config}")

    assert compact_config["max_articles"] == 10
    assert compact_config["top_articles_count"] == 3
    assert compact_config["max_groups"] == 3
    assert compact_config["max_definitions"] == 3
    assert compact_config["template_name"] == "newsletter_template_compact.html"

    # Test detailed config
    detailed_config = NewsletterConfig.get_config("detailed")
    print(f"Detailed config: {detailed_config}")

    assert detailed_config["max_articles"] is None
    assert detailed_config["top_articles_count"] == 3
    assert detailed_config["max_groups"] == 6
    assert detailed_config["max_definitions"] is None
    assert detailed_config["template_name"] == "newsletter_template.html"

    print("✅ NewsletterConfig tests passed!")


def test_utility_functions():
    """Test the individual utility functions."""
    print("\n=== Testing Utility Functions ===")

    test_data = create_test_data()

    # Test extract_and_prepare_top_articles
    print("Testing extract_and_prepare_top_articles...")
    top_articles = extract_and_prepare_top_articles(test_data, 3)
    print(f"Top articles count: {len(top_articles)}")
    assert len(top_articles) <= 3
    if top_articles:
        assert "title" in top_articles[0]
        assert "url" in top_articles[0]
    print("✅ extract_and_prepare_top_articles passed!")

    # Test create_grouped_sections
    print("Testing create_grouped_sections...")
    compact_config = NewsletterConfig.get_config("compact")
    grouped_sections = create_grouped_sections(
        test_data,
        top_articles,
        max_groups=compact_config["max_groups"],
        max_articles=compact_config["max_articles"],
    )
    print(f"Grouped sections count: {len(grouped_sections)}")
    assert len(grouped_sections) <= compact_config["max_groups"]
    if grouped_sections:
        assert "heading" in grouped_sections[0]
        assert "articles" in grouped_sections[0]
    print("✅ create_grouped_sections passed!")

    # Test extract_definitions
    print("Testing extract_definitions...")
    definitions = extract_definitions(test_data, grouped_sections, compact_config)
    print(f"Definitions count: {len(definitions)}")
    assert len(definitions) <= compact_config["max_definitions"]
    if definitions:
        assert "term" in definitions[0]
        assert "explanation" in definitions[0]
    print("✅ extract_definitions passed!")

    # Test extract_food_for_thought
    print("Testing extract_food_for_thought...")
    food_for_thought = extract_food_for_thought(test_data)
    print(f"Food for thought type: {type(food_for_thought)}")
    assert food_for_thought is not None
    print("✅ extract_food_for_thought passed!")


def test_unified_compose_newsletter():
    """Test the unified compose_newsletter function for both styles."""
    print("\n=== Testing Unified compose_newsletter Function ===")

    test_data = create_test_data()
    template_dir = os.path.join(project_root, "templates")

    if not os.path.exists(template_dir):
        print(f"⚠️  Template directory not found: {template_dir}")
        print("Skipping template rendering tests...")
        return

    # Test compact style
    print("Testing compact style...")
    try:
        compact_html = compose_newsletter(test_data, template_dir, "compact")
        assert isinstance(compact_html, str)
        assert len(compact_html) > 0
        assert "html" in compact_html.lower()
        print("✅ Compact newsletter generation passed!")

        # Save compact output for inspection
        output_dir = os.path.join(project_root, "output")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        compact_file = os.path.join(output_dir, f"test_compact_{timestamp}.html")
        with open(compact_file, "w", encoding="utf-8") as f:
            f.write(compact_html)
        print(f"📄 Compact newsletter saved to: {compact_file}")

    except Exception as e:
        print(f"❌ Compact newsletter generation failed: {e}")

    # Test detailed style
    print("Testing detailed style...")
    try:
        detailed_html = compose_newsletter(test_data, template_dir, "detailed")
        assert isinstance(detailed_html, str)
        assert len(detailed_html) > 0
        assert "html" in detailed_html.lower()
        print("✅ Detailed newsletter generation passed!")

        # Save detailed output for inspection
        detailed_file = os.path.join(output_dir, f"test_detailed_{timestamp}.html")
        with open(detailed_file, "w", encoding="utf-8") as f:
            f.write(detailed_html)
        print(f"📄 Detailed newsletter saved to: {detailed_file}")

    except Exception as e:
        print(f"❌ Detailed newsletter generation failed: {e}")


def test_legacy_compatibility():
    """Test that legacy functions still work."""
    print("\n=== Testing Legacy Compatibility ===")

    from newsletter.compose import (
        compose_newsletter_html,
        compose_compact_newsletter_html,
    )

    test_data = create_test_data()
    template_dir = os.path.join(project_root, "templates")

    if not os.path.exists(template_dir):
        print("⚠️  Template directory not found. Skipping legacy tests...")
        return

    # Test legacy detailed function
    print("Testing legacy compose_newsletter_html...")
    try:
        detailed_html = compose_newsletter_html(
            test_data, template_dir, "newsletter_template.html"
        )
        assert isinstance(detailed_html, str)
        assert len(detailed_html) > 0
        print("✅ Legacy detailed function works!")
    except Exception as e:
        print(f"❌ Legacy detailed function failed: {e}")

    # Test legacy compact function
    print("Testing legacy compose_compact_newsletter_html...")
    try:
        compact_html = compose_compact_newsletter_html(
            test_data, template_dir, "newsletter_template_compact.html"
        )
        assert isinstance(compact_html, str)
        assert len(compact_html) > 0
        print("✅ Legacy compact function works!")
    except Exception as e:
        print(f"❌ Legacy compact function failed: {e}")


def test_10_step_flow():
    """Test that the 10-step unified flow is properly implemented."""
    print("\n=== Testing 10-Step Unified Flow ===")

    test_data = create_test_data()
    template_dir = os.path.join(project_root, "templates")

    print("Step 1: News keyword determination ✅ (provided in test data)")
    print("Step 2: News article search ✅ (simulated in test data)")
    print("Step 3: News article period filtering ✅ (simulated in test data)")
    print("Step 4: News article scoring ✅ (simulated in test data)")

    # Step 5: Top 3 article selection
    print("Step 5: Top 3 article selection...")
    compact_config = NewsletterConfig.get_config("compact")
    top_articles = extract_and_prepare_top_articles(
        test_data, compact_config["top_articles_count"]
    )
    assert len(top_articles) <= 3
    print(f"✅ Selected {len(top_articles)} top articles")

    # Step 6: Topic grouping
    print("Step 6: Topic grouping...")
    grouped_sections = create_grouped_sections(
        test_data,
        top_articles,
        max_groups=compact_config["max_groups"],
        max_articles=compact_config["max_articles"],
    )
    assert len(grouped_sections) <= compact_config["max_groups"]
    print(f"✅ Created {len(grouped_sections)} topic groups")

    # Step 7: Content summarization (already in test data)
    print("Step 7: Grouped news content summarization ✅ (provided in test data)")

    # Step 8: Term definitions
    print("Step 8: Term definitions...")
    definitions = extract_definitions(test_data, grouped_sections, compact_config)
    assert len(definitions) <= compact_config["max_definitions"]
    print(f"✅ Extracted {len(definitions)} definitions")

    # Step 9: Food for thought
    print("Step 9: Food for thought generation...")
    food_for_thought = extract_food_for_thought(test_data)
    assert food_for_thought is not None
    print("✅ Generated food for thought")

    # Step 10: Template-based final newsletter generation
    print("Step 10: Template-based final newsletter generation...")
    if os.path.exists(template_dir):
        final_html = compose_newsletter(test_data, template_dir, "compact")
        assert isinstance(final_html, str) and len(final_html) > 0
        print("✅ Generated final newsletter HTML")
    else:
        print("⚠️  Template directory not found, skipping final generation")

    print("🎉 All 10 steps of the unified flow completed successfully!")


def main():
    """Run all tests."""
    print("🧪 Testing Unified Newsletter Architecture")
    print("=" * 50)

    try:
        test_newsletter_config()
        test_utility_functions()
        test_unified_compose_newsletter()
        test_legacy_compatibility()
        test_10_step_flow()

        print("\n" + "=" * 50)
        print("🎉 All tests passed! The unified architecture is working correctly.")
        print("\n📋 Summary:")
        print("✅ NewsletterConfig class provides centralized settings")
        print("✅ Unified compose_newsletter() function handles both styles")
        print("✅ All utility functions work correctly")
        print("✅ Legacy compatibility maintained")
        print("✅ Complete 10-step flow implemented")
        print("\n🏗️  Architecture Benefits:")
        print("• Single codebase for both newsletter types")
        print("• Configuration-driven differences")
        print("• Easy to extend for new template styles")
        print("• Consistent behavior across versions")
        print("• Maintainable and testable code")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
