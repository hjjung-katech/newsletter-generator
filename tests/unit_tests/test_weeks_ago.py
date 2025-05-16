from newsletter.date_utils import (
    format_date_for_display,
    parse_date_string,
    standardize_date,
)
from datetime import datetime, timedelta


def test_weeks_ago_pattern():
    """'X weeks ago' 패턴이 올바르게 파싱되고 표준화되는지 테스트"""

    test_cases = [
        "2 weeks ago",
        "3 weeks ago",
        "1 week ago",
        "4 weeks ago",
        "브릿지경제, 3 weeks ago",
        "아시아경제, 2 weeks ago",
        "meconomynews.com, 3 weeks ago",
    ]

    print("=" * 80)
    print("'X weeks ago' 패턴 테스트:")
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
    test_weeks_ago_pattern()
