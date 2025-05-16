from newsletter.date_utils import extract_source_and_date, format_date_for_display


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
    test_source_and_date_extraction()
