import os
import pytest
import re
from newsletter.tools import (
    sanitize_filename,
    get_filename_safe_theme,
    extract_common_theme_from_keywords,
)


def test_sanitize_filename():
    """파일명 정리 함수 테스트"""

    # 테스트 케이스 1: 특수 문자 제거
    test_str1 = "hello*world?"
    result1 = sanitize_filename(test_str1)
    assert "*" not in result1
    assert "?" not in result1
    assert result1 == "helloworld"

    # 테스트 케이스 2: 괄호 처리
    test_str2 = "AI(인공지능)_ML(머신러닝)"
    result2 = sanitize_filename(test_str2)
    assert "(" not in result2
    assert ")" not in result2
    assert "인공지능" in result2
    assert "머신러닝" in result2

    # 테스트 케이스 3: 공백 처리
    test_str3 = "hello world example"
    result3 = sanitize_filename(test_str3)
    assert " " not in result3
    assert result3 == "hello_world_example"

    # 테스트 케이스 4: 길이 제한
    long_str = "a" * 100
    result4 = sanitize_filename(long_str)
    assert len(result4) <= 50

    # 테스트 케이스 5: 긴 다단어 문자열
    long_words = "first_second_third_fourth_fifth_sixth_seventh_eighth_ninth_tenth"
    result5 = sanitize_filename(long_words)
    assert len(result5) <= 50
    assert result5.startswith("first_second_third")
    assert result5.endswith("_etc")

    # 테스트 케이스 6: 빈 문자열
    empty_str = ""
    result6 = sanitize_filename(empty_str)
    assert result6 == "unknown"

    # 테스트 케이스 7: 콤마 및 마침표 처리
    test_str7 = "hello, world. example"
    result7 = sanitize_filename(test_str7)
    assert "," not in result7
    assert "." not in result7


def test_get_filename_safe_theme():
    """파일명 안전한 테마 생성 함수 테스트"""

    # 테스트 케이스 1: 도메인이 있는 경우
    keywords1 = ["AI", "머신러닝", "딥러닝"]
    domain1 = "인공지능"
    result1 = get_filename_safe_theme(keywords1, domain1)
    assert result1 == "인공지능"

    # 테스트 케이스 2: 단일 키워드
    keywords2 = ["블록체인"]
    result2 = get_filename_safe_theme(keywords2)
    assert result2 == "블록체인"

    # 테스트 케이스 3: 여러 키워드 (extract_common_theme_from_keywords 모킹 필요)
    keywords3 = ["반도체", "메모리", "CPU"]

    # 원래 extract_common_theme_from_keywords 함수 저장
    original_func = extract_common_theme_from_keywords

    try:
        # extract_common_theme_from_keywords 함수를 모킹
        def mock_extract_theme(kw, api_key=None):
            return "반도체기술"

        # 모킹 함수로 교체
        import newsletter.tools

        newsletter.tools.extract_common_theme_from_keywords = mock_extract_theme

        result3 = get_filename_safe_theme(keywords3)
        assert result3 == "반도체기술"

    finally:
        # 테스트 후 원래 함수 복원
        newsletter.tools.extract_common_theme_from_keywords = original_func

    # 테스트 케이스 4: 문자열 키워드
    keywords4 = "AI, 머신러닝, 딥러닝"

    try:
        # extract_common_theme_from_keywords 함수를 모킹
        def mock_extract_theme2(kw, api_key=None):
            return "인공지능분야"

        # 모킹 함수로 교체
        import newsletter.tools

        newsletter.tools.extract_common_theme_from_keywords = mock_extract_theme2

        result4 = get_filename_safe_theme(keywords4)
        assert result4 == "인공지능분야"

    finally:
        # 테스트 후 원래 함수 복원
        newsletter.tools.extract_common_theme_from_keywords = original_func


def test_real_world_problematic_filenames():
    """실제 문제가 될 수 있는 파일명 케이스 테스트"""

    # 테스트 케이스 1: 괄호 및 특수문자가 많은 케이스
    problematic1 = "GenerativeAI_LargeLanguageModels(LLMs)_MultimodalLearning_FederatedLearning_ExplainableAI(XAI)"
    result1 = sanitize_filename(problematic1)
    assert "(" not in result1
    assert ")" not in result1
    assert len(result1) <= 50

    # 테스트 케이스 2: 너무 긴 파일명
    problematic2 = "전고체배터리_리튬황배터리_실리콘음극재_차세대배터리_배터리재활용_배터리안전성_고용량배터리_고속충전배터리_배터리관리시스템(BMS)_배터리수명연장"
    result2 = sanitize_filename(problematic2)
    assert len(result2) <= 50

    # 테스트 케이스 3: 파일명 제한 문자가 많은 케이스
    problematic3 = 'file:name*with?invalid"chars<>|\\and/slashes'
    result3 = sanitize_filename(problematic3)
    # Windows 파일 시스템에서 금지된 문자들이 없어야 함
    invalid_chars = [":", "*", "?", '"', "<", ">", "|", "\\", "/"]
    for char in invalid_chars:
        assert char not in result3


if __name__ == "__main__":
    test_sanitize_filename()
    test_get_filename_safe_theme()
    test_real_world_problematic_filenames()
    print("All filename generation tests passed!")
