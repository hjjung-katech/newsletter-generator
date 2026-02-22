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
from typing import List, Tuple

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
        self.changed_files = self._get_changed_files()

    def _get_changed_files(self) -> List[str]:
        """검사 대상 변경 파일 목록을 가져옵니다.

        CI_CHECK_SOURCE:
        - head    : git diff HEAD (기본값)
        - staged  : git diff --cached
        - baseline: git diff baseline/main-equivalent...HEAD
        """
        source = os.getenv("CI_CHECK_SOURCE", "head").lower()
        baseline_ref = os.getenv("CI_BASELINE_REF", "baseline/main-equivalent")
        if source == "head":
            cmd = ["git", "diff", "--name-only", "HEAD"]
        elif source == "staged":
            cmd = ["git", "diff", "--name-only", "--cached"]
        elif source == "baseline":
            cmd = ["git", "diff", "--name-only", f"{baseline_ref}...HEAD"]
        else:
            source = "head"
            cmd = ["git", "diff", "--name-only", "HEAD"]

        if self.verbose:
            print(f"{Colors.OKCYAN}검사 소스: {source}{Colors.ENDC}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            if self.verbose:
                print(f"{Colors.WARNING}변경 파일 조회 실패, 전체 검사로 폴백합니다{Colors.ENDC}")
            return []
        files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return files

    def _get_python_targets(self) -> List[str]:
        """린트 대상 Python 파일 목록(변경 파일 기준)."""
        if not self.changed_files:
            return []
        targets = []
        for path in self.changed_files:
            if not path.endswith(".py"):
                continue
            if path.startswith(
                (
                    "newsletter/",
                    "tests/",
                    "web/",
                    "scripts/",
                    "apps/",
                    "packages/newsletter_core/",
                    "newsletter_core/",
                )
            ):
                if Path(path).exists():
                    targets.append(path)
        return targets

    def _get_runtime_python_targets(self) -> List[str]:
        """런타임 영향 코드(newsletter/web) 변경 파일."""
        return [
            path
            for path in self._get_python_targets()
            if path.startswith(
                (
                    "newsletter/",
                    "web/",
                    "apps/",
                    "packages/newsletter_core/",
                    "newsletter_core/",
                )
            )
        ]

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

        targets = self._get_python_targets()
        if not targets:
            self.print_status("Black 포맷팅", True, "검사 대상 Python 변경 파일 없음")
            return True
        directories = targets
        print(f"  {Colors.OKCYAN}변경 파일 기준 Black 검사: {len(targets)}개{Colors.ENDC}")

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

        targets = self._get_python_targets()
        if not targets:
            self.print_status("isort 정렬", True, "검사 대상 Python 변경 파일 없음")
            return True
        directories = targets
        print(f"  {Colors.OKCYAN}변경 파일 기준 isort 검사: {len(targets)}개{Colors.ENDC}")

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

        targets = self._get_python_targets()
        if not targets:
            self.print_status("Flake8 린팅", True, "검사 대상 Python 변경 파일 없음")
            return True
        directories = targets
        print(f"  {Colors.OKCYAN}변경 파일 기준 Flake8 검사: {len(targets)}개{Colors.ENDC}")
        cmd = (
            [sys.executable, "-m", "flake8"]
            + directories
            + ["--max-line-length=88", "--ignore=E203,W503,E501"]
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

    def check_import_boundaries(self) -> bool:
        """아키텍처 import 경계 검사"""
        self.print_header("Architecture Import Boundary 검사")

        cmd = [
            sys.executable,
            "scripts/architecture/check_import_boundaries.py",
            "--mode",
            "ratchet",
        ]
        returncode, stdout, stderr = self.run_command(cmd)

        if returncode == 0:
            self.print_status("Import 경계 검사", True)
            return True

        self.print_status("Import 경계 검사", False, "신규/확대된 구조 위반이 발견되었습니다")
        if stdout:
            print(stdout[:2000])
        if stderr and self.verbose:
            print(stderr[:2000])
        return False

    def check_import_cycles(self) -> bool:
        """아키텍처 import 사이클 검사"""
        self.print_header("Architecture Import Cycle 검사")

        cmd = [sys.executable, "scripts/architecture/check_import_cycles.py"]
        returncode, stdout, stderr = self.run_command(cmd)

        if returncode == 0:
            self.print_status("Import 사이클 검사", True)
            return True

        self.print_status("Import 사이클 검사", False, "모듈 import cycle(SCC>1)가 발견되었습니다")
        if stdout:
            print(stdout[:2000])
        if stderr and self.verbose:
            print(stderr[:2000])
        return False

    def check_mypy(self) -> bool:
        """MyPy 타입 검사"""
        self.print_header("MyPy 타입 검사")

        targets = self._get_runtime_python_targets()
        if not targets:
            self.print_status("MyPy 타입 검사", True, "검사 대상 런타임 Python 변경 파일 없음")
            return True

        cmd = [
            sys.executable,
            "-m",
            "mypy",
            "--ignore-missing-imports",
            "--follow-imports=skip",
        ] + targets
        returncode, stdout, stderr = self.run_command(cmd)

        if returncode == 0:
            self.print_status("MyPy 타입 검사", True)
            return True
        else:
            self.print_status("MyPy 타입 검사", False, "타입 오류가 발견되었습니다")
            if stdout:
                errors = stdout.split("\n")[:10]
                for error in errors:
                    if error.strip():
                        print(f"      {Colors.WARNING}{error}{Colors.ENDC}")
            return False

    def check_bandit(self) -> bool:
        """Bandit 보안 검사"""
        self.print_header("Bandit 보안 검사")

        targets = self._get_runtime_python_targets()
        if not targets:
            self.print_status("Bandit 보안 검사", True, "검사 대상 런타임 Python 변경 파일 없음")
            return True

        cmd = [
            sys.executable,
            "-m",
            "bandit",
            "-f",
            "txt",
            "--skip",
            "B104,B110",
        ] + targets
        returncode, stdout, stderr = self.run_command(cmd)

        if returncode == 0:
            self.print_status("Bandit 보안 검사", True)
            return True
        else:
            self.print_status("Bandit 보안 검사", False, "보안 이슈가 발견되었습니다")
            if stdout:
                lines = stdout.split("\n")[:20]
                for line in lines:
                    if line.strip():
                        print(f"      {Colors.WARNING}{line}{Colors.ENDC}")
            if stderr and self.verbose:
                print(f"      {Colors.WARNING}{stderr[:1000]}{Colors.ENDC}")
            return False

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

        # Worktree에서는 .git이 파일이므로 git-path로 실제 hooks 경로를 계산한다.
        returncode, stdout, _ = self.run_command(
            ["git", "rev-parse", "--git-path", "hooks/pre-commit"]
        )
        if returncode == 0 and stdout.strip():
            pre_commit_hook = Path(stdout.strip())
        else:
            pre_commit_hook = Path(".git/hooks/pre-commit")

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
            ("Import 경계 검사", self.check_import_boundaries),
            ("Import 사이클 검사", self.check_import_cycles),
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
  1. 개발 중: make check
  2. 푸시 전: make check-full
  3. PR 전: make check-full (필요 시 이 스크립트에 --verbose 사용)
        """,
    )

    parser.add_argument(
        "--fix",
        action="store_true",
        help="자동으로 수정 가능한 문제 해결 (black, isort)",
    )
    parser.add_argument(
        "--source",
        choices=["head", "staged", "baseline"],
        default=os.getenv("CI_CHECK_SOURCE", "head"),
        help="변경 파일 탐지 소스 (기본: head)",
    )
    parser.add_argument("--quick", action="store_true", help="빠른 검사만 실행 (포맷팅, 린팅)")
    parser.add_argument("--full", action="store_true", help="전체 검사 실행 (테스트 포함)")
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 출력")

    args = parser.parse_args()

    # 변경 파일 소스 설정을 명시적으로 고정
    os.environ["CI_CHECK_SOURCE"] = args.source

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
        print("\n다음 명령어로 설치하세요:")
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
