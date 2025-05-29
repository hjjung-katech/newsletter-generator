"""
파일 이름 관련 유틸리티 함수들
"""

import os
import re
from datetime import datetime
from typing import List, Optional


def get_safe_filename(topic: str) -> str:
    """
    파일명으로 사용 가능한 안전한 문자열로 변환

    Args:
        topic: 변환할 주제 문자열

    Returns:
        안전한 파일명 문자열
    """
    if not topic:
        return "default"

    # 특수 문자 제거 및 안전한 문자로 변환
    safe_topic = re.sub(r"[^\w\s-]", "", topic)
    safe_topic = re.sub(r"[-\s]+", "_", safe_topic)
    safe_topic = safe_topic[:50].strip("_")

    return safe_topic if safe_topic else "default"


def generate_unified_newsletter_filename(
    topic: str,
    style: str = "detailed",
    timestamp: str = None,
    use_current_date: bool = True,
    generation_type: str = "original",  # "original", "regenerated", "test"
    source_timestamp: str = None,  # 원본 파일의 타임스탬프 (재생성시 사용)
) -> str:
    """
    통일된 뉴스레터 파일명 생성 함수

    파일명 체계:
    - 원본: 2025-05-29_142113_newsletter_토픽_스타일.html
    - 재생성: 2025-05-29_142113_newsletter_토픽_스타일_regen_20250530_103045.html
    - 테스트: 2025-05-29_142113_newsletter_test_토픽_스타일.html

    Args:
        topic: 뉴스레터 주제
        style: 템플릿 스타일 (detailed, compact 등)
        timestamp: 타임스탬프 (YYYYMMDD_HHMMSS 또는 HHMMSS 형식)
        use_current_date: 현재 날짜를 사용할지 여부
        generation_type: 생성 타입 ("original", "regenerated", "test")
        source_timestamp: 원본 파일의 타임스탬프 (재생성시 원본 시간 유지용)

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

    # timestamp 형식 분석 및 표준화
    date_part, time_part = _parse_and_standardize_timestamp(timestamp, use_current_date)

    # 생성 타입에 따른 파일명 구성
    if generation_type == "original":
        # 원본: 2025-05-29_142113_newsletter_토픽_스타일.html
        filename = f"{date_part}_{time_part}_newsletter_{safe_topic}_{style}.html"

    elif generation_type == "regenerated":
        # 재생성: 원본 시간 유지 + 재생성 시간 추가
        if source_timestamp:
            source_date, source_time = _parse_and_standardize_timestamp(
                source_timestamp, use_current_date
            )
            regen_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            regen_date, regen_time = _parse_and_standardize_timestamp(
                regen_timestamp, True
            )
            filename = f"{source_date}_{source_time}_newsletter_{safe_topic}_{style}_regen_{regen_date}_{regen_time}.html"
        else:
            # source_timestamp가 없으면 현재 시간으로 재생성 표시
            filename = (
                f"{date_part}_{time_part}_newsletter_{safe_topic}_{style}_regen.html"
            )

    elif generation_type == "test":
        # 테스트: 2025-05-29_142113_newsletter_test_토픽_스타일.html
        filename = f"{date_part}_{time_part}_newsletter_test_{safe_topic}_{style}.html"

    else:
        # 기본값 (original과 동일)
        filename = f"{date_part}_{time_part}_newsletter_{safe_topic}_{style}.html"

    return os.path.join(output_dir, filename)


def _parse_and_standardize_timestamp(
    timestamp: str, use_current_date: bool = True
) -> tuple:
    """
    타임스탬프를 파싱하여 표준화된 날짜와 시간 부분을 반환

    Args:
        timestamp: 입력 타임스탬프 (다양한 형식)
        use_current_date: 날짜가 없을 때 현재 날짜 사용 여부

    Returns:
        tuple: (date_part, time_part) - ("2025-05-29", "142113")
    """
    # YYYYMMDD_HHMMSS 형태인지 확인
    if "_" in timestamp and len(timestamp.split("_")) == 2:
        date_str, time_str = timestamp.split("_")
        if len(date_str) == 8 and date_str.isdigit():
            # YYYYMMDD를 YYYY-MM-DD로 변환
            date_part = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            time_part = time_str
            return date_part, time_part

    # 시간만 있는 경우 (HHMMSS)
    if timestamp.isdigit() and len(timestamp) == 6:
        if use_current_date:
            date_part = datetime.now().strftime("%Y-%m-%d")
        else:
            date_part = "1900-01-01"  # 기본값
        time_part = timestamp
        return date_part, time_part

    # 기타 형식이거나 파싱 실패시 현재 시간 사용
    now = datetime.now()
    date_part = now.strftime("%Y-%m-%d")
    time_part = now.strftime("%H%M%S")
    return date_part, time_part


def generate_newsletter_filename(topic: str, timestamp: str = None) -> str:
    """
    뉴스레터 HTML 파일의 경로를 생성 (기존 함수 - 호환성 유지)

    Args:
        topic: 뉴스레터 주제
        timestamp: 선택적 타임스탬프 (YYYYMMDD_HHMMSS 형식)

    Returns:
        뉴스레터 HTML 파일의 전체 경로
    """
    # 새로운 통일 함수 호출 (기본 스타일은 detailed, 현재 날짜 포함)
    return generate_unified_newsletter_filename(topic, "detailed", timestamp, True)


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

    # 일관된 파일명 형식: timestamp_render_data.json
    filename = f"{timestamp}_render_data.json"

    return os.path.join(intermediate_dir, filename)


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


def generate_regenerated_newsletter_filename(
    original_filename: str, style: str = "detailed"
) -> str:
    """
    원본 파일명을 기반으로 재생성된 뉴스레터 파일명을 생성

    Args:
        original_filename: 원본 파일명 (경로 포함 가능)
        style: 템플릿 스타일

    Returns:
        재생성된 뉴스레터 파일의 전체 경로
    """
    # 원본 파일명에서 정보 추출
    basename = os.path.basename(original_filename)

    # 패턴 매칭으로 원본 정보 추출
    # 예: 2025-05-29_142113_newsletter_첨단바이오_detailed.html
    import re

    pattern = r"(\d{4}-\d{2}-\d{2})_(\d{6})_newsletter_(.+?)_(\w+)\.html"
    match = re.match(pattern, basename)

    if match:
        orig_date, orig_time, topic, orig_style = match.groups()
        source_timestamp = f"{orig_date.replace('-', '')}_{orig_time}"

        return generate_unified_newsletter_filename(
            topic=topic,
            style=style,
            generation_type="regenerated",
            source_timestamp=source_timestamp,
        )
    else:
        # 패턴 매칭 실패시 기본 재생성 파일명
        topic = "unknown"
        return generate_unified_newsletter_filename(
            topic=topic, style=style, generation_type="regenerated"
        )
