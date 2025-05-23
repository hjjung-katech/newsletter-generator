#!/usr/bin/env python3
"""
Compact 뉴스레터 체인 테스트 스크립트 (Legacy)
"""

import os
import sys

sys.path.append(os.path.dirname(__file__))

from newsletter.chains import get_newsletter_chain

# 테스트 데이터
test_data = {
    "articles": [
        {
            "title": "OpenAI GPT-4 출시",
            "url": "https://example.com/gpt4",
            "snippet": "OpenAI가 새로운 GPT-4 모델을 발표했습니다.",
            "source": "TechCrunch",
            "date": "2025-05-23",
        },
        {
            "title": "Google AI 연구 발표",
            "url": "https://example.com/google-ai",
            "snippet": "Google이 새로운 AI 연구 결과를 발표했습니다.",
            "source": "Wired",
            "date": "2025-05-22",
        },
    ],
    "keywords": ["AI", "인공지능"],
}

if __name__ == "__main__":
    try:
        print("Compact 체인 테스트 시작...")
        # 수정: get_newsletter_chain with is_compact=True 사용
        chain = get_newsletter_chain(is_compact=True)
        result = chain.invoke(test_data)

        print("테스트 완료!")

        # 결과 검증
        if result and isinstance(result, str) and len(result) > 0:
            print("✅ Compact 체인 테스트 성공!")
            print(f"생성된 HTML 길이: {len(result)} 문자")

            # 기본적인 HTML 구조 확인
            if "<!DOCTYPE html>" in result:
                print("✅ 유효한 HTML 형식 확인")
            else:
                print("❌ HTML 형식 검증 실패")

            # 핵심 섹션 확인
            if "이런 뜻이에요" in result:
                print("✅ '이런 뜻이에요' 섹션 포함 확인")
            else:
                print("⚠️ '이런 뜻이에요' 섹션 미발견")

        else:
            print("❌ 테스트 실패: 유효하지 않은 결과")
            print(f"결과 타입: {type(result)}")
            print(f"결과 길이: {len(result) if result else 'N/A'}")

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
