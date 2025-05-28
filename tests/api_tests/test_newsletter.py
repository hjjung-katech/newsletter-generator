# -*- coding: utf-8 -*-
"""
뉴스레터 생성 기능 통합 테스트
"""
import datetime
import os
import re
import sys
import unittest
from unittest.mock import MagicMock, patch

import pytest

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from newsletter.chains import get_summarization_chain

# 테스트 데이터
test_data = {
    "articles": [
        {
            "title": "구글, 새로운 머신러닝 알고리즘 발표",
            "url": "https://example.com/google-ml",
            "summary": "구글이 최신 머신러닝 기술을 공개했습니다.",
            "content": "구글은 최근 인공지능 컨퍼런스에서 새로운 머신러닝 알고리즘을 발표했습니다. 이 알고리즘은 기존 모델보다 30% 향상된 성능을 보여줍니다.",
            "source": "TechNews",
            "date": "2025-01-15",
        },
        {
            "title": "애플, AI 칩 개발 가속화",
            "url": "https://example.com/apple-ai-chip",
            "summary": "애플이 자체 AI 칩 개발에 박차를 가하고 있습니다.",
            "content": "애플은 자사의 AI 역량 강화를 위해 전용 칩 개발에 대규모 투자를 결정했습니다. 이는 경쟁사들과의 AI 경쟁에서 우위를 확보하기 위한 전략으로 보입니다.",
            "source": "AppleInsider",
            "date": "2025-01-14",
        },
    ],
    "keywords": ["머신러닝", "AI", "인공지능"],
}


@pytest.mark.api  # API 테스트로 표시
@pytest.mark.skip(reason="API quota limitation - requires external API calls")
@patch("newsletter.chains.compose_newsletter")
def test_newsletter_generation(mock_compose):
    """뉴스레터 생성 테스트 (API 할당량 문제로 스킵)"""
    print("===== 뉴스레터 생성 테스트 시작 =====")

    # compose_newsletter 결과 모킹
    mock_html = """<!DOCTYPE html>
<html>
<head><title>테스트 뉴스레터</title></head>
<body>
<h1>주간 산업 동향 뉴스 클리핑</h1>
<p>머신러닝 기술이 발전하고 있습니다.</p>
<p>구글의 새로운 발표가 있었습니다.</p>
</body>
</html>"""
    mock_compose.return_value = mock_html

    try:
        # 체인 생성
        print("1. Summarization 체인 생성 중...")
        chain = get_summarization_chain()
        print("✅ 체인 생성 성공")

        # 뉴스레터 생성
        print("\n2. 뉴스레터 생성 중...")
        result = chain.invoke(test_data)
        print(f"✅ 뉴스레터 생성 완료 (길이: {len(result)} 자)")

        # 마크다운 코드 블록 제거
        clean_result = result
        markdown_pattern = r"```(?:html)?\n([\s\S]*?)\n```"
        markdown_match = re.search(markdown_pattern, result)
        if markdown_match:
            clean_result = markdown_match.group(1)
            print(
                f"마크다운 코드 블록이 제거되었습니다. (이전 길이: {len(result)}, 새 길이: {len(clean_result)})"
            )

        # 결과 파일에 저장
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            output_dir, f"test_newsletter_result_{timestamp}.html"
        )
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(clean_result)

        # 검증
        print("\n3. 생성된 뉴스레터 검증 중...")

        # HTML 구조 확인
        assert clean_result.startswith(
            "<!DOCTYPE html>"
        ), "생성된 문서가 HTML이 아닙니다."
        print(f"✅ HTML 구조 확인")

        # 키워드 포함 확인
        assert (
            "머신러닝" in clean_result or "AI" in clean_result
        ), "생성된 문서에 키워드가 없습니다."
        print(f"✅ 키워드 포함 확인")

        # 기사 내용 포함 확인
        assert (
            "구글" in clean_result or "테스트" in clean_result
        ), "생성된 문서에 기사 내용이 없습니다."
        print(f"✅ 기사 내용 포함 확인")

        print(
            f"\n✅ 뉴스레터 생성 테스트 성공! 결과는 {output_path} 파일을 확인하세요."
        )
    except Exception as e:
        print(f"\n❌ 뉴스레터 생성 중 오류 발생: {e}")
        pytest.fail(f"뉴스레터 생성 중 오류 발생: {e}")


if __name__ == "__main__":
    test_newsletter_generation()
