#!/usr/bin/env python3
"""
Newsletter Generator 환경 설정 문제 해결 스크립트
.env 파일 문제를 진단하고 자동으로 해결합니다.
"""

import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def print_header():
    """헤더 출력"""
    print("=" * 70)
    print("🔧 Newsletter Generator 환경 설정 문제 해결")
    print("=" * 70)
    print()


def diagnose_env_problem():
    """환경변수 문제 진단"""
    print("1. 📋 문제 진단")
    print("-" * 30)

    env_file = Path(".env")
    backup_file = Path(".env.backup")
    example_file = Path(".env.example")

    # 파일 존재 여부 확인
    print(f"📄 .env 파일: {'✅ 존재' if env_file.exists() else '❌ 없음'}")
    print(f"📄 .env.backup 파일: {'✅ 존재' if backup_file.exists() else '❌ 없음'}")
    print(f"📄 .env.example 파일: {'✅ 존재' if example_file.exists() else '❌ 없음'}")

    # 백업 파일 문제 확인
    if backup_file.exists():
        print("\n🔍 .env.backup 파일 분석 중...")
        try:
            content = backup_file.read_text(encoding="utf-8")

            # 여러 줄에 걸친 값 찾기
            multiline_issues = []
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "=" in line and line.strip() and not line.strip().startswith("#"):
                    key, value = line.split("=", 1)
                    # 따옴표로 시작하지만 끝나지 않는 경우
                    if (value.startswith('"') and not value.endswith('"')) or (
                        value.startswith("'") and not value.endswith("'")
                    ):
                        multiline_issues.append((i + 1, key.strip(), value))

            if multiline_issues:
                print("❌ 발견된 문제:")
                for line_num, key, value in multiline_issues:
                    print(f"   라인 {line_num}: {key} - 여러 줄에 걸친 값")
                return True
            else:
                print("✅ .env.backup 파일 형식이 올바름")
                return False

        except Exception as e:
            print(f"❌ .env.backup 파일 읽기 실패: {e}")
            return True

    return False


def fix_backup_file():
    """백업 파일의 형식 문제 수정"""
    print("\n2. 🔧 .env.backup 파일 수정")
    print("-" * 30)

    backup_file = Path(".env.backup")
    if not backup_file.exists():
        print("❌ .env.backup 파일이 없습니다.")
        return False

    try:
        # 원본 내용 읽기
        content = backup_file.read_text(encoding="utf-8")
        lines = content.split("\n")

        fixed_lines = []
        current_key = None
        current_value = ""

        for line in lines:
            line = line.strip()

            # 주석이나 빈 줄
            if not line or line.startswith("#"):
                # 이전에 처리 중인 키가 있다면 저장
                if current_key:
                    # 따옴표 제거 및 정리
                    clean_value = current_value.strip().strip('"').strip("'")
                    fixed_lines.append(f"{current_key}={clean_value}")
                    current_key = None
                    current_value = ""
                fixed_lines.append(line)
                continue

            # 새로운 키=값 시작
            if "=" in line and not current_key:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # 값이 완전한지 확인
                if (
                    (value.startswith('"') and value.endswith('"'))
                    or (value.startswith("'") and value.endswith("'"))
                    or (not value.startswith('"') and not value.startswith("'"))
                ):
                    # 완전한 값
                    clean_value = value.strip('"').strip("'")
                    fixed_lines.append(f"{key}={clean_value}")
                else:
                    # 불완전한 값 - 다음 줄까지 이어짐
                    current_key = key
                    current_value = value

            # 이전 키의 값 계속
            elif current_key:
                current_value += line

                # 값이 완료되었는지 확인
                if current_value.endswith('"') or current_value.endswith("'"):
                    clean_value = current_value.strip().strip('"').strip("'")
                    fixed_lines.append(f"{current_key}={clean_value}")
                    current_key = None
                    current_value = ""

        # 마지막에 처리되지 않은 키가 있다면 저장
        if current_key:
            clean_value = current_value.strip().strip('"').strip("'")
            fixed_lines.append(f"{current_key}={clean_value}")

        # 수정된 내용 저장
        fixed_content = "\n".join(fixed_lines)

        # 새 파일로 저장
        fixed_file = Path(".env.backup.fixed")
        fixed_file.write_text(fixed_content, encoding="utf-8")

        print("✅ .env.backup 파일을 수정하여 .env.backup.fixed로 저장했습니다.")
        return True

    except Exception as e:
        print(f"❌ 백업 파일 수정 실패: {e}")
        return False


