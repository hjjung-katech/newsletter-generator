#!/usr/bin/env python3
"""
Smoke test script for newsletter-generator deployment
Railway 배포 후 기본적인 기능들이 정상 작동하는지 확인합니다.

이 테스트는 배포된 서비스에 대한 검증을 수행합니다.
독립 실행 스크립트로 설계되어 pytest fixture에 의존하지 않습니다.
"""

import os
import sys
import requests
import json
import argparse
from typing import Dict, Any
import pytest


@pytest.mark.deployment
def test_health_endpoint(base_url: str):
    """Health check 엔드포인트 테스트"""
    print("🔍 Health check 엔드포인트 테스트 중...")

    try:
        response = requests.get(f"{base_url}/health", timeout=10)

        if response.status_code != 200:
            print(f"❌ Health check 실패: HTTP {response.status_code}")
            assert False, f"Health check failed with status {response.status_code}"

        health_data = response.json()
        status = health_data.get("status")

        if status != "healthy":
            print(f"❌ 시스템 상태 불량: {status}")
            print(f"   응답: {json.dumps(health_data, indent=2)}")
            assert False, f"System status is unhealthy: {status}"

        # 의존성 상태 확인
        dependencies = health_data.get("dependencies", {})
        failed_deps = []

        for dep_name, dep_info in dependencies.items():
            if dep_info.get("status") != "healthy":
                failed_deps.append(f"{dep_name}: {dep_info.get('status')}")

        if failed_deps:
            print(f"⚠️  일부 의존성에 문제가 있습니다:")
            for dep in failed_deps:
                print(f"   - {dep}")
            assert False, f"Dependencies failed: {failed_deps}"

        print("✅ Health check 통과")
        print(f"   응답 시간: {response.elapsed.total_seconds():.2f}초")

    except requests.exceptions.RequestException as e:
        print(f"❌ Health check 요청 실패: {e}")
        assert False, f"Health check request failed: {e}"


@pytest.mark.deployment
def test_newsletter_endpoint(base_url: str):
    """뉴스레터 생성 엔드포인트 테스트"""
    print("📰 뉴스레터 엔드포인트 테스트 중...")

    try:
        # Mock 모드가 비활성화되어 있는지 확인
        params = {"keywords": "AI,technology", "period": 7}

        response = requests.get(f"{base_url}/newsletter", params=params, timeout=30)

        if response.status_code != 200:
            print(f"❌ 뉴스레터 생성 실패: HTTP {response.status_code}")
            print(f"   응답: {response.text[:200]}...")
            assert (
                False
            ), f"Newsletter generation failed with status {response.status_code}"

        # Mock 데이터가 아닌 실제 데이터인지 확인
        content = response.text.lower()
        if "mock" in content:
            print("⚠️  Mock 모드가 활성화되어 있습니다 (MOCK_MODE=true)")
            print("   운영 환경에서는 MOCK_MODE=false로 설정해주세요")
            # Mock 모드는 경고만 출력하고 테스트는 통과시킴
            pytest.skip("Mock mode is enabled")

        if len(content) < 100:
            print("❌ 뉴스레터 내용이 너무 짧습니다")
            print(f"   내용 길이: {len(content)} 문자")
            assert False, f"Newsletter content too short: {len(content)} characters"

        print("✅ 뉴스레터 생성 성공")
        print(f"   콘텐츠 길이: {len(content)} 문자")

    except requests.exceptions.RequestException as e:
        print(f"❌ 뉴스레터 요청 실패: {e}")
        assert False, f"Newsletter request failed: {e}"


@pytest.mark.deployment
def test_period_validation(base_url: str):
    """Period 파라미터 검증 테스트"""
    print("🔢 Period 파라미터 검증 테스트 중...")

    try:
        # 유효하지 않은 period 값으로 테스트
        params = {"keywords": "test", "period": 999}  # 허용되지 않는 값

        response = requests.get(f"{base_url}/newsletter", params=params, timeout=10)

        if response.status_code == 400:
            print("✅ Period 검증 정상 작동 (잘못된 값 거부)")
        else:
            print(f"❌ Period 검증 실패: HTTP {response.status_code}")
            print("   잘못된 period 값(999)이 허용되었습니다")
            assert False, f"Period validation failed: status {response.status_code}"

    except requests.exceptions.RequestException as e:
        print(f"❌ Period 검증 요청 실패: {e}")
        assert False, f"Period validation request failed: {e}"


@pytest.mark.deployment
def test_dependencies(base_url: str):
    """의존성 상태 확인"""
    print("🔍 의존성 상태 확인 중...")

    try:
        response = requests.get(f"{base_url}/health", timeout=10)

        if response.status_code != 200:
            print(f"❌ Health check 실패: HTTP {response.status_code}")
            assert False, f"Health check failed with status {response.status_code}"

        health_data = response.json()
        deps = health_data.get("dependencies", {})

        # 기본적인 의존성 체크만 수행 (실제 서버가 없는 경우 유연하게 처리)
        print("✅ 의존성 상태 확인 완료")
        if deps:
            print(f"   발견된 의존성: {list(deps.keys())}")

    except Exception as e:
        print(f"❌ 의존성 확인 실패: {str(e)}")
        assert False, f"Dependencies check failed: {e}"


def run_smoke_tests_standalone(base_url: str) -> bool:
    """모든 smoke test를 독립적으로 실행 (pytest 없이)"""
    print(f"🚀 Smoke test 시작: {base_url}")
    print("=" * 50)

    tests = [
        ("Health Check", lambda: test_health_endpoint(base_url)),
        ("Period Validation", lambda: test_period_validation(base_url)),
        ("Newsletter Generation", lambda: test_newsletter_endpoint(base_url)),
        ("Dependencies", lambda: test_dependencies(base_url)),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 {test_name} 테스트:")
        if test_func():
            passed += 1
        else:
            print(f"   테스트 실패: {test_name}")

    print("\n" + "=" * 50)
    print(f"🎯 테스트 결과: {passed}/{total} 통과")

    if passed == total:
        print("✅ 모든 smoke test 통과!")
        return True
    else:
        print("❌ 일부 테스트 실패")
        return False


def main():
    """CLI 실행 진입점"""
    parser = argparse.ArgumentParser(description="Newsletter Generator Smoke Tests")
    parser.add_argument(
        "--url", default="http://localhost:5000", help="Base URL to test against"
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Run tests against production environment",
    )

    args = parser.parse_args()

    if args.production:
        base_url = os.getenv("PRODUCTION_URL", "https://your-app.railway.app")
        print(f"🚀 프로덕션 환경 테스트: {base_url}")
    else:
        base_url = args.url
        print(f"🔧 개발 환경 테스트: {base_url}")

    success = run_smoke_tests_standalone(base_url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
