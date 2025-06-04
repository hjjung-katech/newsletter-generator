#!/usr/bin/env python3
"""
필수 테스트 실행 스크립트
핵심 기능의 정상 작동을 검증합니다.
"""

import sys
import subprocess
import os
from pathlib import Path


def run_test_category(category_name, test_path, description):
    """테스트 카테고리 실행"""
    print(f"\n{'='*60}")
    print(f"🧪 {category_name}: {description}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                test_path,
                "-v",
                "--tb=short",
                "-m",
                "not manual",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        if result.returncode == 0:
            print(f"✅ {category_name} 테스트 통과!")
            lines = result.stdout.split("\n")
            for line in lines:
                if "passed" in line and "=" in line:
                    print(f"📊 {line.strip()}")
            return True
        else:
            print(f"❌ {category_name} 테스트 실패!")
            print("🔍 오류 정보:")
            print(result.stdout)
            if result.stderr:
                print("🚨 오류 메시지:")
                print(result.stderr)
            return False

    except Exception as e:
        print(f"❌ {category_name} 테스트 실행 중 오류: {e}")
        return False


def run_unit_test(test_name, test_file):
    """개별 단위 테스트 실행"""
    print(f"\n{'='*40}")
    print(f"🔬 {test_name}")
    print(f"{'='*40}")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        if result.returncode == 0:
            print(f"✅ {test_name} 통과")
            return True
        else:
            print(f"❌ {test_name} 실패")
            print("오류 정보:")
            error_lines = result.stdout.split("\n")
            for line in error_lines:
                if "FAILED" in line or "ERROR" in line:
                    print(f"  {line}")
            return False

    except Exception as e:
        print(f"❌ {test_name} 실행 중 오류: {e}")
        return False


def main():
    """메인 실행 함수"""
    print("🚀 Newsletter Generator 필수 테스트 실행")
    print("=" * 60)

    # 현재 작업 디렉토리 확인
    current_dir = Path.cwd()
    print(f"📁 작업 디렉토리: {current_dir}")

    # 프로젝트 루트 확인
    project_root = Path(__file__).parent.parent
    if not (project_root / "newsletter").exists():
        print("❌ 프로젝트 루트를 찾을 수 없습니다!")
        return False

    print(f"📁 프로젝트 루트: {project_root}")

    # 테스트 결과 추적
    results = {}

    # 1. ConfigManager 테스트
    print("\n" + "=" * 60)
    print("��️  1단계: 핵심 설정 관리 테스트")
    print("=" * 60)

    config_test = project_root / "tests" / "unit_tests" / "test_config_manager.py"
    if config_test.exists():
        results["ConfigManager"] = run_unit_test(
            "ConfigManager 테스트", str(config_test)
        )
    else:
        print("❌ ConfigManager 테스트 파일을 찾을 수 없습니다")
        results["ConfigManager"] = False

    # 2. 메일 시스템 테스트
    print("\n" + "=" * 60)
    print("📧 2단계: 이메일 발송 시스템 테스트")
    print("=" * 60)

    mail_test = project_root / "tests" / "test_mail.py"
    if mail_test.exists():
        results["Mail System"] = run_unit_test("메일 시스템 테스트", str(mail_test))
    else:
        print("❌ 메일 테스트 파일을 찾을 수 없습니다")
        results["Mail System"] = False

    # 3. 날짜 처리 테스트
    print("\n" + "=" * 60)
    print("📅 3단계: 날짜 처리 기능 테스트")
    print("=" * 60)

    date_test = project_root / "tests" / "unit_tests" / "test_scrape_dates.py"
    if date_test.exists():
        results["Date Processing"] = run_unit_test("날짜 처리 테스트", str(date_test))
    else:
        print("⚠️  날짜 처리 테스트 파일을 찾을 수 없습니다")
        results["Date Processing"] = False

    # 4. 전체 단위 테스트 (수정된 것들만)
    print("\n" + "=" * 60)
    print("🧪 4단계: 핵심 단위 테스트")
    print("=" * 60)

    unit_tests_dir = project_root / "tests" / "unit_tests"
    if unit_tests_dir.exists():
        results["Core Unit Tests"] = run_test_category(
            "핵심 단위 테스트", str(unit_tests_dir), "핵심 기능의 단위 테스트"
        )
    else:
        print("❌ 단위 테스트 디렉토리를 찾을 수 없습니다")
        results["Core Unit Tests"] = False

    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)

    passed_count = sum(1 for result in results.values() if result)
    total_count = len(results)

    for test_name, result in results.items():
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{test_name:20} : {status}")

    print(f"\n총 테스트: {total_count}")
    print(f"통과: {passed_count}")
    print(f"실패: {total_count - passed_count}")
    print(f"성공률: {(passed_count/total_count)*100:.1f}%")

    if passed_count == total_count:
        print("\n🎉 모든 필수 테스트가 통과했습니다!")
        return True
    else:
        print(f"\n⚠️  {total_count - passed_count}개의 테스트가 실패했습니다.")
        print("실패한 테스트를 검토해주세요.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
