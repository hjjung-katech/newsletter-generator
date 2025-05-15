#!/usr/bin/env python
"""
Newsletter Generator - 테스트 스크립트
이 스크립트는 newsletter 모듈의 개선된 체인 파이프라인을 테스트합니다.
"""

import os
import sys
from dotenv import load_dotenv
from newsletter.chains import get_newsletter_chain

# .env 파일 로드
load_dotenv()

# 테스트 데이터
test_data = {
    "keywords": "전기차, 배터리 기술",
    "articles": [
        {
            "title": "테슬라, 새로운 배터리 기술로 주행거리 20% 향상",
            "url": "https://example.com/tesla-battery",
            "content": "테슬라가 새로운 4680 배터리 셀을 도입해 전기차 주행거리를 20% 이상 향상시킨다고 발표했습니다. 이 배터리는 에너지 밀도가 높고 생산 비용도 절감된다는 특징이 있습니다. 실리콘 음극재와 새로운 양극재 기술을 적용해 충전 속도도 크게 개선되었습니다.",
            "source": "테크 뉴스",
            "date": "2025-05-15",
        },
        {
            "title": "현대자동차, 고체 전해질 배터리 상용화 계획 발표",
            "url": "https://example.com/hyundai-solid-state",
            "content": "현대자동차가 2027년까지 고체 전해질 배터리를 탑재한 전기차 출시 계획을 발표했습니다. 이 배터리는 기존 리튬이온 배터리보다 안전성이 높고 에너지 밀도도 30% 이상 향상될 것으로 기대됩니다. 삼성SDI와 공동으로 개발 중이며, 충전 속도와 내구성에서도 큰 개선이 이루어질 전망입니다.",
            "source": "자동차 경제",
            "date": "2025-05-14",
        },
        {
            "title": "중국 BYD, 전기차 시장 점유율 급증",
            "url": "https://example.com/byd-market-share",
            "content": "중국 전기차 제조업체 BYD가 글로벌 전기차 시장에서 점유율을 크게 늘리고 있습니다. 1분기 판매량은 전년 대비 89% 증가했으며, 특히 유럽 시장에서 급성장하고 있습니다. 저렴한 가격과 긴 주행거리, 다양한 모델 라인업이 인기 요인으로 분석됩니다.",
            "source": "국제 비즈니스",
            "date": "2025-05-12",
        },
        {
            "title": "미국, 전기차 배터리 생산 투자 확대",
            "url": "https://example.com/us-battery-investment",
            "content": "미국 정부가 전기차 배터리 국내 생산 강화를 위해 100억 달러 규모의 투자 계획을 발표했습니다. 이를 통해 배터리 공급망 안정화와 중국 의존도 감소를 목표로 하고 있습니다. GM, 포드 등 미국 자동차 제조업체들과 협력하여 배터리 생산 시설을 미국 내에 확충할 예정입니다.",
            "source": "정책 뉴스",
            "date": "2025-05-10",
        },
        {
            "title": "새로운 리튬 채굴 기술, 배터리 원자재 수급 개선 기대",
            "url": "https://example.com/lithium-extraction",
            "content": "친환경적인 새로운 리튬 채굴 기술이 개발되어 배터리 원자재 수급 개선이 기대됩니다. 직접 리튬 추출(DLE) 기술을 활용해 물 사용량을 90% 줄이고 채굴 속도도 기존 방식보다 4배 빠르다는 특징이 있습니다. 이를 통해 전기차 배터리 생산 비용 절감과 안정적인 공급망 구축이 가능할 것으로 전망됩니다.",
            "source": "과학 기술",
            "date": "2025-05-08",
        },
    ],
}


def main():
    """메인 테스트 함수"""
    try:
        # 뉴스레터 생성 체인 가져오기
        chain = get_newsletter_chain()

        # 체인 실행
        print("뉴스레터 생성 중...")
        result = chain.invoke(test_data)

        # 결과 저장
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "newsletter_test.html")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)

        print(f"뉴스레터가 성공적으로 생성되었습니다. 파일: {output_path}")
        return 0

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
