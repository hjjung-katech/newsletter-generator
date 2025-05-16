from newsletter.date_utils import (
    format_date_for_display,
    parse_date_string,
    standardize_date,
)
from datetime import datetime, timedelta


def test_date_utils():
    # Create a date that's older than 24 hours
    past_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

    test_cases = [
        ("2시간 전", "시간 전 포맷 (한국어)"),
        ("5분 전", "분 전 포맷 (한국어)"),
        ("2 hours ago", "hours ago 포맷 (영어)"),
        ("3 minutes ago", "minutes ago 포맷 (영어)"),
        ("21 hours ago", "21 hours ago 포맷 (영어)"),
        ("2024-05-01", "ISO 날짜 포맷 (YYYY-MM-DD)"),
        (past_date, "5일 전 날짜"),
        ("2024-05-01T12:34:56", "ISO 날짜+시간 포맷"),
        ("포쓰저널, 2시간 전", "소스와 상대적 시간"),
        ("서울경제, 21 hours ago", "영문 시간 표현과 소스"),
        ("네이버뉴스, 2024-05-01", "소스와 ISO 날짜"),
        ("날짜 없음", "날짜 없음 케이스"),
        ("", "빈 문자열"),
        (None, "None 값"),
    ]

    print("=" * 80)
    print("날짜 처리 유틸리티 테스트 결과:")
    print("=" * 80)

    print("\n1. 날짜 문자열 파싱 테스트 (parse_date_string):")
    print("-" * 60)
    for test_input, description in test_cases:
        result = parse_date_string(test_input)
        print(f"입력: '{test_input}' ({description})")
        print(f"결과: {result}")
        print()

    print("\n2. 날짜 표준화 테스트 (standardize_date):")
    print("-" * 60)
    for test_input, description in test_cases:
        result = standardize_date(test_input)
        print(f"입력: '{test_input}' ({description})")
        print(f"결과: '{result}'")
        print()

    print("\n3. 표시용 날짜 포맷팅 테스트 (format_date_for_display):")
    print("-" * 60)
    for test_input, description in test_cases:
        result = format_date_for_display(date_str=test_input)
        print(f"입력: '{test_input}' ({description})")
        print(f"결과: '{result}'")
        print()


if __name__ == "__main__":
    test_date_utils()
