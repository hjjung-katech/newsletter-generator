import os
from datetime import datetime
from pathlib import Path

import pytest

from newsletter import config
from newsletter.tools import (
    extract_common_theme_fallback,
    extract_common_theme_from_keywords,
)


def test_extract_common_theme_fallback():
    """키워드 공통 주제 추출 폴백 방식 테스트"""

    # 테스트 케이스 1: 단일 키워드
    keywords1 = ["인공지능"]
    result1 = extract_common_theme_fallback(keywords1)
    assert result1 == "인공지능"

    # 테스트 케이스 2: 2-3개 키워드
    keywords2 = ["인공지능", "머신러닝", "딥러닝"]
    result2 = extract_common_theme_fallback(keywords2)
    assert result2 == "인공지능, 머신러닝, 딥러닝"

    # 테스트 케이스 3: 4개 이상 키워드
    keywords3 = ["인공지능", "머신러닝", "딥러닝", "강화학습", "자연어처리"]
    result3 = extract_common_theme_fallback(keywords3)
    assert result3 == "인공지능 외 4개 분야"

    # 테스트 케이스 4: 문자열로 된 키워드
    keywords4 = "인공지능, 머신러닝, 딥러닝"
    result4 = extract_common_theme_fallback(keywords4)
    assert result4 == "인공지능, 머신러닝, 딥러닝"


def test_extract_common_theme_with_mock():
    """키워드 공통 주제 추출 메인 함수 테스트 (API 호출 없이)"""

    # 테스트를 위해 모든 API 키를 비활성화
    original_config_gemini_key = config.GEMINI_API_KEY
    original_config_openai_key = getattr(config, "OPENAI_API_KEY", None)
    original_config_anthropic_key = getattr(config, "ANTHROPIC_API_KEY", None)

    # config 모두 비활성화
    config.GEMINI_API_KEY = None
    config.OPENAI_API_KEY = None
    config.ANTHROPIC_API_KEY = None

    try:
        # 테스트 케이스: 여러 키워드
        keywords = ["인공지능", "머신러닝", "딥러닝"]
        result = extract_common_theme_from_keywords(keywords)

        # 폴백 함수의 결과와 일치해야 함
        expected = extract_common_theme_fallback(keywords)
        assert result == expected, f"Expected '{expected}', got '{result}'"

        # 단일 키워드 테스트 (API 없이)
        single_keyword = ["블록체인"]
        result_single = extract_common_theme_from_keywords(single_keyword)
        assert result_single == "블록체인"  # 단일 키워드는 그대로 반환

        # 문자열 키워드 테스트 (API 없이)
        keywords_str = "메타버스, NFT, 가상현실"
        result_str = extract_common_theme_from_keywords(keywords_str)
        expected_str = extract_common_theme_fallback(keywords_str)
        assert result_str == expected_str

    finally:
        # config 복원
        config.GEMINI_API_KEY = original_config_gemini_key
        config.OPENAI_API_KEY = original_config_openai_key
        config.ANTHROPIC_API_KEY = original_config_anthropic_key


if __name__ == "__main__":
    test_extract_common_theme_fallback()
    test_extract_common_theme_with_mock()
    print("All unit tests passed!")
