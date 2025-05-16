"""
날짜 및 시간 유틸리티 모듈

이 모듈은 날짜와 시간 문자열을 파싱하고 포맷팅하는 함수들을 제공합니다.
프로그램 전체에서 일관된 날짜 형식을 유지하기 위해 이 모듈을 사용합니다.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple
import re


def parse_date_string(date_str: Any) -> Optional[datetime]:
    """
    다양한 형식의 날짜/시간 문자열을 파싱하여 datetime 객체로 변환합니다.
    상대 시간을 포함한 다양한 형식을 지원합니다.

    Args:
        date_str: 변환할 날짜 문자열

    Returns:
        파싱 성공 시 datetime 객체, 실패 시 None
    """
    if not isinstance(date_str, str) or not date_str.strip() or date_str == "날짜 없음":
        return None

    date_str = date_str.strip()
    now = datetime.now(timezone.utc)  # Use timezone-aware now for relative dates

    # 1. Handle relative Korean dates
    if date_str.endswith("일 전"):  # "X일 전"
        try:
            days_ago = int(date_str.split("일")[0].strip())
            return now - timedelta(days=days_ago)
        except ValueError:
            pass
    elif date_str.endswith("시간 전"):  # "X시간 전"
        try:
            hours_ago = int(date_str.split("시간")[0].strip())
            return now - timedelta(hours=hours_ago)
        except ValueError:
            pass
    elif date_str.endswith("분 전"):  # "X분 전"
        try:
            minutes_ago = int(date_str.split("분")[0].strip())
            return now - timedelta(minutes=minutes_ago)
        except ValueError:
            pass
    elif date_str == "어제":
        return now - timedelta(days=1)
    elif date_str == "오늘":
        return now

    # 2. Handle relative English dates
    # 추가: months ago 패턴 처리
    months_match = re.search(r"(\d+)\s+months?\s+ago", date_str, re.IGNORECASE)
    if months_match:
        try:
            months_ago = int(months_match.group(1))
            # 한 달을 30일로 근사
            return now - timedelta(days=months_ago * 30)
        except ValueError:
            pass

    # 추가: weeks ago 패턴 처리
    weeks_match = re.search(r"(\d+)\s+weeks?\s+ago", date_str, re.IGNORECASE)
    if weeks_match:
        try:
            weeks_ago = int(weeks_match.group(1))
            return now - timedelta(weeks=weeks_ago)
        except ValueError:
            pass

    days_match = re.search(r"(\d+)\s+days?\s+ago", date_str, re.IGNORECASE)
    if days_match:
        try:
            days_ago = int(days_match.group(1))
            return now - timedelta(days=days_ago)
        except ValueError:
            pass

    hours_match = re.search(r"(\d+)\s+hours?\s+ago", date_str, re.IGNORECASE)
    if hours_match:
        try:
            hours_ago = int(hours_match.group(1))
            return now - timedelta(hours=hours_ago)
        except ValueError:
            pass

    minutes_match = re.search(r"(\d+)\s+minutes?\s+ago", date_str, re.IGNORECASE)
    if minutes_match:
        try:
            minutes_ago = int(minutes_match.group(1))
            return now - timedelta(minutes=minutes_ago)
        except ValueError:
            pass

    # 3. ISO 8601 format (with or without 'Z')
    try:
        if date_str.endswith("Z") and len(date_str) > 1:
            dt = datetime.fromisoformat(date_str[:-1] + "+00:00")
        else:
            dt = datetime.fromisoformat(date_str)
        # If parsed successfully but naive, make it timezone-aware (assume UTC)
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass

    # 4. Try other common formats
    common_formats = [
        "%Y-%m-%dT%H:%M:%S.%f%z",  # ISO with microseconds and timezone
        "%Y-%m-%dT%H:%M:%S%z",  # ISO with timezone
        "%Y-%m-%dT%H:%M:%S",  # ISO without timezone
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y.%m.%d. %H:%M:%S",  # Added dot after day, space before H:M:S
        "%Y.%m.%d %H:%M:%S",  # Original
        "%Y.%m.%d.",  # Format like "2024. 7. 3." (with trailing dot)
        "%Y. %m. %d.",  # Format like "2024. 7. 3." (with spaces and trailing dot)
        "%Y.%m.%d",  # Original
        "%Y-%m-%d",
        "%Y년 %m월 %d일",  # Korean format "YYYY년 MM월 DD일"
        # English formats
        "%b %d, %Y",  # e.g., Apr 16, 2025
        "%B %d, %Y",  # e.g., April 16, 2025
        "%m/%d/%Y",  # e.g., 04/16/2025
        "%d %b %Y",  # e.g., 16 Apr 2025
        "%d %B %Y",  # e.g., 16 April 2025
    ]

    for fmt in common_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # If parsed successfully but naive, make it timezone-aware (assume UTC)
            if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue

    # 5. If we've reached here, we couldn't parse the date
    return None


def extract_source_and_date(source_date_str: str) -> Tuple[str, Optional[str]]:
    """
    'source, date' 형식의 문자열에서 소스와 날짜를 분리합니다.

    Args:
        source_date_str: 소스와 날짜 정보가 포함된 문자열 (예: "언론사, 2시간 전")

    Returns:
        (source, date_str) 튜플. 날짜가 없으면 (source, None) 반환
    """
    # 날짜 패턴 정의
    date_patterns = [
        # 상대적 시간 (한국어)
        r"\d+시간 전",
        r"\d+분 전",
        r"\d+일 전",
        r"어제",
        r"오늘",
        # 상대적 시간 (영어)
        r"\d+ hours? ago",
        r"\d+ minutes? ago",
        r"\d+ days? ago",
        r"\d+ weeks? ago",
        r"\d+ months? ago",
        # ISO 형식
        r"\d{4}-\d{2}-\d{2}",
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
    ]

    # 기본 값 설정
    source = source_date_str
    date_str = None

    # 쉼표로 구분된 경우 처리
    if "," in source_date_str:
        parts = source_date_str.split(",", 1)
        if len(parts) > 1 and parts[0].strip() and parts[1].strip():
            source = parts[0].strip()
            date_part = parts[1].strip()

            # 날짜 부분에서 패턴 매칭
            for pattern in date_patterns:
                match = re.search(pattern, date_part)
                if match:
                    date_str = match.group(0)
                    break

            # 패턴 매칭에 실패한 경우 전체 날짜 부분 반환
            if date_str is None:
                date_str = date_part
    else:
        # 쉼표가 없는 경우, 텍스트에서 날짜 패턴 직접 검색
        for pattern in date_patterns:
            match = re.search(pattern, source_date_str)
            if match:
                date_str = match.group(0)
                # 날짜 부분을 제외한 나머지를 소스로 설정
                source = source_date_str.replace(date_str, "").strip()
                # 끝에 남은 쉼표나 공백 제거
                source = source.rstrip(",").strip()
                break

    return source, date_str


def format_date_for_display(
    date_obj: Optional[datetime] = None, date_str: Optional[str] = None
) -> str:
    """
    날짜를 표시용으로 포맷팅합니다.
    날짜가 24시간 이내이면 상대적 시간 정보를 추가합니다.

    Args:
        date_obj: 표시할 datetime 객체
        date_str: 날짜 객체가 없을 경우 파싱할 날짜 문자열

    Returns:
        표준화된 날짜 문자열 (YYYY-MM-DD 형식, 필요시 상대 시간 추가)
    """
    if date_obj is None and date_str:
        date_obj = parse_date_string(date_str)

    if date_obj is None:
        return ""

    # 현재 시간 기준 상대적 시간 계산
    now = datetime.now(timezone.utc)

    # datetime 객체가 timezone을 가지고 있는지 확인
    if date_obj.tzinfo is None or date_obj.tzinfo.utcoffset(date_obj) is None:
        date_obj = date_obj.replace(tzinfo=timezone.utc)

    # 현재 시간도 timezone을 가지고 있는지 확인
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        now = now.replace(tzinfo=timezone.utc)

    # 표준 날짜 형식 (YYYY-MM-DD)
    standard_date = date_obj.strftime("%Y-%m-%d")

    # 날짜가 24시간 이내인지 확인
    time_diff = now - date_obj
    hours_diff = time_diff.total_seconds() / 3600

    if hours_diff < 24:
        if hours_diff < 1:
            # 1시간 이내 -> 분 단위
            minutes = int(time_diff.total_seconds() / 60)
            return f"{standard_date} ({minutes}분 전)"
        else:
            # 24시간 이내 -> 시간 단위
            hours = int(hours_diff)
            return f"{standard_date} ({hours}시간 전)"

    # 24시간 이상 -> 날짜만 표시
    return standard_date


def standardize_date(date_str: Any) -> str:
    """
    임의의 날짜 형식을 표준 ISO 형식(YYYY-MM-DD)으로 변환합니다.
    이 함수는 데이터 저장용 표준 날짜 형식을 생성합니다.

    Args:
        date_str: 변환할 날짜 문자열

    Returns:
        표준화된 날짜 문자열 (YYYY-MM-DD 형식) 또는 빈 문자열
    """
    dt = parse_date_string(date_str)
    if dt:
        return dt.strftime("%Y-%m-%d")
    return ""
