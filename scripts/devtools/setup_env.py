#!/usr/bin/env python3
"""
Newsletter Generator 환경 설정 도우미 스크립트
.env 파일을 생성하고 필요한 환경변수를 설정할 수 있도록 도와줍니다.
"""

import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_SAMPLE_PATH = PROJECT_ROOT / ".env.example"
DEFAULT_ENV_VALUES = {
    "SERPER_API_KEY": "your_serper_api_key_here",
    "GEMINI_API_KEY": "your_gemini_api_key_here",
    "OPENAI_API_KEY": "your_openai_api_key_here",
    "ANTHROPIC_API_KEY": "your_anthropic_api_key_here",
    "POSTMARK_SERVER_TOKEN": "your_postmark_server_token_here",
    "EMAIL_SENDER": "your_verified_email@yourdomain.com",
    "NAVER_CLIENT_ID": "your_naver_client_id_here",
    "NAVER_CLIENT_SECRET": "your_naver_client_secret_here",
    "GOOGLE_APPLICATION_CREDENTIALS": "path/to/your/credentials.json",
    "GOOGLE_CLIENT_ID": "your_google_client_id_here",
    "GOOGLE_CLIENT_SECRET": "your_google_client_secret_here",
    "ADDITIONAL_RSS_FEEDS": "",
}


def render_env_content(overrides):
    """Render .env content from the canonical sample with selected overrides."""
    template = ENV_SAMPLE_PATH.read_text(encoding="utf-8")
    rendered_lines = []

    for line in template.splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            rendered_lines.append(line)
            continue

        key, _, _ = line.partition("=")
        key = key.strip()
        if key in overrides:
            rendered_lines.append(f"{key}={overrides[key]}")
        else:
            rendered_lines.append(line)

    return "\n".join(rendered_lines) + "\n"


def print_header():
    """헤더 출력"""
    print("=" * 60)
    print("📧 Newsletter Generator 환경 설정 도우미")
    print("=" * 60)
    print()


def check_existing_env():
    """기존 .env 파일 확인"""
    env_path = Path(".env")
    if env_path.exists():
        print("⚠️  기존 .env 파일이 발견되었습니다.")
        backup = input("백업 후 새로 생성하시겠습니까? (y/n): ").lower().strip()
        if backup == "y":
            # 백업 생성
            backup_path = ".env.backup"
            shutil.copy(".env", backup_path)
            print(f"✅ 기존 파일이 {backup_path}로 백업되었습니다.")
            return True
        else:
            print("❌ 설정을 취소했습니다.")
            return False
    return True


def get_user_input(prompt, default="", required=False):
    """사용자 입력 받기"""
    if default:
        prompt += f" [{default}]"
    prompt += ": "

    while True:
        value = input(prompt).strip()
        if not value and default:
            return default
        if not value and required:
            print("❌ 필수 항목입니다. 값을 입력해주세요.")
            continue
        return value or default


def setup_env_interactive():
    """대화형 환경 설정"""
    print("📝 필수 API 키 설정")
    print("-" * 30)

    # 필수 설정
    serper_key = get_user_input(
        "Serper API 키 (https://serper.dev)", "your_serper_api_key_here", required=True
    )

    gemini_key = get_user_input(
        "Gemini API 키 (https://aistudio.google.com)",
        "your_gemini_api_key_here",
        required=True,
    )

    print("\n📧 이메일 발송 설정")
    print("-" * 30)

    postmark_token = get_user_input(
        "Postmark 서버 토큰 (https://postmarkapp.com)",
        "your_postmark_server_token_here",
    )

    email_sender = get_user_input(
        "발송자 이메일 주소 (Postmark에서 인증된 주소)",
        "your_verified_email@yourdomain.com",
    )

    print("\n🔧 선택사항 설정 (Enter로 건너뛰기)")
    print("-" * 30)

    # 선택사항
    openai_key = get_user_input("OpenAI API 키", "your_openai_api_key_here")
    anthropic_key = get_user_input("Anthropic API 키", "your_anthropic_api_key_here")
    naver_id = get_user_input("네이버 클라이언트 ID", "your_naver_client_id_here")
    naver_secret = get_user_input("네이버 클라이언트 시크릿", "your_naver_client_secret_here")
    google_creds = get_user_input("Google 인증서 경로", "path/to/your/credentials.json")
    google_client_id = get_user_input("Google 클라이언트 ID", "your_google_client_id_here")
    google_client_secret = get_user_input(
        "Google 클라이언트 시크릿", "your_google_client_secret_here"
    )
    rss_feeds = get_user_input("추가 RSS 피드 URL (쉼표로 구분)", "")

    env_content = render_env_content(
        {
            **DEFAULT_ENV_VALUES,
            "SERPER_API_KEY": serper_key,
            "GEMINI_API_KEY": gemini_key,
            "OPENAI_API_KEY": openai_key,
            "ANTHROPIC_API_KEY": anthropic_key,
            "POSTMARK_SERVER_TOKEN": postmark_token,
            "EMAIL_SENDER": email_sender,
            "NAVER_CLIENT_ID": naver_id,
            "NAVER_CLIENT_SECRET": naver_secret,
            "GOOGLE_APPLICATION_CREDENTIALS": google_creds,
            "GOOGLE_CLIENT_ID": google_client_id,
            "GOOGLE_CLIENT_SECRET": google_client_secret,
            "ADDITIONAL_RSS_FEEDS": rss_feeds,
        }
    )

    # 파일 저장
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)

    print("\n✅ .env 파일이 성공적으로 생성되었습니다!")
    return True


