#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
스케줄링 테스트 실행 스크립트

새로운 스케줄링 기능에 대한 포괄적인 테스트를 실행합니다.
CICD 환경에서 사용하기 적합하도록 설계되었습니다.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description, ignore_failure=False):
    """명령어 실행 및 결과 출력"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print("STDERR:")
        print(result.stderr)

    if result.returncode != 0:
        print(f"❌ Failed: {description}")
        if not ignore_failure:
            return False
        else:
            print("⚠️  Continuing despite failure...")
    else:
        print(f"✅ Passed: {description}")

    return True


def check_web_server():
    """웹 서버 실행 상태 확인"""
    try:
        import requests

        response = requests.get("http://localhost:8000/", timeout=3)
        return response.status_code == 200
    except:
        return False


def main():
    parser = argparse.ArgumentParser(description="Run scheduling tests")
    parser.add_argument(
        "--level",
        choices=["unit", "integration", "e2e", "compatibility", "all"],
        default="unit",
        help="Test level to run",
    )
    parser.add_argument(
        "--with-coverage", action="store_true", help="Run with coverage reporting"
    )
    parser.add_argument("--real-api", action="store_true", help="Enable real API tests")
    parser.add_argument(
        "--web-server-check",
        action="store_true",
        help="Check if web server is running for E2E tests",
    )

    args = parser.parse_args()

    # 프로젝트 루트로 이동
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    print("[START] Newsletter Scheduling Tests")
    print(f"Test Level: {args.level}")
    print(f"Project Root: {project_root}")
    print(f"Python: {sys.executable}")

    # 환경 설정
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)

    if args.real_api:
        env["RUN_REAL_API_TESTS"] = "1"
        env["RUN_INTEGRATION_TESTS"] = "1"
        print("[API] Real API tests enabled")
    else:
        env["RUN_MOCK_API_TESTS"] = "1"
        print("[API] Mock API tests enabled")

    # 기본 pytest 명령어
    base_cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short"]

    if args.with_coverage:
        base_cmd.extend(
            [
                "--cov=web.schedule_runner",
                "--cov=web.time_utils",
                "--cov-report=term-missing",
                "--cov-report=html:coverage_schedule",
            ]
        )

    success_count = 0
    total_tests = 0

    if args.level in ["unit", "all"]:
        print("\n[UNIT] Running Unit Tests...")
        total_tests += 1

        cmd = base_cmd + ["tests/unit_tests/test_schedule_time_sync.py", "-m", "unit"]

        if run_command(cmd, "Schedule Time Sync Unit Tests", env=env):
            success_count += 1

    if args.level in ["compatibility", "all"]:
        print("\n[COMPAT] Running Compatibility Tests...")
        total_tests += 1

        cmd = base_cmd + [
            "tests/test_schedule_compatibility.py",
            "-m",
            "unit or integration",
        ]

        if run_command(cmd, "Schedule Compatibility Tests", env=env):
            success_count += 1

    if args.level in ["integration", "all"]:
        print("\n[INTEG] Running Integration Tests...")
        total_tests += 1

        cmd = base_cmd + [
            "tests/integration/test_schedule_execution.py",
            "-m",
            "integration",
        ]

        if run_command(cmd, "Schedule Integration Tests", env=env):
            success_count += 1

    if args.level in ["e2e", "all"]:
        print("\n[E2E] Running E2E Tests...")

        if args.web_server_check and not check_web_server():
            print("[WARN] Web server not detected at http://localhost:8000")
            print("   Start server with: python web/app.py")
            print("   Skipping E2E tests...")
        else:
            total_tests += 1

            cmd = base_cmd + [
                "tests/e2e/test_schedule_e2e.py",
                "-m",
                "e2e and not manual",
            ]

            if run_command(cmd, "Schedule E2E Tests", env=env):
                success_count += 1

    # 결과 요약
    print(f"\n{'='*60}")
    print(f"[SUMMARY] TEST SUMMARY")
    print(f"{'='*60}")
    print(f"[OK] Passed: {success_count}/{total_tests}")
    print(f"[ERROR] Failed: {total_tests - success_count}")

    if args.with_coverage:
        print(f"[INFO] Coverage report: coverage_schedule/index.html")

    # 추가 정보
    if args.level == "all":
        print(f"\n[INFO] Manual Verification:")
        print(
            f"   • Run 'python -m pytest tests/e2e/test_schedule_e2e.py -m manual' for live tests"
        )
        print(f"   • Check web interface at http://localhost:8000")
        print(f"   • Monitor schedule execution logs")

    # 종료 코드 설정
    if success_count < total_tests:
        print(f"\n[ERROR] Some tests failed. Check output above.")
        return 1
    else:
        print(f"\n[SUCCESS] All tests passed!")
        return 0


def run_command(cmd, description, env=None, ignore_failure=False):
    """명령어 실행 및 결과 출력"""
    print(f"\n{'='*60}")
    print(f"[TEST] {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print("STDERR:")
        print(result.stderr)

    if result.returncode != 0:
        print(f"[ERROR] Failed: {description}")
        if not ignore_failure:
            return False
        else:
            print("[WARN] Continuing despite failure...")
    else:
        print(f"[OK] Passed: {description}")

    return True


if __name__ == "__main__":
    sys.exit(main())
