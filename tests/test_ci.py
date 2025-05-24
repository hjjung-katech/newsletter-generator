#!/usr/bin/env python3
"""
CI 테스트 스크립트
GitHub Actions에서 안정적으로 실행되는 테스트
"""

import sys
import os
import subprocess
from pathlib import Path


def run_command(cmd, description):
    """명령어를 실행하고 결과를 반환"""
    print(f"\n🔄 {description}")
    print(f"Running: {cmd}")

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=300  # 5분 타임아웃
        )

        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            if result.stdout:
                print(f"Output: {result.stdout}")
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(f"Error: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"💥 {description} - EXCEPTION: {e}")
        return False


def main():
    """메인 테스트 실행"""
    print("🚀 Starting CI Tests")

    # 작업 디렉토리 확인
    cwd = Path.cwd()
    print(f"Working directory: {cwd}")

    # 필요한 디렉토리 생성
    output_dir = cwd / "output"
    output_dir.mkdir(exist_ok=True)
    print(f"✅ Created output directory: {output_dir}")

    # 테스트 실행
    tests = [
        ("python -m pytest tests/test_minimal.py -v", "Minimal Tests"),
        ("black --check newsletter tests", "Code Formatting Check"),
    ]

    success_count = 0
    total_tests = len(tests)

    for cmd, description in tests:
        if run_command(cmd, description):
            success_count += 1

    # 결과 요약
    print(f"\n📊 Test Results: {success_count}/{total_tests} passed")

    if success_count == total_tests:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
