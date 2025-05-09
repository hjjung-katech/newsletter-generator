from dotenv import load_dotenv
import os

load_dotenv() # Load environment variables from .env file

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
# Add other configurations as needed

# For local development, you might want to set default values or raise errors if keys are missing
if not NEWS_API_KEY:
    print("Warning: NEWS_API_KEY not found in .env file.")
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in .env file.")
if not SENDGRID_API_KEY:
    print("Warning: SENDGRID_API_KEY not found in .env file.")
