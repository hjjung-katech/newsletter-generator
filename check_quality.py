#!/usr/bin/env python3
"""
Newsletter Generator 품질 관리 스크립트
- 코드 포맷팅과 테스트를 한번에 실행합니다.
"""
import os
import subprocess
import sys
from pathlib import Path


def check_black_installed():
    """Black이 설치되어 있는지 확인합니다."""
    try:
        subprocess.run(
            [sys.executable, "-m", "black", "--version"],
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Black이 설치되어 있지 않습니다. 설치를 시도합니다...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "black"], check=True
            )
            print("Black 설치 완료!")
            return True
        except subprocess.SubprocessError:
            print("오류: Black 설치에 실패했습니다. 'pip install black'으로 수동 설치해주세요.")
            return False


def format_code():
    """코드 포맷팅을 실행합니다."""
    print("\n1. 코드 포맷팅 실행 중...")

    # newsletter 패키지 포맷팅
    print("- newsletter 패키지 포맷팅...")
    subprocess.run([sys.executable, "-m", "black", "newsletter"], check=False)

    # tests 디렉토리 포맷팅
    print("- tests 디렉토리 포맷팅...")
    subprocess.run([sys.executable, "-m", "black", "tests"], check=False)

    print("✅ 코드 포맷팅 완료!")


def run_tests():
    """테스트를 실행합니다."""
    print("\n2. 테스트 실행 중...")
    # _backup 디렉토리 제외
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "--ignore=tests/_backup"], check=False
    )

    if result.returncode == 0:
        print("✅ 모든 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패!")

    return result.returncode


def run_specific_tests(test_name):
    """특정 테스트를 실행합니다."""
    if not test_name.startswith("test_"):
        test_name = f"test_{test_name}"
    if not test_name.endswith(".py"):
        test_name = f"{test_name}.py"

    test_path = Path("tests") / test_name

    if not test_path.exists():
        print(f"❌ 오류: {test_path} 파일을 찾을 수 없습니다.")
        return 1

    print(f"\n2. {test_name} 테스트 실행 중...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_path)], check=False
    )

    if result.returncode == 0:
        print(f"✅ {test_name} 테스트 통과!")
    else:
        print(f"❌ {test_name} 테스트 실패!")

    return result.returncode


def main():
    """메인 함수"""
    if not check_black_installed():
        return 1

    # 코드 포맷팅 실행
    format_code()

    # 인자가 있으면 특정 테스트 실행, 없으면 전체 테스트 실행
    if len(sys.argv) > 1:
        return run_specific_tests(sys.argv[1])
    else:
        return run_tests()


if __name__ == "__main__":
    sys.exit(main())
