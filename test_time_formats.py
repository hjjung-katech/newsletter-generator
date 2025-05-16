from newsletter.date_utils import (
    format_date_for_display,
    parse_date_string,
    standardize_date,
)
from datetime import datetime, timedelta


def test_all_time_formats():
    """모든 시간 형식이 올바르게 파싱되고 표준화되는지 테스트"""

    test_cases = [
        # 상대적 시간 표현 (한국어)
        "2시간 전",
        "5분 전",
        "3일 전",
        "어제",
        "오늘",
        # 상대적 시간 표현 (영어)
        "2 hours ago",
        "3 minutes ago",
        "1 day ago",
        "5 days ago",
        "1 week ago",
        "3 weeks ago",
        "1 month ago",
        "6 months ago",
        # ISO 형식
        "2024-05-01",
        "2024-05-01T12:34:56",
        "2024-05-01T12:34:56Z",
        # 소스와 시간 결합
        "포쓰저널, 2시간 전",
        "브릿지경제, 3 weeks ago",
        "경향신문, 1 month ago",
        "아시아경제, 2 months ago",
        "네이버뉴스, 2024-05-01",
    ]

    print("=" * 80)
    print("다양한 시간 형식 파싱 테스트:")
    print("=" * 80)

    print("\n1. 날짜 문자열 파싱 테스트 (parse_date_string):")
    print("-" * 60)
    for test_input in test_cases:
        result = parse_date_string(test_input)
        print(f"입력: '{test_input}'")
        print(f"결과: {result}")
        print()

    print("\n2. 날짜 표준화 테스트 (standardize_date):")
    print("-" * 60)
    for test_input in test_cases:
        result = standardize_date(test_input)
        print(f"입력: '{test_input}'")
        print(f"결과: '{result}'")
        print()

    print("\n3. 표시용 날짜 포맷팅 테스트 (format_date_for_display):")
    print("-" * 60)
    for test_input in test_cases:
        result = format_date_for_display(date_str=test_input)
        print(f"입력: '{test_input}'")
        print(f"결과: '{result}'")
        print()


if __name__ == "__main__":
    test_all_time_formats()
