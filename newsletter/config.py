from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

# 기존 API 키 설정
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # 통합된 API 키
GOOGLE_APPLICATION_CREDENTIALS = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS"
)  # 새로 추가
# GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # 이 줄 삭제

# 새로운 API 키 설정
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")  # 네이버 API 클라이언트 ID
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")  # 네이버 API 클라이언트 시크릿
ADDITIONAL_RSS_FEEDS = os.getenv(
    "ADDITIONAL_RSS_FEEDS", ""
)  # 추가 RSS 피드 URL (쉼표로 구분)

# 이메일 발송 설정 (Postmark)
POSTMARK_SERVER_TOKEN = os.getenv("POSTMARK_SERVER_TOKEN")
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "newsletter@example.com")

# Google Drive 설정
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Add other configurations as needed

# 경고 메시지 출력
# 필수 API 키
if not SERPER_API_KEY:
    print("Warning: SERPER_API_KEY not found in .env file.")
if not GEMINI_API_KEY:
    print(
        "Warning: GEMINI_API_KEY not found in .env file. Keyword suggestion and other Gemini-based features may not work."
    )

# 선택적 API 키
if not GOOGLE_APPLICATION_CREDENTIALS:
    print(
        "Warning: GOOGLE_APPLICATION_CREDENTIALS not found in .env file. Google Drive upload will not work."
    )

# Postmark 설정 경고
if not POSTMARK_SERVER_TOKEN:
    print(
        "Warning: POSTMARK_SERVER_TOKEN not found in .env file. Email sending will not work."
    )

# 새로 추가된 API 키에 대한 경고 (선택적)
if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
    print(
        "Note: Naver News API credentials not found. Naver News API source will be disabled."
    )
