#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 테스트 실행 스크립트
환경별 테스트 전략과 기존 디렉토리별 테스트 기능을 통합하여 제공합니다.

환경별 실행:
- dev: 개발용 빠른 피드백 (Mock API + 핵심 테스트)
- ci: CI/CD용 전체 검증 (Real API 제외)
- unit: 순수 단위 테스트만
- integration: 실제 API 포함 전체 검증

디렉토리별 실행:
- --api: API 테스트만
- --unit-tests: 단위 테스트만
- --specific: 특정 테스트 파일

유틸리티:
- --format: 코드 포맷팅
- --list: 테스트 목록 조회
"""

import os
import sys

# F-14: Windows 한글 인코딩 문제 해결 (강화된 버전)
if sys.platform.startswith("win"):
    import io
    import locale

    # UTF-8 인코딩 강제 설정
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"

    # 시스템 기본 인코딩을 UTF-8로 설정
    try:
        locale.setlocale(locale.LC_ALL, "ko_KR.UTF-8")
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, ".65001")  # Windows UTF-8 codepage
        except locale.Error:
            pass  # 설정할 수 없으면 무시

    # 표준 입출력 스트림을 UTF-8로 재구성
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    else:
        # 이전 Python 버전을 위한 fallback
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace"
        )

    # 디폴트 인코딩 설정
    if hasattr(sys, "_setdefaultencoding"):
        sys._setdefaultencoding("utf-8")

import argparse
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_command(cmd, description):
    """명령어 실행 및 결과 출력"""
    print(f"\n{'=' * 60}")
    print(f"🚀 {description}")
    print(f"{'=' * 60}")
    print(f"실행 명령: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, capture_output=False)

    if result.returncode == 0:
        print(f"\n✅ {description} 완료!")
    else:
        print(f"\n❌ {description} 실패! (exit code: {result.returncode})")

    return result.returncode


def setup_environment_variables(env_type):
    """환경 타입에 따른 환경 변수 설정"""

    if env_type == "dev":
        # 개발 환경: Mock API만 실행 (GitHub Actions 안전)
        os.environ["RUN_REAL_API_TESTS"] = "0"
        os.environ["RUN_MOCK_API_TESTS"] = "1"
        os.environ["RUN_INTEGRATION_TESTS"] = "0"
        os.environ["RUN_DEPLOYMENT_TESTS"] = "0"

    elif env_type == "ci":
        # CI/CD 환경: Mock API + 단위 테스트 (GitHub Actions 안전)
        os.environ["RUN_REAL_API_TESTS"] = "0"
        os.environ["RUN_MOCK_API_TESTS"] = "1"
        os.environ["RUN_INTEGRATION_TESTS"] = "0"
        os.environ["RUN_DEPLOYMENT_TESTS"] = "0"

    elif env_type == "integration":
        # 통합 환경: 실제 API 테스트 포함 (API 키 필요)
        os.environ["RUN_REAL_API_TESTS"] = "1"
        os.environ["RUN_MOCK_API_TESTS"] = "1"
        os.environ["RUN_INTEGRATION_TESTS"] = "1"
        os.environ["RUN_DEPLOYMENT_TESTS"] = "0"

    elif env_type == "unit":
        # 단위 테스트만: API 테스트 모두 비활성화
        os.environ["RUN_REAL_API_TESTS"] = "0"
        os.environ["RUN_MOCK_API_TESTS"] = "0"
        os.environ["RUN_INTEGRATION_TESTS"] = "0"
        os.environ["RUN_DEPLOYMENT_TESTS"] = "0"

    elif env_type == "deployment":
        # 배포 테스트만: 실제 서버 테스트
        os.environ["RUN_REAL_API_TESTS"] = "0"
        os.environ["RUN_MOCK_API_TESTS"] = "0"
        os.environ["RUN_INTEGRATION_TESTS"] = "0"
        os.environ["RUN_DEPLOYMENT_TESTS"] = "1"


def run_code_formatting():
    """Black과 isort를 사용하여 코드를 포맷팅합니다."""
    print("🎨 코드 포맷팅 검사 실행 중...")

    # isort로 import 정렬
    print("📋 import 정렬 중...")
    result_isort = subprocess.run(
        [sys.executable, "-m", "isort", "newsletter", "tests"], check=False
    )

    # newsletter 패키지 포맷팅
    print("📦 newsletter 패키지 포맷팅 중...")
    result_pkg = subprocess.run(
        [sys.executable, "-m", "black", "newsletter"], check=False
    )

    # tests 디렉토리 포맷팅
    print("🧪 tests 디렉토리 포맷팅 중...")
    result_tests = subprocess.run([sys.executable, "-m", "black", "tests"], check=False)

    if (
        result_isort.returncode == 0
        and result_pkg.returncode == 0
        and result_tests.returncode == 0
    ):
        print("✅ 코드 포맷팅 완료!")
        return True
    else:
        print("❌ 코드 포맷팅 중 오류가 발생했습니다.")
        return False


def list_tests(include_backup=False, include_api=False, include_unit=False):
    """사용 가능한 테스트 파일 목록을 출력합니다."""
    test_dir = PROJECT_ROOT / "tests"

    print("\n📋 테스트 파일 목록")
    print(f"{'=' * 60}")

    # 메인 폴더의 테스트 수집
    test_files = []
    for f in test_dir.glob("test_*.py"):
        if "_backup" not in str(f) and f.parent == test_dir:
            test_files.append(f)

    if test_files:
        print(f"\n📄 메인 테스트 ({len(test_files)}개):")
        for f in sorted(test_files):
            print(f"  - {f.name}")

    # API 테스트 수집
    if include_api:
        api_dir = test_dir / "api_tests"
        if api_dir.exists():
            api_files = list(api_dir.glob("test_*.py"))
            if api_files:
                print(f"\n🌐 API 테스트 ({len(api_files)}개):")
                for f in sorted(api_files):
                    print(f"  - api_tests/{f.name}")

    # 단위 테스트 수집
    if include_unit:
        unit_dir = test_dir / "unit_tests"
        if unit_dir.exists():
            unit_files = list(unit_dir.glob("test_*.py"))
            if unit_files:
                print(f"\n🔧 단위 테스트 ({len(unit_files)}개):")
                for f in sorted(unit_files):
                    print(f"  - unit_tests/{f.name}")

    # 백업 테스트 수집
    if include_backup:
        backup_dir = test_dir / "_backup"
        if backup_dir.exists():
            backup_files = list(backup_dir.glob("test_*.py"))
            if backup_files:
                print(f"\n📦 백업 테스트 ({len(backup_files)}개):")
                for f in sorted(backup_files):
                    print(f"  - _backup/{f.name}")

    print()


def run_specific_test(test_name, include_backup=False):
    """지정된 테스트를 실행합니다."""
    if not test_name.startswith("test_"):
        test_name = f"test_{test_name}"
    if not test_name.endswith(".py"):
        test_name = f"{test_name}.py"

    # 메인 tests 디렉토리에서 먼저 찾기
    test_path = PROJECT_ROOT / "tests" / test_name

    # 메인 디렉토리에 없고 백업 폴더 검색이 활성화되어 있다면
    if not test_path.exists() and include_backup:
        backup_path = PROJECT_ROOT / "tests" / "_backup" / test_name
        if backup_path.exists():
            test_path = backup_path

    # API 테스트에서 찾기
    if not test_path.exists():
        api_path = PROJECT_ROOT / "tests" / "api_tests" / test_name
        if api_path.exists():
            test_path = api_path

    # 단위 테스트에서 찾기
    if not test_path.exists():
        unit_path = PROJECT_ROOT / "tests" / "unit_tests" / test_name
        if unit_path.exists():
            test_path = unit_path

    if not test_path.exists():
        print(f"❌ 오류: 테스트 파일 {test_name}를 찾을 수 없습니다.")
        return 1

    cmd = [sys.executable, "-m", "pytest", str(test_path)]
    return run_command(cmd, f"특정 테스트 실행: {test_path.name}")


def run_api_tests():
    """API 키가 필요한 테스트만 별도로 실행합니다."""
    api_test_path = PROJECT_ROOT / "tests" / "api_tests"

    if not api_test_path.exists():
        print(f"❌ 오류: {api_test_path} 디렉토리가 존재하지 않습니다.")
        return 1

    test_files = list(api_test_path.glob("test_*.py"))

    if not test_files:
        print("📋 실행할 API 테스트 파일이 없습니다.")
        return 0

    # 테스트 파일 목록 출력
    print(f"🌐 실행할 API 테스트 파일 수: {len(test_files)}")
    for f in sorted(test_files):
        print(f"  - {f.relative_to(PROJECT_ROOT)}")

    cmd = [sys.executable, "-m", "pytest"] + [str(f) for f in test_files]
    return run_command(cmd, "API 테스트 실행")


def run_unit_tests():
    """단위 테스트만 별도로 실행합니다."""
    unit_test_path = PROJECT_ROOT / "tests" / "unit_tests"

    if not unit_test_path.exists():
        print(f"❌ 오류: {unit_test_path} 디렉토리가 존재하지 않습니다.")
        return 1

    test_files = list(unit_test_path.glob("test_*.py"))

    if not test_files:
        print("📋 실행할 단위 테스트 파일이 없습니다.")
        return 0

    # 테스트 파일 목록 출력
    print(f"🔧 실행할 단위 테스트 파일 수: {len(test_files)}")
    for f in sorted(test_files):
        print(f"  - {f.relative_to(PROJECT_ROOT)}")

    cmd = [sys.executable, "-m", "pytest"] + [str(f) for f in test_files]
    return run_command(cmd, "단위 테스트 실행")


def main():
    parser = argparse.ArgumentParser(
        description="통합 테스트 실행 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
환경별 실행 예시:
  python scripts/devtools/run_tests.py dev              # 개발용 빠른 테스트
  python scripts/devtools/run_tests.py ci               # CI/CD용 전체 검증
  python scripts/devtools/run_tests.py integration      # 실제 API 포함 검증

디렉토리별 실행 예시:
  python scripts/devtools/run_tests.py --api            # API 테스트만
  python scripts/devtools/run_tests.py --unit-tests     # 단위 테스트만

유틸리티 예시:
  python scripts/devtools/run_tests.py --format         # 코드 포맷팅
  python scripts/devtools/run_tests.py --list --all     # 모든 테스트 목록
        """,
    )

    # 환경별 실행
    parser.add_argument(
        "env",
        nargs="?",
        choices=["dev", "ci", "integration", "unit", "deployment"],
        help="실행할 테스트 환경 (dev: 개발용, ci: CI/CD용, integration: 통합 테스트, unit: 단위 테스트만, deployment: 배포 테스트)",
    )

    # 디렉토리별 실행 옵션
    parser.add_argument("--api", action="store_true", help="API 테스트만 실행")
    parser.add_argument("--unit-tests", action="store_true", help="단위 테스트만 실행")

    # 특정 테스트 실행
    parser.add_argument("--test", "-t", help="특정 테스트 파일 실행")

    # 유틸리티 옵션
    parser.add_argument("--format", action="store_true", help="코드 포맷팅 실행")
    parser.add_argument("--list", action="store_true", help="테스트 목록 출력")
    parser.add_argument("--all", action="store_true", help="모든 카테고리 포함 (--list와 함께 사용)")

    # 테스트 실행 옵션
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 출력 모드")
    parser.add_argument("--coverage", action="store_true", help="커버리지 리포트 생성")
    parser.add_argument("--include-backup", action="store_true", help="백업 테스트 포함")

    args = parser.parse_args()

    # 코드 포맷팅
    if args.format:
        return 0 if run_code_formatting() else 1

    # 테스트 목록 출력
    if args.list:
        list_tests(
            include_backup=args.include_backup or args.all,
            include_api=args.all,
            include_unit=args.all,
        )
        return 0

    # 특정 테스트 실행
    if args.test:
        return run_specific_test(args.test, args.include_backup)

    # 디렉토리별 테스트 실행
    if args.api:
        return run_api_tests()

    if args.unit_tests:
        return run_unit_tests()

    # 환경별 테스트 실행
    if not args.env:
        parser.print_help()
        print("\n💡 팁: 환경을 지정하거나 다른 옵션을 사용하세요.")
        return 1

    # 환경 변수 설정
    setup_environment_variables(args.env)

    print(f"🎯 테스트 환경: {args.env.upper()}")
    print(f"   - Real API Tests: {os.getenv('RUN_REAL_API_TESTS')}")
    print(f"   - Mock API Tests: {os.getenv('RUN_MOCK_API_TESTS')}")

    # 기본 pytest 옵션
    pytest_cmd = ["python", "-m", "pytest"]

    if args.verbose:
        pytest_cmd.append("-v")

    if args.coverage:
        pytest_cmd.extend(
            ["--cov=newsletter", "--cov-report=html", "--cov-report=term"]
        )

    # 환경별 테스트 실행
    if args.env == "dev":
        # 개발 환경: 빠른 피드백을 위한 핵심 테스트만 (E2E/배포/수동 제외)
        cmd = pytest_cmd + [
            "tests/",
            "-m",
            "not real_api and not e2e and not deployment and not manual",
            "--tb=short",
            "--disable-warnings",
        ]
        return run_command(
            cmd,
            f"{args.env.upper()} 환경 테스트 (Mock API + 단위 테스트, 서버 의존성 제외)",
        )

    elif args.env == "ci":
        # CI/CD 환경: 전체 검증 (실제 API 및 서버 의존성 제외)
        cmd = pytest_cmd + [
            "tests/",
            "-m",
            "not real_api and not e2e and not deployment and not manual",
            "--tb=line",
        ]
        return run_command(cmd, f"{args.env.upper()} 환경 테스트 (전체 검증, 서버 의존성 제외)")

    elif args.env == "integration":
        # 통합 환경: 모든 테스트 실행 (E2E 제외, 실제 API 포함)
        print("⚠️  통합 테스트는 실제 API를 호출하여 할당량을 소모할 수 있습니다.")

        # API 키 확인
        api_keys = {
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
            "SERPER_API_KEY": os.getenv("SERPER_API_KEY"),
        }

        missing_keys = [key for key, value in api_keys.items() if not value]
        if missing_keys:
            print(f"❌ 누락된 API 키: {', '.join(missing_keys)}")
            print("   통합 테스트를 실행하려면 환경 변수에 API 키를 설정하세요.")
            return 1

        cmd = pytest_cmd + ["tests/", "-m", "not e2e and not deployment", "--tb=short"]
        return run_command(
            cmd,
            f"{args.env.upper()} 환경 테스트 (전체 테스트, 실제 API 포함, E2E 제외)",
        )

    elif args.env == "unit":
        # 단위 테스트만: API 호출 완전 배제
        cmd = pytest_cmd + [
            "tests/",
            "-m",
            "unit or (not api and not mock_api and not real_api and not e2e and not deployment)",
            "--tb=short",
            "--disable-warnings",
        ]
        return run_command(cmd, f"{args.env.upper()} 환경 테스트 (순수 단위 테스트만)")

    elif args.env == "deployment":
        # 배포 테스트: 실제 서버 대상 smoke test
        test_base_url = os.getenv("TEST_BASE_URL")
        if not test_base_url:
            print("❌ TEST_BASE_URL 환경 변수가 설정되지 않았습니다.")
            print("   예: export TEST_BASE_URL=http://localhost:5000")
            return 1

        print(f"🎯 배포 테스트 대상 URL: {test_base_url}")
        cmd = pytest_cmd + [
            "tests/deployment/",
            "-m",
            "deployment",
            "--tb=short",
        ]
        return run_command(cmd, f"{args.env.upper()} 환경 테스트 (배포 서버 검증)")

    else:
        print(f"❌ 알 수 없는 환경: {args.env}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  테스트가 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 예상치 못한 오류가 발생했습니다: {e}")
        sys.exit(1)
