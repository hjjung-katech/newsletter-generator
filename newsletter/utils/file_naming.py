"""
파일 이름 관련 유틸리티 함수들
"""

import os
import re
from datetime import datetime
from typing import Optional, List


def get_safe_filename(text: str) -> str:
    """
    주어진 텍스트를 파일 이름으로 안전하게 사용할 수 있도록 변환

    Args:
        text: 변환할 텍스트

    Returns:
        파일 이름으로 사용 가능한 텍스트
    """
    # 유효하지 않은 파일명 문자 제거 및 공백을 밑줄로 대체
    safe_text = re.sub(r"[^\w\s-]", "", text)
    safe_text = re.sub(r"[-\s]+", "_", safe_text)

    # 최대 길이 제한
    return safe_text[:50].strip("_")


def generate_render_data_filename(topic: str, timestamp: Optional[str] = None) -> str:
    """
    렌더링 데이터 JSON 파일의 경로를 생성

    Args:
        topic: 뉴스레터 주제
        timestamp: 선택적 타임스탬프 (YYYYMMDD_HHMMSS 형식)

    Returns:
        렌더링 데이터 파일의 전체 경로
    """
    # 타임스탬프가 제공되지 않은 경우 현재 시간 사용
    if not timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 중간 처리 디렉토리 경로
    intermediate_dir = os.path.join("output", "intermediate_processing")
    os.makedirs(intermediate_dir, exist_ok=True)

    # 주제를 파일 이름으로 사용 가능하게 변환
    safe_topic = get_safe_filename(topic)

    # 파일 이름 구성
    if safe_topic:
        filename = f"render_data_{timestamp}_{safe_topic}.json"
    else:
        filename = f"render_data_{timestamp}.json"

    return os.path.join(intermediate_dir, filename)


def generate_newsletter_filename(topic: str, timestamp: Optional[str] = None) -> str:
    """
    뉴스레터 HTML 파일의 경로를 생성

    Args:
        topic: 뉴스레터 주제
        timestamp: 선택적 타임스탬프 (YYYYMMDD_HHMMSS 형식)

    Returns:
        뉴스레터 HTML 파일의 전체 경로
    """
    # 타임스탬프가 제공되지 않은 경우 현재 시간 사용
    if not timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 출력 디렉토리 경로
    output_dir = os.path.join("output")
    os.makedirs(output_dir, exist_ok=True)

    # 주제를 파일 이름으로 사용 가능하게 변환
    safe_topic = get_safe_filename(topic)

    # 파일 이름 구성
    if safe_topic:
        filename = f"newsletter_{timestamp}_{safe_topic}.html"
    else:
        filename = f"newsletter_{timestamp}.html"

    return os.path.join(output_dir, filename)


def find_recent_render_data_files(
    directory: str = os.path.join("output", "intermediate_processing"),
    count: int = 5,
    topic_filter: Optional[str] = None,
) -> List[str]:
    """
    가장 최근의 렌더링 데이터 파일 찾기

    Args:
        directory: 검색할 디렉토리
        count: 반환할 최대 파일 수
        topic_filter: 선택적 주제 필터

    Returns:
        최근 렌더링 데이터 파일 경로 목록
    """
    if not os.path.exists(directory):
        return []

    # 디렉토리 내 모든 파일 가져오기
    all_files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f)) and f.startswith("render_data_")
    ]

    # 주제 필터링 (필요한 경우)
    if topic_filter:
        safe_topic = get_safe_filename(topic_filter)
        all_files = [f for f in all_files if safe_topic in os.path.basename(f)]

    # 수정 시간 기준으로 정렬
    all_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

    # 지정된 수만큼 반환
    return all_files[:count]
