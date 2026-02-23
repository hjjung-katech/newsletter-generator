#!/usr/bin/env python3
"""
Newsletter Generator 환경 설정 도우미 스크립트
.env 파일을 생성하고 필요한 환경변수를 설정할 수 있도록 도와줍니다.
"""

import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 환경변수 템플릿
ENV_TEMPLATE = """# Newsletter Generator 환경변수 설정
# =============================================
# 이 파일을 .env로 저장하고 실제 값들로 변경하세요.

# API 키 설정 (필수)
# =============================================
# 구글 Serper API (뉴스 검색용) - 필수
# https://serper.dev에서 무료 API 키 발급 (월 2,500회 무료)
SERPER_API_KEY={serper_key}

# AI 모델 API 키들
# Google Gemini API - https://aistudio.google.com (무료 할당량 있음)
GEMINI_API_KEY={gemini_key}

# 추가 AI 모델 API 키들 (선택사항)
# OpenAI API - https://platform.openai.com
OPENAI_API_KEY={openai_key}
# Anthropic API - https://console.anthropic.com
ANTHROPIC_API_KEY={anthropic_key}

# 이메일 발송 설정 (필수 - 이메일 발송용)
# =============================================
# Postmark 서버 토큰 - https://postmarkapp.com에서 발급
# 새 계정 시 월 100개 이메일 무료
POSTMARK_SERVER_TOKEN={postmark_token}

# 이메일 발송자 주소 (Postmark에서 인증된 도메인/주소여야 함)
# CLI와 웹 인터페이스 모두에서 사용됨
EMAIL_SENDER={email_sender}
# 웹 인터페이스 호환성을 위한 별칭 (EMAIL_SENDER와 동일하게 설정)
POSTMARK_FROM_EMAIL={email_sender}

# 추가 API 설정 (선택사항)
# =============================================
# 네이버 뉴스 API (선택사항) - https://developers.naver.com
NAVER_CLIENT_ID={naver_id}
NAVER_CLIENT_SECRET={naver_secret}

# Google Drive 업로드용 (선택사항)
GOOGLE_APPLICATION_CREDENTIALS={google_creds}
GOOGLE_CLIENT_ID={google_client_id}
GOOGLE_CLIENT_SECRET={google_client_secret}

# 추가 RSS 피드 URL (쉼표로 구분, 선택사항)
ADDITIONAL_RSS_FEEDS={rss_feeds}

# 개발 환경 설정
# =============================================
# Flask 환경 (development/production)
FLASK_ENV=development
# 디버그 모드
DEBUG=true
# 포트 설정
PORT=5000
"""


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

    # .env 파일 생성
    env_content = ENV_TEMPLATE.format(
        serper_key=serper_key,
        gemini_key=gemini_key,
        openai_key=openai_key,
        anthropic_key=anthropic_key,
        postmark_token=postmark_token,
        email_sender=email_sender,
        naver_id=naver_id,
        naver_secret=naver_secret,
        google_creds=google_creds,
        google_client_id=google_client_id,
        google_client_secret=google_client_secret,
        rss_feeds=rss_feeds,
    )

    # 파일 저장
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)

    print("\n✅ .env 파일이 성공적으로 생성되었습니다!")
    return True


def create_simple_env():
    """간단한 템플릿 .env 파일 생성"""
    env_content = ENV_TEMPLATE.format(
        serper_key="your_serper_api_key_here",
        gemini_key="your_gemini_api_key_here",
        openai_key="your_openai_api_key_here",
        anthropic_key="your_anthropic_api_key_here",
        postmark_token="your_postmark_server_token_here",
        email_sender="your_verified_email@yourdomain.com",
        naver_id="your_naver_client_id_here",
        naver_secret="your_naver_client_secret_here",
        google_creds="path/to/your/credentials.json",
        google_client_id="your_google_client_id_here",
        google_client_secret="your_google_client_secret_here",
        rss_feeds="",
    )

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
    print("4. 웹 인터페이스 실행: python test_server.py")
    print()


if __name__ == "__main__":
    main()
