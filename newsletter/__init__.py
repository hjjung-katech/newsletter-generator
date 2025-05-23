"""
Newsletter Generator - LangChain과 LangGraph 기반 뉴스레터 생성 패키지

이 패키지는 키워드를 기반으로 최신 뉴스를 수집하고 요약하여
HTML 형식의 뉴스레터를 자동으로 생성하는 기능을 제공합니다.
"""

import os
from datetime import datetime

# Set the generation date environment variable with current date and time
os.environ["GENERATION_DATE"] = datetime.now().strftime("%Y-%m-%d")
os.environ["GENERATION_TIMESTAMP"] = datetime.now().strftime("%H:%M:%S")

__version__ = "0.2.0"
