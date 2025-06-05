#!/usr/bin/env python3
"""
Railway 배포 테스트 실행 스크립트

이 스크립트는 Railway 배포 환경에서 E2E 테스트를 실행합니다.
pytest 마커: @pytest.mark.deployment

사용법:
    python test_railway.py                    # 로컬 테스트
    python test_railway.py --url <URL>       # 특정 URL 테스트
    python test_railway.py --production      # Railway 프로덕션 테스트
"""

import os
import sys
import argparse
import subprocess
import pytest
from typing import Optional


@pytest.mark.deployment
def run_tests(
    base_url: Optional[str] = None, test_pattern: str = "test_railway_e2e.py"
):
    """테스트를 실행합니다."""

    # 환경변수 설정
    env = os.environ.copy()
    if base_url:
        env["TEST_BASE_URL"] = base_url
        print(f"🎯 Testing URL: {base_url}")
    else:
        print("🏠 Testing local environment (http://localhost:5000)")

    # pytest 명령 구성
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        f"tests/{test_pattern}",
        "-v",
        "--tb=short",
        "--color=yes",
    ]

    print(f"🚀 Running command: {' '.join(cmd)}")
    print("=" * 60)

    # 테스트 실행
    try:
        result = subprocess.run(cmd, env=env, cwd=os.getcwd())
        return result.returncode
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


def check_dependencies():
    """테스트 실행에 필요한 의존성을 확인합니다."""
    required_packages = ["pytest", "httpx", "pytest-asyncio"]

    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing.append(package)

    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print("📦 Install with: pip install " + " ".join(missing))
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description="Railway 배포 테스트 실행")
    parser.add_argument("--url", help="테스트할 URL (기본값: http://localhost:5000)")
    parser.add_argument(
        "--production",
        action="store_true",
        help="Railway 프로덕션 환경에서 테스트 (RAILWAY_PRODUCTION_URL 환경변수 사용)",
    )
    parser.add_argument(
        "--pattern",
        default="test_railway_e2e.py",
        help="테스트 파일 패턴 (기본값: test_railway_e2e.py)",
    )
    parser.add_argument(
        "--check-deps", action="store_true", help="의존성만 체크하고 종료"
    )

    args = parser.parse_args()

    print("🧪 Railway Newsletter Generator E2E Test Runner")
    print("=" * 60)

    # 의존성 체크
    if not check_dependencies():
        if args.check_deps:
            return 1
        print("💡 Try: cd web && pip install -r requirements.txt")
        return 1

    if args.check_deps:
        print("✅ All dependencies are installed")
        return 0

    # URL 결정
    test_url = None
    if args.production:
        test_url = os.getenv("RAILWAY_PRODUCTION_URL")
        if not test_url:
            print("❌ RAILWAY_PRODUCTION_URL environment variable not set")
            print("💡 Set it to your Railway app URL, e.g.:")
            print("   export RAILWAY_PRODUCTION_URL=https://your-app.railway.app")
            return 1
    elif args.url:
        test_url = args.url

    # 테스트 실행
    return run_tests(test_url, args.pattern)


if __name__ == "__main__":
    sys.exit(main())
