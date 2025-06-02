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
            [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"],
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
            print("STDOUT:", result.stdout[-500:])  # 마지막 500자만 출력
            print("STDERR:", result.stderr[-500:])
            return False

    except Exception as e:
        print(f"💥 {category_name} 테스트 실행 중 오류: {e}")
        return False


def test_config_integration():
    """설정 통합 테스트"""
    print(f"\n{'='*60}")
    print(f"🔧 ConfigManager 통합 테스트")
    print(f"{'='*60}")

    try:
        from newsletter.config_manager import config_manager

        print("✅ ConfigManager 임포트 성공")

        # 설정 로딩 테스트
        llm_config = config_manager.get_llm_config()
        newsletter_settings = config_manager.get_newsletter_settings()
        scoring_weights = config_manager.get_scoring_weights()

        print(
            f"✅ LLM 설정 로딩 성공 (기본 제공자: {llm_config.get('default_provider')})"
        )
        print(
            f"✅ 뉴스레터 설정 로딩 성공 (제목: {newsletter_settings.get('newsletter_title')[:30]}...)"
        )
        print(
            f"✅ 스코어링 가중치 로딩 성공 (가중치 합: {sum(scoring_weights.values()):.2f})"
        )

        # 이메일 설정 검증
        email_validation = config_manager.validate_email_config()
        email_status = "설정됨" if email_validation["ready"] else "미설정"
        print(f"📧 이메일 설정 상태: {email_status}")

        return True

    except Exception as e:
        print(f"❌ 설정 통합 테스트 실패: {e}")
        return False


def main():
    """메인 테스트 실행"""
    print("🚀 Newsletter Generator 필수 테스트 시작")
    print(f"작업 디렉토리: {os.getcwd()}")

    results = []

    # 1. ConfigManager 단위 테스트
    results.append(
        run_test_category(
            "ConfigManager",
            "tests/unit_tests/test_config_manager.py",
            "설정 관리자 핵심 기능 검증",
        )
    )

    # 2. 설정 통합 테스트
    results.append(test_config_integration())

    # 3. 이메일 기능 테스트 (있는 경우)
    email_test_path = "tests/unit_tests/test_mail.py"
    if Path(email_test_path).exists():
        results.append(
            run_test_category("Email", email_test_path, "이메일 발송 기능 검증")
        )

    # 4. 핵심 컴포넌트 테스트
    core_tests = [
        ("tests/test_compose.py", "뉴스레터 구성"),
        ("tests/test_scoring.py", "기사 점수 매기기"),
        ("tests/test_themes.py", "주제 추출"),
    ]

    for test_path, description in core_tests:
        if Path(test_path).exists():
            results.append(
                run_test_category(
                    Path(test_path).stem.replace("test_", ""), test_path, description
                )
            )

    # 결과 요약
    print(f"\n{'='*60}")
    print("📊 테스트 결과 요약")
    print(f"{'='*60}")

    passed = sum(results)
    total = len(results)

    print(f"총 {total}개 테스트 카테고리 중 {passed}개 통과")
    print(f"성공률: {passed/total*100:.1f}%" if total > 0 else "테스트 없음")

    if passed == total:
        print("🎉 모든 필수 테스트 통과!")
        return 0
    else:
        print("⚠️ 일부 테스트 실패. 위의 오류 메시지를 확인하세요.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
