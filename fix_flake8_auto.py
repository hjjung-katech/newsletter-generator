#!/usr/bin/env python3
"""
Flake8 오류 자동 수정 스크립트
자동으로 수정 가능한 Flake8 오류를 처리합니다.
"""

import os
import re
import sys
from pathlib import Path


def fix_unused_imports(file_path):
    """사용하지 않는 import 제거 (F401)"""
    # 이 작업은 위험할 수 있으므로 autoflake 사용 권장
    pass


def fix_long_lines(file_path):
    """긴 줄을 자동으로 줄바꿈 (E501)"""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    modified = False
    new_lines = []

    for line in lines:
        # 주석이나 문자열 내부가 아닌 경우만 처리
        if len(line.rstrip()) > 88:
            # f-string이나 긴 문자열을 포함한 경우
            if 'f"' in line or "f'" in line:
                # f-string을 여러 줄로 분할
                if '")' in line or "']" in line or '"}' in line:
                    # 문자열 연결 시도
                    indent = len(line) - len(line.lstrip())
                    if indent > 0:
                        # 적절한 위치에서 분할
                        parts = line.split(' f"')
                        if len(parts) > 1:
                            new_lines.append(parts[0] + "\n")
                            new_lines.append(" " * (indent + 4) + 'f"' + parts[1])
                            modified = True
                            continue
            new_lines.append(line)
        else:
            new_lines.append(line)

    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    return modified


def fix_whitespace_issues(file_path):
    """공백 관련 문제 수정 (E226, W291, W293)"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # E226: 연산자 주변 공백 추가
    content = re.sub(r"(\w)(\+|\-|\*|/)(\w)", r"\1 \2 \3", content)

    # W291: 줄 끝 공백 제거
    content = re.sub(r"[ \t]+$", "", content, flags=re.MULTILINE)

    # W293: 빈 줄의 공백 제거
    content = re.sub(r"^[ \t]+$", "", content, flags=re.MULTILINE)

    # E303: 너무 많은 빈 줄 (3개 이상을 2개로)
    content = re.sub(r"\n{4,}", "\n\n\n", content)

    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    return False


def fix_f_string_placeholders(file_path):
    """f-string placeholder 누락 수정 (F541)"""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    modified = False
    new_lines = []

    for line in lines:
        # f-string이지만 placeholder가 없는 경우
        if re.search(r'f["\']([^{]*)["\']', line):
            # f를 제거
            new_line = re.sub(r'f(["\'][^{]*["\'])', r"\1", line)
            if new_line != line:
                new_lines.append(new_line)
                modified = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    return modified


def main():
    """메인 함수"""
    # newsletter 디렉토리의 모든 Python 파일 처리
    newsletter_dir = Path("newsletter")

    if not newsletter_dir.exists():
        print("Error: newsletter directory not found")
        return 1

    fixed_files = 0
    total_files = 0

    for py_file in newsletter_dir.rglob("*.py"):
        total_files += 1
        file_modified = False

        # 각 수정 함수 실행
        if fix_whitespace_issues(py_file):
            file_modified = True

        if fix_f_string_placeholders(py_file):
            file_modified = True

        # fix_long_lines는 복잡하므로 일단 생략
        # if fix_long_lines(py_file):
        #     file_modified = True

        if file_modified:
            fixed_files += 1
            print(f"✅ Fixed: {py_file}")

    print(f"\n📊 Summary: Fixed {fixed_files}/{total_files} files")

    # autoflake 사용 권장 메시지
    print("\n💡 For unused imports (F401), use autoflake:")
    print("   pip install autoflake")
    print(
        "   autoflake --in-place --remove-unused-variables --remove-all-unused-imports -r newsletter"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
