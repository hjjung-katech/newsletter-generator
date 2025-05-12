# -*- coding: utf-8 -*-
"""
뉴스레터 생성 기능 통합 테스트
"""
from newsletter.chains import get_summarization_chain
import os
import sys
import datetime
import pytest
import re

# 테스트 데이터 생성
test_data = {
    "keywords": "인공지능, 머신러닝",
    "articles": [
        {
            "title": "구글, 새로운 AI 모델 출시",
            "url": "https://example.com/google-ai",
            "content": "구글이 새로운 AI 모델 'Gemini'를 출시했습니다. 이번 모델은 기존 모델보다 성능이 30% 향상되었으며, 다국어 처리 능력이 크게 개선되었습니다.",
        },
        {
            "title": "애플, AI 기술 투자 확대",
            "url": "https://example.com/apple-ai",
            "content": "애플이 AI 기술 개발에 대한 투자를 확대한다고 발표했습니다. 향후 5년간 100억 달러를 투자할 계획이며, 음성 인식과 이미지 처리 분야에 집중할 예정입니다.",
        },
    ],
}


def test_newsletter_generation():
    """뉴스레터 생성 테스트"""
    print("===== 뉴스레터 생성 테스트 시작 =====")
    try:
        # 체인 생성
        print("1. Summarization 체인 생성 중...")
        chain = get_summarization_chain()
        print("✅ 체인 생성 성공")

        # 뉴스레터 생성
        print("\n2. 뉴스레터 생성 중...")
        result = chain.invoke(test_data)
        print(f"✅ 뉴스레터 생성 완료 (길이: {len(result)} 자)")

        # 마크다운 코드 블록 제거
        # LLM이 ```html ... ``` 형태로 응답하는 경우 처리
        clean_result = result
        markdown_pattern = r"```(?:html)?\n([\s\S]*?)\n```"
        markdown_match = re.search(markdown_pattern, result)
        if markdown_match:
            clean_result = markdown_match.group(1)
            print(
                f"마크다운 코드 블록이 제거되었습니다. (이전 길이: {len(result)}, 새 길이: {len(clean_result)})"
            )

        # 결과 파일에 저장
        # 프로젝트 루트의 output 디렉토리에 파일 저장
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            output_dir, f"test_newsletter_result_{timestamp}.html"
        )
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(clean_result)

        # 검증
        print("\n3. 생성된 뉴스레터 검증 중...")

        # HTML 구조 확인
        assert clean_result.startswith(
            "<!DOCTYPE html>"
        ), "생성된 문서가 HTML이 아닙니다."
        print(f"✅ HTML 구조 확인")

        # 키워드 포함 확인
        assert "머신러닝" in clean_result, "생성된 문서에 키워드가 없습니다."
        print(f"✅ 키워드 포함 확인")

        # 기사 내용 포함 확인
        assert "구글" in clean_result, "생성된 문서에 기사 내용이 없습니다."
        print(f"✅ 기사 내용 포함 확인")

        print(
            f"\n✅ 뉴스레터 생성 테스트 성공! 결과는 {output_path} 파일을 확인하세요."
        )
    except Exception as e:
        print(f"\n❌ 뉴스레터 생성 중 오류 발생: {e}")
        pytest.fail(f"뉴스레터 생성 중 오류 발생: {e}")


if __name__ == "__main__":
    success = test_newsletter_generation()
    print(f"\n테스트 결과: {'성공' if success else '실패'}")
    sys.exit(0 if success else 1)
