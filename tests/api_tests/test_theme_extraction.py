import os
import pytest
from datetime import datetime
from pathlib import Path
from newsletter.tools import extract_common_theme_from_keywords
from newsletter import config


@pytest.mark.api
def test_extract_common_theme_with_api():
    """API를 사용한 키워드 공통 주제 추출 테스트 (API 키가 설정된 경우에만 실행)"""

    # API 키가 없으면 테스트를 건너뜁니다
    if not (os.environ.get("GOOGLE_API_KEY") or config.GEMINI_API_KEY):
        pytest.skip("No API key set")

    # 테스트 케이스: AI 관련 키워드
    keywords = ["인공지능", "머신러닝", "딥러닝"]
    result = extract_common_theme_from_keywords(keywords)

    # API 응답이므로 정확한 값을 예측할 수 없지만, 결과가 있어야 함
    assert result
    assert isinstance(result, str)
    assert len(result) > 0

    # 테스트 케이스: 반도체 관련 키워드
    keywords2 = ["반도체", "웨이퍼", "파운드리"]
    result2 = extract_common_theme_from_keywords(keywords2)

    assert result2
    assert isinstance(result2, str)
    assert len(result2) > 0

    # 테스트 케이스: 다양한 키워드 수 테스트
    # 단일 키워드
    single_keyword = ["블록체인"]
    result_single = extract_common_theme_from_keywords(single_keyword)
    assert result_single == "블록체인"  # 단일 키워드는 그대로 반환되어야 함

    # 문자열 형태의 키워드 목록
    keywords_str = "메타버스, NFT, 가상현실"
    result_str = extract_common_theme_from_keywords(keywords_str)
    assert result_str
    assert isinstance(result_str, str)

    print(f"AI 키워드 테마: {result}")
    print(f"반도체 키워드 테마: {result2}")
    print(f"문자열 키워드 테마: {result_str}")


if __name__ == "__main__":
    test_extract_common_theme_with_api()
