"""
Minimal version of tools.py with only clean_html_markers function
"""

import re


def clean_html_markers(html_content: str) -> str:
    """
    Removes ```html and ``` markers and filepath comments from the beginning and end of an HTML string.
    """
    content = html_content

    # 1. 파일 경로 주석 제거 (존재하는 경우)
    # 패턴: 문자열 시작의 공백 + "<!-- filepath: 내용 -->" + 뒤따르는 공백(개행 포함)
    comment_pattern = r"^\s*<!--\s*filepath:.*?-->\s*"
    match_comment = re.match(comment_pattern, content, flags=re.IGNORECASE | re.DOTALL)
    if match_comment:
        # 주석 및 주석 뒤 공백 이후의 문자열을 가져옴
        content = content[match_comment.end() :]

    # 2. HTML 시작 마커 제거 (존재하는 경우)
    # 패턴: (새로운) 문자열 시작의 공백 + "```html" + 뒤따르는 공백(개행 포함)
    html_marker_pattern = r"^\s*```html\s*"
    match_html_marker = re.match(
        html_marker_pattern, content
    )  # ```html은 대소문자 구분 없음 불필요
    if match_html_marker:
        # HTML 마커 및 마커 뒤 공백 이후의 문자열을 가져옴
        content = content[match_html_marker.end() :]

    # 3. 끝부분 ``` 마커 제거
    content = content.rstrip()  # 먼저 오른쪽 끝 공백 제거
    if content.endswith("```"):
        content = content[: -len("```")]

    # 최종적으로 앞뒤 공백 제거
    return content.strip()
