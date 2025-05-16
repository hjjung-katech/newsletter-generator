"""
날짜 및 시간 유틸리티 테스트

이 모듈은 date_utils.py의 모든 주요 함수를 테스트합니다.
테스트 케이스에는 다양한 날짜 형식, 상대적 시간 표현, 소스와 날짜 분리 등이 포함됩니다.
"""

from newsletter.date_utils import (
    format_date_for_display,
    parse_date_string,
    standardize_date,
    extract_source_and_date,
)
from datetime import datetime, timedelta


def test_all_time_formats():
    """다양한 시간 형식이 올바르게 파싱되고 표준화되는지 테스트"""

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
        # 특수 케이스
        "날짜 없음",
        "",
        None,
    ]

    print("=" * 80)
    print("날짜 형식 파싱 테스트:")
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


def test_source_and_date_extraction():
    """소스와 날짜 분리 기능 테스트"""

    test_cases = [
        # 쉼표로 구분된 케이스 (소스, 날짜)
        "서울경제, 2시간 전",
        "한국경제, 3일 전",
        "뉴시스, 2 hours ago",
        "포쓰저널, 3 weeks ago",
        "브릿지경제, 1 month ago",
        "네이버뉴스, 2024-05-01",
        "조선일보, 2024-05-01T12:34:56Z",
        # 쉼표 없이 날짜 정보만 있는 케이스
        "2시간 전",
        "3 weeks ago",
        "2024-05-01",
        # 쉼표 없이 소스와 날짜가 공백으로 구분된 케이스
        "서울경제 2시간 전",
        "한겨레 3 weeks ago",
        "매일경제 2024-05-01",
        # 잘못된 형식 또는 날짜 없음
        "서울경제",
        "날짜 없음",
        "",
    ]

    print("=" * 80)
    print("소스와 날짜 분리 테스트:")
    print("=" * 80)

    for test_input in test_cases:
        source, date_str = extract_source_and_date(test_input)
        formatted_date = format_date_for_display(date_str=date_str) if date_str else ""

        print(f"입력: '{test_input}'")
        print(f"결과: 소스 = '{source}', 날짜 = '{date_str}'")
        print(f"표시용 날짜: '{formatted_date}'")
        print("-" * 60)


if __name__ == "__main__":
    test_all_time_formats()
    print("\n")
    test_source_and_date_extraction()
