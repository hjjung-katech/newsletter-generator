#!/usr/bin/env python3
# filepath: c:\Development\newsletter-generator\run_tests.py
"""
테스트 실행 자동화 스크립트
- 모든 테스트 또는 특정 테스트를 실행합니다.
- 기본적으로 _backup 및 하위 폴더의 테스트는 무시합니다.
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
    result_pkg = subprocess.run(
        [sys.executable, "-m", "black", "newsletter"], check=False
    )

    # tests 디렉토리 포맷팅
    print("tests 디렉토리 포맷팅 중...")
    result_tests = subprocess.run([sys.executable, "-m", "black", "tests"], check=False)

    if result_pkg.returncode == 0 and result_tests.returncode == 0:
        print("✅ 코드 포맷팅 완료!")
        return True
    else:
        print("❌ 코드 포맷팅 중 오류가 발생했습니다.")
        return False


def run_api_tests():
    """
    API 키가 필요한 테스트만 별도로 실행합니다.
    tests/api_tests 디렉토리의 모든 테스트를 실행합니다.
    """
    print("API 테스트만 실행 중...")
    api_test_path = Path(__file__).parent / "tests" / "api_tests"

    if not api_test_path.exists():
        print(f"오류: {api_test_path} 디렉토리가 존재하지 않습니다.")
        return None

    test_files = list(api_test_path.glob("test_*.py"))

    if not test_files:
        print("실행할 API 테스트 파일이 없습니다.")
        return None

    # 테스트 파일 목록 출력
    print(f"실행할 API 테스트 파일 수: {len(test_files)}")
    for f in sorted(test_files):
        print(f"  - {f.relative_to(Path(__file__).parent)}")

    cmd = [sys.executable, "-m", "pytest"] + [str(f) for f in test_files]
    return subprocess.run(cmd, check=False)


def run_all_tests(include_backup=False):
    """
    tests 디렉토리의 모든 테스트를 실행합니다.

    Args:
        include_backup (bool): _backup 폴더와 하위 폴더의 테스트를 포함할지 여부
    """
    if include_backup:
        print("모든 테스트 실행 중 (백업 폴더 포함)...")
        test_path = Path(__file__).parent / "tests"
        return subprocess.run(
            [sys.executable, "-m", "pytest", str(test_path)], check=False
        )
    else:
        print("메인 테스트만 실행 중 (백업 폴더 제외)...")
        test_path = Path(__file__).parent / "tests"

        # 메인 폴더의 테스트 파일만 수집 (_backup 폴더 제외)
        test_files = []
        for f in test_path.glob("test_*.py"):
            if "_backup" not in str(f) and f.parent == test_path:
                test_files.append(str(f))

        if not test_files:
            print("실행할 테스트 파일이 없습니다.")
            return None

        # 테스트 파일 목록 출력
        print(f"실행할 테스트 파일 수: {len(test_files)}")

        # 각 테스트 파일을 별도로 실행하도록 명령 구성
        cmd = [sys.executable, "-m", "pytest"] + test_files
        return subprocess.run(cmd, check=False)


def run_specific_test(test_name, include_backup=False):
    """
    지정된 테스트를 실행합니다.

    Args:
        test_name (str): 실행할 테스트 파일 이름
        include_backup (bool): 백업 폴더에서도 테스트를 찾을지 여부
    """
    if not test_name.startswith("test_"):
        test_name = f"test_{test_name}"
    if not test_name.endswith(".py"):
        test_name = f"{test_name}.py"

    # 메인 tests 디렉토리에서 먼저 찾기
    test_path = Path(__file__).parent / "tests" / test_name

    # 메인 디렉토리에 없고 백업 폴더 검색이 활성화되어 있다면
    if not test_path.exists() and include_backup:
        backup_path = Path(__file__).parent / "tests" / "_backup" / test_name
        if backup_path.exists():
            test_path = backup_path

    if not test_path.exists():
        print(f"오류: 테스트 파일 {test_name}를 찾을 수 없습니다.")
        return None

    print(f"{test_path} 테스트 실행 중...")
    return subprocess.run([sys.executable, "-m", "pytest", str(test_path)], check=False)


def list_tests(include_backup=False, include_api=False):
    """
    사용 가능한 테스트 파일 목록을 출력합니다.

    Args:
        include_backup (bool): 백업 폴더의 테스트도 포함할지 여부
        include_api (bool): API 테스트도 포함할지 여부
    """
    test_dir = Path(__file__).parent / "tests"

    # 메인 폴더의 테스트만 수집
    test_files = []
    for f in test_dir.glob("test_*.py"):
        if "_backup" not in str(f) and f.parent == test_dir:
            test_files.append(f)

    # 백업 폴더 포함 옵션이 활성화된 경우 백업 폴더의 테스트도 수집
    backup_files = []
    if include_backup:
        backup_dir = test_dir / "_backup"
        if backup_dir.exists():
            backup_files = list(backup_dir.glob("test_*.py"))

    # API 테스트 수집
    api_files = []
    if include_api:
        api_dir = test_dir / "api_tests"
        if api_dir.exists():
            api_files = list(api_dir.glob("test_*.py"))

    print("\n사용 가능한 테스트 파일:")
    print("\n[메인 테스트]")
    for i, test_file in enumerate(sorted(test_files), 1):
        print(f"{i:2d}. {test_file.name}")

    if include_api and api_files:
        print("\n[API 테스트]")
        for i, test_file in enumerate(sorted(api_files), 1):
            print(f"{i:2d}. api_tests/{test_file.name}")

    if include_backup and backup_files:
        print("\n[백업 테스트]")
        for i, test_file in enumerate(sorted(backup_files), 1):
            print(f"{i:2d}. _backup/{test_file.name}")

    print("")


def parse_arguments():
    """명령행 인수를 파싱합니다."""
    parser = argparse.ArgumentParser(description="뉴스레터 제너레이터 테스트 실행 도구")

    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="모든 메인 테스트 실행 (_backup 폴더 제외)",
    )
    parser.add_argument(
        "--full",
        "--include-all",
        action="store_true",
        help="모든 테스트 실행 (_backup 폴더 포함)",
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="API 키가 필요한 테스트만 실행 (tests/api_tests 디렉토리)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="사용 가능한 테스트 목록 출력 (기본: 메인 테스트만)",
    )
    parser.add_argument(
        "--list-all",
        action="store_true",
        help="모든 테스트 목록 출력 (백업 테스트 포함)",
    )
    parser.add_argument("--list-api", action="store_true", help="API 테스트 목록 출력")
    parser.add_argument(
        "--test",
        "-t",
        type=str,
        help="실행할 특정 테스트 파일 이름 (예: serper_api 또는 test_serper_api.py)",
    )
    parser.add_argument(
        "--include-backup",
        action="store_true",
        help="--test 옵션 사용 시 백업 폴더에서도 테스트 파일 검색",
    )
    parser.add_argument(
        "--format",
        "-f",
        action="store_true",
        help="Black을 사용한 코드 포맷팅 검사 실행",
    )
    parser.add_argument(
        "--format-only",
        action="store_true",
        help="테스트를 실행하지 않고 코드 포맷팅만 수행",
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
    if args.list or args.list_all or args.list_api:
        list_tests(
            include_backup=args.list_all, include_api=args.list_api or args.list_all
        )
        return 0

    # 특정 테스트 실행
    if args.test:
        result = run_specific_test(args.test, include_backup=args.include_backup)
        return 0 if result and result.returncode == 0 else 1

    # API 테스트만 실행
    if args.api:
        result = run_api_tests()
        return 0 if result and result.returncode == 0 else 1

    # 모든 테스트 실행 (백업 포함 여부에 따라)
    if args.full:
        # 백업 폴더 포함한 모든 테스트 실행
        result = run_all_tests(include_backup=True)
        return 0 if result and result.returncode == 0 else 1
    elif args.all or not (
        args.list
        or args.list_all
        or args.test
        or args.format_only
        or args.list_api
        or args.api
    ):
        # 기본 동작: 메인 테스트만 실행
        result = run_all_tests(include_backup=False)
        return 0 if result and result.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
