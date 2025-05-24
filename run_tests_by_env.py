#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
환경별 테스트 실행 스크립트
개발/CI/CD/통합 환경에 따라 적절한 테스트를 실행합니다.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """명령어 실행 및 결과 출력"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
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
        # 개발 환경: Mock API만 실행
        os.environ["RUN_REAL_API_TESTS"] = "0"
        os.environ["RUN_MOCK_API_TESTS"] = "1"

    elif env_type == "ci":
        # CI/CD 환경: Mock API + 단위 테스트
        os.environ["RUN_REAL_API_TESTS"] = "0"
        os.environ["RUN_MOCK_API_TESTS"] = "1"

    elif env_type == "integration":
        # 통합 환경: 실제 API 테스트 (API 키 필요)
        os.environ["RUN_REAL_API_TESTS"] = "1"
        os.environ["RUN_MOCK_API_TESTS"] = "1"

    elif env_type == "unit":
        # 단위 테스트만: API 테스트 모두 비활성화
        os.environ["RUN_REAL_API_TESTS"] = "0"
        os.environ["RUN_MOCK_API_TESTS"] = "0"


def main():
    parser = argparse.ArgumentParser(description="환경별 테스트 실행")
    parser.add_argument(
        "env",
        choices=["dev", "ci", "integration", "unit"],
        help="실행할 테스트 환경 (dev: 개발용, ci: CI/CD용, integration: 통합 테스트, unit: 단위 테스트만)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 출력 모드")
    parser.add_argument("--coverage", action="store_true", help="커버리지 리포트 생성")

    args = parser.parse_args()

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
        # 개발 환경: 빠른 피드백을 위한 핵심 테스트만
        cmd = pytest_cmd + [
            "tests/",
            "-m",
            "not real_api",
            "--tb=short",
            "--disable-warnings",
        ]
        return run_command(
            cmd, f"{args.env.upper()} 환경 테스트 (Mock API + 단위 테스트)"
        )

    elif args.env == "ci":
        # CI/CD 환경: 전체 검증 (실제 API 제외)
        cmd = pytest_cmd + ["tests/", "-m", "not real_api", "--tb=line"]
        return run_command(
            cmd, f"{args.env.upper()} 환경 테스트 (전체 검증, Real API 제외)"
        )

    elif args.env == "integration":
        # 통합 환경: 모든 테스트 실행
        print("⚠️  통합 테스트는 실제 API를 호출하여 할당량을 소모할 수 있습니다.")

        # API 키 확인
        api_keys = {
            "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
            "SERPER_API_KEY": os.getenv("SERPER_API_KEY"),
        }

        missing_keys = [key for key, value in api_keys.items() if not value]
        if missing_keys:
            print(f"❌ 누락된 API 키: {', '.join(missing_keys)}")
            print("   통합 테스트를 실행하려면 환경 변수에 API 키를 설정하세요.")
            return 1

        cmd = pytest_cmd + ["tests/", "--tb=short"]
        return run_command(
            cmd, f"{args.env.upper()} 환경 테스트 (전체 테스트, 실제 API 포함)"
        )

    elif args.env == "unit":
        # 단위 테스트만: API 호출 완전 배제
        cmd = pytest_cmd + [
            "tests/",
            "-m",
            "unit or (not api and not mock_api and not real_api)",
            "--tb=short",
            "--disable-warnings",
        ]
        return run_command(cmd, f"{args.env.upper()} 환경 테스트 (순수 단위 테스트만)")


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