def create_simple_env():
    """간단한 템플릿 .env 파일 생성"""
    env_content = render_env_content(DEFAULT_ENV_VALUES)

    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)

    print("✅ .env 템플릿 파일이 생성되었습니다.")
    print("📝 .env 파일을 열어서 실제 API 키 값들로 수정해주세요.")


def print_instructions():
    """설치 안내사항 출력"""
    print("\n" + "=" * 60)
    print("📋 API 키 발급 안내")
    print("=" * 60)
    print()
    print("1. 🔍 Serper API (필수 - 뉴스 검색용)")
    print("   - https://serper.dev 방문")
    print("   - 구글 계정으로 로그인")
    print("   - Dashboard에서 API 키 복사")
    print("   - 월 2,500회 무료 사용 가능")
    print()
    print("2. 🤖 Google Gemini API (필수 - AI 모델용)")
    print("   - https://aistudio.google.com 방문")
    print("   - Google 계정으로 로그인")
    print("   - 'Get API Key' 클릭하여 발급")
    print("   - 무료 할당량 제공")
    print()
    print("3. 📧 Postmark (필수 - 이메일 발송용)")
    print("   - https://postmarkapp.com 방문")
    print("   - 계정 생성 (월 100개 이메일 무료)")
    print("   - Server → API Tokens에서 토큰 발급")
    print("   - Signatures에서 발송자 이메일 인증")
    print()
    print("4. 🔧 선택사항 API들")
    print("   - OpenAI: https://platform.openai.com")
    print("   - Anthropic: https://console.anthropic.com")
    print("   - 네이버: https://developers.naver.com")
    print()


def main():
    """메인 실행 함수"""
    os.chdir(PROJECT_ROOT)

    print_header()

    if not ENV_SAMPLE_PATH.exists():
        print("❌ canonical .env.example 파일을 찾을 수 없습니다.")
        print("   저장소 루트의 .env.example을 복구한 뒤 다시 실행하세요.")
        return

    if not check_existing_env():
        return

    print("환경 설정 방법을 선택하세요:")
    print("1. 대화형 설정 (추천)")
    print("2. 템플릿 파일만 생성")
    print("3. API 키 발급 안내 보기")
    print("4. 종료")

    choice = input("\n선택 (1-4): ").strip()

    if choice == "1":
        setup_env_interactive()
        print_instructions()
    elif choice == "2":
        create_simple_env()
        print_instructions()
    elif choice == "3":
        print_instructions()
    elif choice == "4":
        print("👋 설정을 종료합니다.")
        return
    else:
        print("❌ 잘못된 선택입니다.")
        return

    print("\n" + "=" * 60)
    print("🎉 설정 완료! 다음 단계:")
    print("=" * 60)
    print("1. .env 파일에서 API 키들을 실제 값으로 변경")
    print("2. 이메일 발송 테스트: python -m newsletter test-email --to your@email.com")
    print("3. 뉴스레터 생성 테스트: python -m newsletter run")
    print("4. 웹 인터페이스 실행: python -m web.app")
    print()


if __name__ == "__main__":
    main()
