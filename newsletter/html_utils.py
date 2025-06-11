"""
HTML Utility Functions
순수한 HTML 처리 함수들을 포함합니다. 외부 AI 의존성이 없습니다.
"""

import re


def clean_html_markers(html_content: str) -> str:
    """
    Removes code markup (```html, ```, ``` etc.) from the beginning and end of an HTML string,
    as well as file path comments.

    This handles various patterns including:
    - ```html at the beginning
    - ``` at the end
    - ```lang syntax (for any language identifier)
    - Filepath comments
    - Multiple backticks (like ````html)
    """
    if not html_content:
        return ""

    content = html_content

    # 1. 파일 경로 주석 제거 (존재하는 경우)
    # 패턴: 문자열 시작의 공백 + "<!-- filepath: 내용 -->" + 뒤따르는 공백(개행 포함)
    comment_pattern = r"^\s*<!--\s*filepath:.*?-->\s*"
    match_comment = re.match(comment_pattern, content, flags=re.IGNORECASE | re.DOTALL)
    if match_comment:
        # 주석 및 주석 뒤 공백 이후의 문자열을 가져옴
        content = content[match_comment.end() :]

    # 2. 시작 부분의 코드 마커 제거 (다양한 언어 식별자 및 여러 개의 백틱 처리)
    # 더 일반적인 패턴: (새로운) 문자열 시작의 공백 + 하나 이상의 백틱 + 선택적 언어 식별자 + 뒤따르는 공백(개행 포함)
    start_marker_pattern = r"^\s*(`{1,4})([a-zA-Z]*)\s*"
    match_start_marker = re.match(start_marker_pattern, content)
    if match_start_marker:
        # 코드 마커 및 마커 뒤 공백 이후의 문자열을 가져옴
        content = content[match_start_marker.end() :]

    # 3. 끝부분 코드 마커 제거 (여러 개의 백틱 처리)
    content = content.rstrip()  # 먼저 오른쪽 끝 공백 제거
    end_marker_pattern = r"`{1,4}\s*$"
    match_end_marker = re.search(end_marker_pattern, content)
    if match_end_marker:
        content = content[: match_end_marker.start()]

    # 최종적으로 앞뒤 공백 제거
    return content.strip()
