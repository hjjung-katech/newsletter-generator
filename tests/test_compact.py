#!/usr/bin/env python3
"""
Compact 뉴스레터 체인 테스트 스크립트
"""

import os
import sys

sys.path.append(os.path.dirname(__file__))

from newsletter.chains import get_compact_newsletter_chain

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
        chain = get_compact_newsletter_chain()
        result = chain.invoke(test_data)
        print("테스트 완료!")
        print(f"결과: {result}")
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback

        traceback.print_exc()
