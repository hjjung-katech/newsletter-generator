#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
로컬 CI 검증 스크립트
GitHub Actions CI에서 실행되는 모든 검사를 로컬에서 미리 실행합니다.
CI 실패를 방지하기 위한 종합적인 사전 검증 도구입니다.

사용법:
  python run_ci_checks.py          # 모든 검사 실행
  python run_ci_checks.py --fix    # 자동 수정 가능한 문제 해결
  python run_ci_checks.py --quick  # 빠른 검사만 (포맷팅, 린팅)
  python run_ci_checks.py --full   # 전체 검사 + 테스트
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

# Windows 한글 인코딩 설정
if sys.platform.startswith("win"):
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"
    # Windows 콘솔 UTF-8 설정
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


class Colors:
    """터미널 색상 코드"""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class CIChecker:
    """CI 검증 도구 클래스"""

    def __init__(self, fix_mode: bool = False, verbose: bool = False):
        self.fix_mode = fix_mode
        self.verbose = verbose
        self.results = []
        self.failed_checks = []

    def print_header(self, message: str):
        """헤더 출력"""
        print(f"\n{Colors.HEADER}{'=' * 70}{Colors.ENDC}")
        print(f"{Colors.HEADER}🔍 {message}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'=' * 70}{Colors.ENDC}")

    def print_status(self, check_name: str, passed: bool, message: str = ""):
        """상태 출력"""
        if passed:
            status = f"{Colors.OKGREEN}✅ PASS{Colors.ENDC}"
        else:
            status = f"{Colors.FAIL}❌ FAIL{Colors.ENDC}"
            self.failed_checks.append(check_name)

        print(f"  {status} - {check_name}")
        if message and (not passed or self.verbose):
            print(f"      {Colors.WARNING}{message}{Colors.ENDC}")

    def run_command(
        self, cmd: List[str], capture_output: bool = True
    ) -> Tuple[int, str, str]:
        """명령어 실행"""
        if self.verbose:
            print(f"    {Colors.OKCYAN}$ {' '.join(cmd)}{Colors.ENDC}")

        result = subprocess.run(cmd, capture_output=capture_output, text=True)
        return result.returncode, result.stdout, result.stderr

    def check_black(self) -> bool:
        """Black 포맷팅 검사"""
        self.print_header("Black 코드 포맷팅 검사")

        directories = ["newsletter", "tests", "web"]

        if self.fix_mode:
            # 자동 수정 모드
            cmd = [sys.executable, "-m", "black"] + directories
            returncode, stdout, stderr = self.run_command(cmd)
            if returncode == 0:
                self.print_status("Black 포맷팅", True, "코드가 포맷팅되었습니다")
                return True
            else:
                self.print_status("Black 포맷팅", False, stderr)
                return False
        else:
            # 검사만 수행
            cmd = [sys.executable, "-m", "black", "--check", "--diff"] + directories
            returncode, stdout, stderr = self.run_command(cmd)

            if returncode == 0:
                self.print_status("Black 포맷팅", True)
                return True
            else:
                self.print_status(
                    "Black 포맷팅",
                    False,
                    "포맷팅이 필요합니다. --fix 옵션으로 자동 수정 가능",
                )
                if self.verbose and stdout:
                    print(f"\n{Colors.WARNING}필요한 변경사항:{Colors.ENDC}")
                    print(stdout[:1000])  # 처음 1000자만 표시
                return False

    def check_isort(self) -> bool:
        """isort 임포트 정렬 검사"""
        self.print_header("isort 임포트 정렬 검사")

        directories = ["newsletter", "tests", "web"]

        if self.fix_mode:
            # 자동 수정 모드
            cmd = [sys.executable, "-m", "isort", "--profile", "black"] + directories
            returncode, stdout, stderr = self.run_command(cmd)
            if returncode == 0:
                self.print_status("isort 정렬", True, "임포트가 정렬되었습니다")
                return True
            else:
                self.print_status("isort 정렬", False, stderr)
                return False
        else:
            # 검사만 수행
            cmd = [
                sys.executable,
                "-m",
                "isort",
                "--check-only",
                "--diff",
                "--profile",
                "black",
            ] + directories
            returncode, stdout, stderr = self.run_command(cmd)

            if returncode == 0:
                self.print_status("isort 정렬", True)
                return True
            else:
                self.print_status(
                    "isort 정렬",
                    False,
                    "임포트 정렬이 필요합니다. --fix 옵션으로 자동 수정 가능",
                )
                return False

    def check_flake8(self) -> bool:
        """Flake8 린팅 검사"""
        self.print_header("Flake8 린팅 검사")

        directories = ["newsletter", "tests", "web"]
        cmd = (
            [sys.executable, "-m", "flake8"]
            + directories
            + ["--max-line-length=88", "--ignore=E203,W503"]
        )

        returncode, stdout, stderr = self.run_command(cmd)

        if returncode == 0:
            self.print_status("Flake8 린팅", True)
            return True
        else:
            self.print_status("Flake8 린팅", False, "린팅 오류가 발견되었습니다")
            if stdout:
                errors = stdout.split("\n")[:10]  # 처음 10개 오류만 표시
                for error in errors:
                    if error.strip():
                        print(f"      {Colors.WARNING}{error}{Colors.ENDC}")
                if len(stdout.split("\n")) > 10:
                    print(f"      {Colors.WARNING}... 그 외 오류들{Colors.ENDC}")
            return False

    def check_mypy(self) -> bool:
        """MyPy 타입 검사"""
        self.print_header("MyPy 타입 검사")

        cmd = [sys.executable, "-m", "mypy", "newsletter", "--ignore-missing-imports"]
        returncode, stdout, stderr = self.run_command(cmd)

        # mypy는 오류가 있어도 CI에서 계속 진행하므로 경고만 표시
        if returncode == 0:
            self.print_status("MyPy 타입 검사", True)
            return True
        else:
            self.print_status("MyPy 타입 검사", True, "타입 오류가 있지만 CI는 통과합니다 (경고)")
            if self.verbose and stdout:
                errors = stdout.split("\n")[:5]
                for error in errors:
                    if error.strip():
                        print(f"      {Colors.WARNING}{error}{Colors.ENDC}")
            return True  # CI에서는 실패하지 않음

    def check_bandit(self) -> bool:
        """Bandit 보안 검사"""
        self.print_header("Bandit 보안 검사")

        cmd = [
            sys.executable,
            "-m",
            "bandit",
            "-r",
            "newsletter",
            "web",
            "-f",
            "txt",
            "--skip",
            "B104,B110",
        ]
        returncode, stdout, stderr = self.run_command(cmd)

        # bandit도 CI에서 실패하지 않음
        if returncode == 0:
            self.print_status("Bandit 보안 검사", True)
        else:
            self.print_status("Bandit 보안 검사", True, "보안 이슈가 있지만 CI는 통과합니다 (경고)")
            if self.verbose and stdout:
                print(f"      {Colors.WARNING}보안 이슈를 검토하세요{Colors.ENDC}")
        return True

    def run_tests(self, quick: bool = False) -> bool:
        """테스트 실행"""
        self.print_header("단위 테스트 실행")

        if quick:
            print(f"  {Colors.WARNING}빠른 모드에서는 테스트를 건너뜁니다{Colors.ENDC}")
            return True

        # 환경 변수 설정
        env = os.environ.copy()
        env.update(
            {
                "MOCK_MODE": "true",
                "TESTING": "1",
                "OPENAI_API_KEY": "test-key",
                "SERPER_API_KEY": "test-key",
                "GEMINI_API_KEY": "test-key",
                "ANTHROPIC_API_KEY": "test-key",
                "POSTMARK_SERVER_TOKEN": "dummy-token",
                "EMAIL_SENDER": "test@example.com",
            }
        )

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-m",
            "unit",
            "--tb=short",
            "-q",
        ]

        print(f"  {Colors.OKCYAN}테스트 실행 중... (시간이 걸릴 수 있습니다){Colors.ENDC}")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode == 0:
            self.print_status("단위 테스트", True)
            return True
        else:
            self.print_status("단위 테스트", False, "테스트 실패")
            if result.stdout:
                print(f"\n{Colors.FAIL}테스트 출력:{Colors.ENDC}")
                print(result.stdout[-2000:])  # 마지막 2000자만 표시
            return False

    def check_pre_commit(self) -> bool:
        """Pre-commit hooks 설치 확인"""
        self.print_header("Pre-commit Hooks 확인")

        git_hooks_dir = Path(".git/hooks")
        pre_commit_hook = git_hooks_dir / "pre-commit"

        if pre_commit_hook.exists():
            self.print_status("Pre-commit hooks", True, "설치됨")
            return True
        else:
            self.print_status(
                "Pre-commit hooks",
                False,
                "설치되지 않음. 'pre-commit install' 실행 필요",
            )
            if self.fix_mode:
                print(f"  {Colors.OKCYAN}Pre-commit hooks 설치 중...{Colors.ENDC}")
                returncode, _, _ = self.run_command(["pre-commit", "install"])
                if returncode == 0:
                    print(f"  {Colors.OKGREEN}Pre-commit hooks 설치 완료!{Colors.ENDC}")
                    return True
            return False

    def run_all_checks(self, quick: bool = False, full: bool = False) -> bool:
        """모든 검사 실행"""
        print(f"\n{Colors.BOLD}🚀 로컬 CI 검증 시작{Colors.ENDC}")
        print(f"모드: {'자동 수정' if self.fix_mode else '검사만'}")

        start_time = time.time()

        # 필수 검사들
        checks = [
            ("Black 포맷팅", self.check_black),
            ("isort 정렬", self.check_isort),
            ("Flake8 린팅", self.check_flake8),
        ]

        # 추가 검사들
        if not quick:
            checks.extend(
                [
                    ("MyPy 타입 검사", self.check_mypy),
                    ("Bandit 보안 검사", self.check_bandit),
                ]
            )

        # 테스트는 full 모드에서만
        if full:
            checks.append(("단위 테스트", lambda: self.run_tests(quick=False)))

        # Pre-commit hooks 확인
        checks.append(("Pre-commit hooks", self.check_pre_commit))

        # 모든 검사 실행
        all_passed = True
        for name, check_func in checks:
            try:
                passed = check_func()
                if not passed:
                    all_passed = False
            except Exception as e:
                self.print_status(name, False, f"오류 발생: {e}")
                all_passed = False

        elapsed_time = time.time() - start_time

        # 최종 결과 출력
        print(f"\n{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
        print(f"{Colors.BOLD}📊 검증 결과 요약{Colors.ENDC}")
        print(f"{Colors.BOLD}{'=' * 70}{Colors.ENDC}")

        if all_passed:
            print(f"\n{Colors.OKGREEN}✅ 모든 검사를 통과했습니다!{Colors.ENDC}")
            print(f"{Colors.OKGREEN}   GitHub Actions CI도 통과할 것으로 예상됩니다.{Colors.ENDC}")
        else:
            print(f"\n{Colors.FAIL}❌ 일부 검사가 실패했습니다:{Colors.ENDC}")
            for check in self.failed_checks:
                print(f"   {Colors.FAIL}- {check}{Colors.ENDC}")

            if not self.fix_mode:
                print(
                    f"\n{Colors.WARNING}💡 팁: --fix 옵션으로 자동 수정 가능한 문제를 해결할 수 있습니다{Colors.ENDC}"
                )

        print(f"\n⏱️  실행 시간: {elapsed_time:.2f}초")

        return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="로컬 CI 검증 도구 - GitHub Actions 실패 방지",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python run_ci_checks.py              # 모든 검사 실행 (검사만)
  python run_ci_checks.py --fix        # 자동 수정 가능한 문제 해결
  python run_ci_checks.py --quick      # 빠른 검사 (포맷팅, 린팅만)
  python run_ci_checks.py --full       # 전체 검사 + 테스트
  python run_ci_checks.py --fix --full # 자동 수정 + 전체 검사

권장 워크플로우:
  1. 커밋 전: python run_ci_checks.py --fix
  2. 푸시 전: python run_ci_checks.py --full
  3. PR 전: python run_ci_checks.py --full --verbose
        """,
    )

    parser.add_argument(
        "--fix",
        action="store_true",
        help="자동으로 수정 가능한 문제 해결 (black, isort)",
    )
    parser.add_argument("--quick", action="store_true", help="빠른 검사만 실행 (포맷팅, 린팅)")
    parser.add_argument("--full", action="store_true", help="전체 검사 실행 (테스트 포함)")
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 출력")

    args = parser.parse_args()

    # 필요한 패키지 확인 (패키지명과 import명이 다른 경우 처리)
    package_imports = {
        "black": "black",
        "isort": "isort",
        "flake8": "flake8",
        "mypy": "mypy",
        "bandit": "bandit",
        "pytest": "pytest",
    }

    missing_packages = []
    for package, import_name in package_imports.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"{Colors.FAIL}❌ 필요한 패키지가 설치되지 않았습니다:{Colors.ENDC}")
        for pkg in missing_packages:
            print(f"   - {pkg}")
        print(f"\n다음 명령어로 설치하세요:")
        print(f"   pip install {' '.join(missing_packages)}")
        return 1

    # CI 검사 실행
    checker = CIChecker(fix_mode=args.fix, verbose=args.verbose)
    success = checker.run_all_checks(quick=args.quick, full=args.full)

    return 0 if success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}⏹️  검사가 중단되었습니다{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}💥 오류 발생: {e}{Colors.ENDC}")
        sys.exit(1)
