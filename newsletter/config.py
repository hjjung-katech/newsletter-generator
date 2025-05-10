from dotenv import load_dotenv
import os

load_dotenv() # Load environment variables from .env file

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # 통합된 API 키
# SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY") # 주석 처리 또는 삭제
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") # 새로 추가
# GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # 이 줄 삭제

# Add other configurations as needed

# For local development, you might want to set default values or raise errors if keys are missing
if not SERPER_API_KEY:
    print("Warning: SERPER_API_KEY not found in .env file.")
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in .env file. Keyword suggestion and other Gemini-based features may not work.")
# if not SENDGRID_API_KEY: # 주석 처리 또는 삭제
#     print("Warning: SENDGRID_API_KEY not found in .env file.") # 주석 처리 또는 삭제
if not GOOGLE_APPLICATION_CREDENTIALS: # 새로 추가
    print("Warning: GOOGLE_APPLICATION_CREDENTIALS not found in .env file. Google Drive upload will not work.") # 새로 추가