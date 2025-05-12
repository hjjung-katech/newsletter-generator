# -*- coding: utf-8 -*-
"""
HTML 템플릿 로딩 기능 테스트
"""
from newsletter.chains import load_html_template, HTML_TEMPLATE
import sys


def test_template_loading():
    """HTML 템플릿 로딩을 테스트합니다."""
    # 직접 함수에서 템플릿 로드
    print("===== HTML 템플릿 로드 테스트 시작 =====")
    template = load_html_template()
    print(f"직접 로드한 HTML 템플릿 (일부):\n{template[:150]}\n...")

    # 미리 로드된 전역 변수 확인
    print(f"\n미리 로드된 HTML_TEMPLATE (일부):\n{HTML_TEMPLATE[:150]}\n...")

    # 템플릿에 Jinja2 구문이 포함되어 있는지 확인
    if "{{" in template and "{%" in template:
        print("\n✅ 템플릿에 Jinja2 구문이 포함되어 있습니다.")
    else:
        print("\n❌ 템플릿에 Jinja2 구문이 없습니다!")
        return False

    print("\n✅ 템플릿 로드 테스트 성공!")
    return True


if __name__ == "__main__":
    success = test_template_loading()
    print(f"\n테스트 결과: {'성공' if success else '실패'}")
    sys.exit(0 if success else 1)
