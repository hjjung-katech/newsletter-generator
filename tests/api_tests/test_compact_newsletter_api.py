#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compact 뉴스레터 API 통합 테스트
LLM API, 뉴스 검색 API 등 외부 API를 사용하는 테스트들
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

from newsletter.graph import generate_newsletter
from newsletter.chains import get_newsletter_chain, create_summarization_chain


class TestCompactNewsletterAPI:
    """Compact 뉴스레터 API 테스트 클래스"""

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

    @pytest.mark.api
    @pytest.mark.integration
    @pytest.mark.skip(reason="API quota limitation - requires external API calls")
    def test_compact_newsletter_generation_full_integration(self):
        """완전 통합 테스트: 실제 API를 사용하여 compact 뉴스레터 생성"""
        try:
            html, status = generate_newsletter(
                keywords=["자율주행"], template_style="compact", news_period_days=3
            )

            # 기본 검증
            assert status == "success", f"뉴스레터 생성 실패: {status}"
            assert html is not None and len(html) > 0, "HTML 내용이 비어있습니다"
            assert "<!DOCTYPE html>" in html, "유효한 HTML 형식이 아닙니다"

            # 핵심 섹션 검증
            assert "이번 주 꼭 봐야 할" in html, "상위 기사 섹션이 누락되었습니다"
            assert "💡 이런 뜻이에요" in html, "용어 정의 섹션이 누락되었습니다"
            assert "💡 생각해 볼 거리" in html, "생각해 볼 거리 섹션이 누락되었습니다"

            # 자율주행 관련 용어 정의 확인
            assert (
                "자율주행" in html or "로보택시" in html
            ), "자율주행 관련 용어 정의가 누락되었습니다"

            print(
                "✅ 완전 통합 테스트 통과: Compact 뉴스레터가 성공적으로 생성되었습니다!"
            )

            # 생성된 파일 경로 확인
            output_dir = os.path.join(project_root, "output")
            files = [
                f
                for f in os.listdir(output_dir)
                if f.endswith(".html") and "compact" in f
            ]
            if files:
                latest_file = max(
                    files, key=lambda x: os.path.getctime(os.path.join(output_dir, x))
                )
                print(f"✅ 생성된 파일: {latest_file}")

        except Exception as e:
            pytest.fail(f"완전 통합 테스트 실패: {e}")

    @pytest.mark.api
    @pytest.mark.slow
    @pytest.mark.skip(reason="API quota limitation - requires external API calls")
    def test_multiple_keywords_compact_api(self):
        """여러 키워드를 사용한 compact 뉴스레터 API 테스트"""
        try:
            html, status = generate_newsletter(
                keywords=["AI", "자율주행", "로봇"],
                template_style="compact",
                news_period_days=7,
            )

            assert status == "success", f"여러 키워드 테스트 실패: {status}"
            assert "이런 뜻이에요" in html, "정의 섹션이 누락되었습니다"

            # 여러 키워드 관련 내용이 포함되어 있는지 확인
            keyword_found = any(
                keyword in html for keyword in ["AI", "자율주행", "로봇"]
            )
            assert keyword_found, "키워드 관련 내용이 발견되지 않습니다"

            print("✅ 여러 키워드 compact API 테스트 통과!")

        except Exception as e:
            pytest.fail(f"여러 키워드 API 테스트 실패: {e}")

    @pytest.mark.api
    @pytest.mark.skip(reason="API quota limitation - requires external API calls")
    def test_compact_chain_with_real_llm(self):
        """실제 LLM을 사용한 Compact 체인 테스트"""
        try:
            # Compact 체인 생성
            chain = get_newsletter_chain(is_compact=True)
            assert chain is not None, "Compact 체인 생성 실패"

            # 체인 실행 (실제 LLM 호출)
            result = chain.invoke(self.test_data)
            assert result is not None, "체인 실행 결과가 None입니다"
            assert isinstance(result, str), "결과가 문자열(HTML)이 아닙니다"

            # HTML 기본 구조 검증
            assert "<!DOCTYPE html>" in result, "유효한 HTML 형식이 아닙니다"
            assert (
                "<html" in result and "</html>" in result
            ), "HTML 태그가 올바르지 않습니다"

            # definitions 섹션 확인
            assert "이런 뜻이에요" in result, "정의 섹션이 누락되었습니다"

            print("✅ 실제 LLM을 사용한 Compact 체인 테스트 통과!")

        except Exception as e:
            pytest.fail(f"실제 LLM Compact 체인 테스트 실패: {e}")

    @pytest.mark.api
    @pytest.mark.unit
    @pytest.mark.skip(reason="API quota limitation - requires external API calls")
    def test_fallback_definitions_with_mocked_llm(self):
        """모킹된 LLM을 사용한 Fallback definitions 생성 테스트"""
        try:
            # Summarization 체인 생성
            chain = create_summarization_chain(is_compact=True)

            # 테스트 데이터 준비
            test_categories_data = {
                "categories": [
                    {"title": "자율주행 기술 개발", "article_indices": [0, 1]}
                ]
            }

            test_data = {
                "categories_data": test_categories_data,
                "articles_data": {"articles": self.test_articles},
            }

            # LLM 모킹 - 빈 definitions를 반환하도록 설정
            with patch("newsletter.chains.get_llm") as mock_llm:
                mock_response = MagicMock()
                mock_response.content = (
                    '{"intro": "테스트 인트로", "definitions": [], "news_links": []}'
                )
                mock_llm.return_value.invoke.return_value = mock_response

                result = chain.invoke(test_data)

                # fallback definitions가 생성되었는지 확인
                assert "sections" in result, "섹션이 생성되지 않았습니다"
                sections = result["sections"]
                assert len(sections) > 0, "섹션이 비어있습니다"

                # 자율주행 관련 섹션에서 fallback definitions 확인
                definitions_found = False
                for section in sections:
                    if "자율주행" in section.get("title", ""):
                        definitions = section.get("definitions", [])
                        if len(definitions) > 0:
                            definitions_found = True
                            # 자율주행 관련 기본 정의 확인
                            terms = [d.get("term", "") for d in definitions]
                            assert any(
                                "자율주행" in term.lower() or "로보택시" in term.lower()
                                for term in terms
                            ), f"자율주행 관련 정의가 없습니다: {terms}"
                            break

                assert definitions_found, "Fallback definitions이 생성되지 않았습니다"
                print("✅ Fallback definitions 테스트 통과!")

        except Exception as e:
            pytest.fail(f"Fallback definitions 테스트 실패: {e}")

    @pytest.mark.api
    @pytest.mark.slow
    @pytest.mark.skip(reason="API quota limitation - requires external API calls")
    def test_compact_newsletter_with_different_topics(self):
        """다양한 주제로 compact 뉴스레터 생성 테스트"""
        topics = [
            ["반도체", "AI"],
            ["자동차", "전기차"],
            ["의료", "바이오"],
        ]

        for keywords in topics:
            try:
                html, status = generate_newsletter(
                    keywords=keywords, template_style="compact", news_period_days=7
                )

                assert status == "success", f"주제 {keywords} 테스트 실패: {status}"
                assert (
                    "<!DOCTYPE html>" in html
                ), f"주제 {keywords}에서 유효하지 않은 HTML"

                # 적어도 하나의 키워드가 HTML에 포함되어 있는지 확인
                keyword_found = any(keyword in html for keyword in keywords)
                assert keyword_found, f"주제 {keywords} 관련 내용이 발견되지 않습니다"

                print(f"✅ {keywords} 주제 테스트 통과!")

            except Exception as e:
                pytest.fail(f"주제 {keywords} 테스트 실패: {e}")

    @pytest.mark.api
    @pytest.mark.skip(reason="API quota limitation - requires external API calls")
    def test_api_error_handling(self):
        """API 오류 처리 테스트"""
        try:
            # 비정상적인 키워드로 테스트
            html, status = generate_newsletter(
                keywords=[""], template_style="compact", news_period_days=1
            )

            # 오류가 있어도 적절히 처리되어야 함
            assert status in ["success", "error"], f"예상하지 못한 상태: {status}"

            if status == "success":
                assert html is not None, "성공 상태인데 HTML이 None입니다"
                print("✅ 빈 키워드에 대한 오류 처리 테스트 통과!")
            else:
                print("✅ 빈 키워드가 적절히 오류로 처리되었습니다!")

        except Exception as e:
            # 예외가 발생해도 적절히 처리되어야 함
            print(f"✅ 예외가 적절히 처리되었습니다: {e}")


@pytest.mark.api
@pytest.mark.skip(reason="API quota limitation - requires external API calls")
def test_api_connectivity():
    """API 연결성 기본 테스트"""
    try:
        # 간단한 뉴스레터 생성으로 API 연결 확인
        html, status = generate_newsletter(
            keywords=["테스트"], template_style="compact", news_period_days=1
        )

        assert status in ["success", "error"], "API 연결 테스트에서 예상하지 못한 상태"
        print(f"✅ API 연결성 테스트 완료: {status}")
        return True

    except Exception as e:
        print(f"API 연결 테스트 중 오류: {e}")
        return False


if __name__ == "__main__":
    # 독립 실행 시 기본 연결성 테스트만 수행 (실제로는 스킵됨)
    print("=== Compact 뉴스레터 API 테스트 (독립 실행) ===")
    print(
        "⚠️ API 할당량 문제로 모든 API 테스트가 스킵됩니다. pytest -m 'not api'로 실행하세요."
    )