def restore_env_file():
    """수정된 백업 파일을 .env로 복원"""
    print("\n3. 📁 .env 파일 복원")
    print("-" * 30)

    fixed_file = Path(".env.backup.fixed")
    env_file = Path(".env")

    if not fixed_file.exists():
        print("❌ 수정된 백업 파일이 없습니다.")
        return False

    try:
        # 기존 .env 파일이 있다면 백업
        if env_file.exists():
            backup_name = f".env.old.{os.getpid()}"
            shutil.copy(env_file, backup_name)
            print(f"📋 기존 .env 파일을 {backup_name}로 백업했습니다.")

        # 수정된 파일을 .env로 복사
        shutil.copy(fixed_file, env_file)

        # 웹 인터페이스 호환성을 위해 POSTMARK_FROM_EMAIL 추가
        content = env_file.read_text(encoding="utf-8")
        if "EMAIL_SENDER=" in content and "POSTMARK_FROM_EMAIL=" not in content:
            # EMAIL_SENDER 값 추출
            for line in content.split("\n"):
                if line.startswith("EMAIL_SENDER="):
                    email_value = line.split("=", 1)[1].strip()
                    content += f"\nPOSTMARK_FROM_EMAIL={email_value}\n"
                    break

            env_file.write_text(content, encoding="utf-8")
            print("📧 웹 인터페이스 호환성을 위해 POSTMARK_FROM_EMAIL을 추가했습니다.")

        print("✅ .env 파일이 성공적으로 복원되었습니다!")

        # 임시 파일 정리
        fixed_file.unlink()

        return True

    except Exception as e:
        print(f"❌ .env 파일 복원 실패: {e}")
        return False


def test_env_loading():
    """환경변수 로딩 테스트"""
    print("\n4. 🧪 환경변수 로딩 테스트")
    print("-" * 30)

    try:
        # dotenv 라이브러리로 테스트
        from dotenv import load_dotenv

        env_file = Path(".env")
        if not env_file.exists():
            print("❌ .env 파일이 없습니다.")
            return False

        # 환경변수 로드 테스트
        load_dotenv(env_file)

        # 주요 환경변수 확인
        required_vars = ["SERPER_API_KEY", "GEMINI_API_KEY"]
        email_vars = ["POSTMARK_SERVER_TOKEN", "EMAIL_SENDER"]

        all_good = True

        print("필수 환경변수:")
        for var in required_vars:
            value = os.getenv(var)
            if value:
                print(f"  ✅ {var}: {'설정됨' if value else '비어있음'}")
            else:
                print(f"  ❌ {var}: 설정되지 않음")
                all_good = False

        print("\n이메일 환경변수:")
        for var in email_vars:
            value = os.getenv(var)
            if value:
                print(f"  ✅ {var}: 설정됨")
            else:
                print(f"  ⚪ {var}: 설정되지 않음 (이메일 기능 비활성화)")

        if all_good:
            print("\n🎉 환경변수 로딩이 성공적으로 완료되었습니다!")
        else:
            print("\n⚠️  일부 필수 환경변수가 누락되었습니다.")

        return all_good

    except Exception as e:
        print(f"❌ 환경변수 로딩 테스트 실패: {e}")
        return False


def test_newsletter_command():
    """newsletter 명령어 테스트"""
    print("\n5. 🚀 Newsletter 명령어 테스트")
    print("-" * 30)

    try:
        import subprocess

        # check-config 명령어 테스트
        result = subprocess.run(
            [sys.executable, "-m", "newsletter", "check-config"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            print("✅ newsletter check-config 명령어가 정상 실행되었습니다!")
            print("\n📋 실행 결과:")
            print(result.stdout)
            return True
        else:
            print("❌ newsletter check-config 명령어 실행 실패:")
            print(result.stderr)
            return False

    except subprocess.TimeoutExpired:
        print("⏰ newsletter 명령어 실행 시간 초과")
        return False
    except Exception as e:
        print(f"❌ newsletter 명령어 테스트 실패: {e}")
        return False


def print_summary():
    """결과 요약 및 권장사항"""
    print("\n" + "=" * 70)
    print("📊 문제 해결 완료!")
    print("=" * 70)
    print()

    print("✅ 완료된 작업:")
    print("  1. .env.backup 파일의 형식 문제 수정")
    print("  2. 올바른 .env 파일 생성")
    print("  3. 웹 인터페이스 호환성 개선")
    print("  4. 환경변수 로딩 검증")
    print()

    print("🎯 다음 단계:")
    print("  1. python -m newsletter check-config 실행하여 설정 확인")
    print("  2. python -m newsletter test-email --to your@email.com 으로 이메일 테스트")
    print("  3. 웹 인터페이스: python -m web.app")
    print()

    print("💡 중복 기능 정리:")
    print("  - 기존 check_email_setup.py 삭제 (newsletter check-config 사용)")
    print("  - setup_env.py는 새 설정용, fix_env_setup.py는 문제 해결용")
    print()


def main():
    """메인 실행 함수"""
    # 레거시와 동일하게 저장소 루트 기준으로 동작
    os.chdir(PROJECT_ROOT)

    print_header()

    # 1. 문제 진단
    has_problem = diagnose_env_problem()

    if not has_problem:
        print("\n✅ 환경설정에 문제가 없습니다!")
        return

    # 2. 백업 파일 수정
    if not fix_backup_file():
        print("\n❌ 백업 파일 수정에 실패했습니다.")
        return

    # 3. .env 파일 복원
    if not restore_env_file():
        print("\n❌ .env 파일 복원에 실패했습니다.")
        return

    # 4. 환경변수 로딩 테스트
    if not test_env_loading():
        print("\n❌ 환경변수 로딩에 문제가 있습니다.")
        return

    # 5. Newsletter 명령어 테스트
    test_newsletter_command()

    # 6. 결과 요약
    print_summary()


if __name__ == "__main__":
    main()
