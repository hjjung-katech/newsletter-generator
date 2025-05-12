#!/usr/bin/env python3
# filepath: c:\Development\newsletter-generator\run_tests.py
"""
테스트 실행 자동화 스크립트
- 모든 테스트 또는 특정 테스트를 실행합니다.
"""
import os
import sys
import unittest
import argparse
import subprocess
from pathlib import Path


def run_code_formatting():
    """Black을 사용하여 코드를 포맷팅합니다."""
    print("코드 포맷팅 검사 실행 중...")
    
    # newsletter 패키지 포맷팅
    print("newsletter 패키지 포맷팅 중...")
    result_pkg = subprocess.run([sys.executable, "-m", "black", "newsletter"], check=False)
    
    # tests 디렉토리 포맷팅
    print("tests 디렉토리 포맷팅 중...")
    result_tests = subprocess.run([sys.executable, "-m", "black", "tests"], check=False)
    
    if result_pkg.returncode == 0 and result_tests.returncode == 0:
        print("✅ 코드 포맷팅 완료!")
        return True
    else:
        print("❌ 코드 포맷팅 중 오류가 발생했습니다.")
        return False


def run_all_tests():
    """tests 디렉토리의 모든 테스트를 실행합니다."""
    print("모든 테스트 실행 중...")
    test_path = Path(__file__).parent / "tests"
    return subprocess.run([sys.executable, "-m", "pytest", str(test_path)], check=False)


def run_specific_test(test_name):
    """지정된 테스트를 실행합니다."""
    if not test_name.startswith("test_"):
        test_name = f"test_{test_name}"
    if not test_name.endswith(".py"):
        test_name = f"{test_name}.py"
    
    test_path = Path(__file__).parent / "tests" / test_name
    
    if not test_path.exists():
        print(f"오류: 테스트 파일 {test_path}를 찾을 수 없습니다.")
        return None
    
    print(f"{test_name} 테스트 실행 중...")
    return subprocess.run([sys.executable, "-m", "pytest", str(test_path)], check=False)


def list_tests():
    """사용 가능한 테스트 파일 목록을 출력합니다."""
    test_dir = Path(__file__).parent / "tests"
    test_files = [f.name for f in test_dir.glob("test_*.py")]
    
    print("\n사용 가능한 테스트 파일:")
    for i, test_file in enumerate(sorted(test_files), 1):
        print(f"{i:2d}. {test_file}")
    print("")


def parse_arguments():
    """명령행 인수를 파싱합니다."""
    parser = argparse.ArgumentParser(description="뉴스레터 제너레이터 테스트 실행 도구")
    
    parser.add_argument(
        "--all", "-a", 
        action="store_true", 
        help="모든 테스트 실행"
    )
    parser.add_argument(
        "--list", "-l", 
        action="store_true", 
        help="사용 가능한 테스트 목록 출력"
    )
    parser.add_argument(
        "--test", "-t", 
        type=str, 
        help="실행할 특정 테스트 파일 이름 (예: serper_api 또는 test_serper_api.py)"
    )
    parser.add_argument(
        "--format", "-f",
        action="store_true",
        help="Black을 사용한 코드 포맷팅 검사 실행"
    )
    parser.add_argument(
        "--format-only",
        action="store_true",
        help="테스트를 실행하지 않고 코드 포맷팅만 수행"
    )
    
    return parser.parse_args()


def main():
    """메인 함수"""
    args = parse_arguments()
    
    # tests 디렉토리가 있는지 확인
    test_dir = Path(__file__).parent / "tests"
    if not test_dir.exists():
        print(f"오류: {test_dir} 디렉토리가 존재하지 않습니다.")
        return 1
    
    # 코드 포맷팅만 수행
    if args.format_only:
        format_result = run_code_formatting()
        return 0 if format_result else 1
    
    # 코드 포맷팅 검사 실행
    if args.format:
        format_result = run_code_formatting()
        if not format_result:
            return 1
    
    # 테스트 목록 출력
    if args.list:
        list_tests()
        return 0
    
    # 특정 테스트 실행
    if args.test:
        result = run_specific_test(args.test)
        return 0 if result and result.returncode == 0 else 1
    
    # 기본적으로 또는 --all이 지정된 경우 모든 테스트 실행
    if args.all or not (args.list or args.test or args.format_only):
        result = run_all_tests()
        return 0 if result and result.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
