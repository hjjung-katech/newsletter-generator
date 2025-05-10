# -*- coding: utf-8 -*-
"""
간단한 뉴스레터 생성 테스트
"""
from newsletter.chains import get_summarization_chain

# 테스트 데이터 생성
test_data = {
    "keywords": "인공지능, 머신러닝",
    "articles": [
        {
            "title": "구글, 새로운 AI 모델 출시",
            "url": "https://example.com/google-ai",
            "content": "구글이 새로운 AI 모델 'Gemini'를 출시했습니다. 이번 모델은 기존 모델보다 성능이 30% 향상되었으며, 다국어 처리 능력이 크게 개선되었습니다."
        },
        {
            "title": "애플, AI 기술 투자 확대",
            "url": "https://example.com/apple-ai",
            "content": "애플이 AI 기술 개발에 대한 투자를 확대한다고 발표했습니다. 향후 5년간 100억 달러를 투자할 계획이며, 음성 인식과 이미지 처리 분야에 집중할 예정입니다."
        }
    ]
}

# 뉴스레터 생성
try:
    chain = get_summarization_chain()
    result = chain.invoke(test_data)
    
    # 결과 파일에 저장
    with open("test_newsletter_result.html", "w", encoding="utf-8") as f:
        f.write(result)
    
    print("뉴스레터 생성 성공! test_newsletter_result.html 파일을 확인하세요.")
except Exception as e:
    print(f"뉴스레터 생성 중 오류 발생: {e}")
