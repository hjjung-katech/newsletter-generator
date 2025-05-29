"""
Utilities for running the newsletter generator in test mode.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def load_intermediate_data(file_path: str) -> Dict[str, Any]:
    """
    Load intermediate data from a JSON file for testing.

    Args:
        file_path: Path to the intermediate data JSON file

    Returns:
        Dictionary containing the loaded data
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Successfully loaded intermediate data from {file_path}")
        return data
    except Exception as e:
        logger.error(f"Failed to load intermediate data from {file_path}: {e}")
        raise


def save_intermediate_data(
    data: Dict[str, Any], file_path: str, config_params: Optional[Dict[str, Any]] = None
) -> None:
    """
    Save intermediate data to a JSON file for future testing.

    Args:
        data: Dictionary containing the newsletter data to save
        file_path: Path where the data should be saved
        config_params: Optional configuration parameters to embed in the same file
    """
    try:
        # Create a copy to avoid modifying the original data
        data_to_save = data.copy()

        # Add test config if provided
        if config_params:
            data_to_save["_test_config"] = config_params

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully saved intermediate data to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save intermediate data to {file_path}: {e}")
        raise


def extract_config_from_data(
    data: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Extract embedded test configuration from render data if present.

    Args:
        data: Dictionary containing loaded data that may have embedded configuration

    Returns:
        Tuple of (content_data, config_data) where:
        - content_data is the newsletter content data without the config
        - config_data is the extracted configuration (empty dict if none exists)
    """
    # Create a copy so we don't modify the original
    content_data = data.copy()
    config_data = {}

    # Extract test config if present
    if "_test_config" in content_data:
        config_data = content_data.pop("_test_config")
        logger.info("Found embedded test configuration in data file")

    return content_data, config_data


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
    import datetime

    if not timestamp:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # 출력 디렉토리 경로
    output_dir = os.path.join("output")
    os.makedirs(output_dir, exist_ok=True)

    # 주제를 파일 이름으로 사용 가능하게 변환
    import re

    safe_topic = re.sub(r"[^\w\s-]", "", topic)
    safe_topic = re.sub(r"[-\s]+", "_", safe_topic)
    safe_topic = safe_topic[:50].strip("_")

    # 파일 이름 구성
    current_date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    if safe_topic:
        filename = f"{current_date_str}_{timestamp}_newsletter_{safe_topic}.html"
    else:
        filename = f"{current_date_str}_{timestamp}_newsletter.html"

    return os.path.join(output_dir, filename)


def run_in_test_mode(data_file: str, output_html_path: Optional[str] = None) -> str:
    """
    Run the newsletter generator in test mode using cached intermediate data.

    Args:
        data_file: Path to the intermediate data file (with optional embedded config)
        output_html_path: Optional path for the output HTML file

    Returns:
        Path to the generated HTML file
    """
    # 실제 템플릿 렌더링을 위해 필요한 모듈 임포트
    import datetime
    import os

    from ..compose import compose_newsletter_html

    # Load data file
    data = load_intermediate_data(data_file)

    # Extract config if present (we may not use it now, but it's ready if needed)
    content_data, config_data = extract_config_from_data(data)

    # 타임스탬프 추출 로직 개선
    timestamp = None
    timestamp_format = "%Y%m%d_%H%M%S"

    # 1. 파일명에서 타임스탬프 추출 시도
    try:
        file_basename = os.path.basename(data_file)
        parts = file_basename.split("_")
        if len(parts) >= 3 and parts[0] == "render" and parts[1] == "data":
            # render_data_YYYYMMDD_HHMMSS 형식에서 추출
            timestamp = parts[2]

            # YYYYMMDD 형식이라면 시간 부분 추가 (기본값 000000)
            if len(timestamp) == 8 and timestamp.isdigit():
                timestamp = f"{timestamp}_000000"

            logger.info(f"Extracted timestamp from filename: {timestamp}")
    except Exception as e:
        logger.warning(f"Failed to extract timestamp from filename: {e}")

    # 2. 설정 데이터에서 타임스탬프 확인
    if not timestamp and config_data.get("timestamp"):
        timestamp = config_data.get("timestamp")
        logger.info(f"Using timestamp from config: {timestamp}")

    # 3. 콘텐츠 데이터에서 타임스탬프 확인
    generation_timestamp = None
    if not timestamp and content_data.get("generation_timestamp"):
        generation_timestamp = content_data.get("generation_timestamp")
        # HH:MM:SS 형식을 HHMMSS로 변환
        if ":" in generation_timestamp:
            hour, minute, second = generation_timestamp.split(":")
            timestamp_time = f"{hour}{minute}{second}"
            # 날짜 부분 추가 (YYYYMMDD)
            generation_date = content_data.get(
                "generation_date", datetime.datetime.now().strftime("%Y-%m-%d")
            )
            # 2025-05-16 형식을 20250516으로 변환
            if "-" in generation_date:
                year, month, day = generation_date.split("-")
                timestamp_date = f"{year}{month}{day}"
                timestamp = f"{timestamp_date}_{timestamp_time}"
                logger.info(f"Created timestamp from date and time: {timestamp}")

    # 4. 현재 시간으로 타임스탬프 생성 (기본값)
    if not timestamp:
        timestamp = datetime.datetime.now().strftime(timestamp_format)
        logger.info(f"Using current time as timestamp: {timestamp}")

    # 생성 날짜와 시간을 content_data에 설정
    if "generation_date" not in content_data:
        # 2025-05-16 형식으로 변환
        if timestamp and len(timestamp) >= 8:
            date_part = timestamp.split("_")[0] if "_" in timestamp else timestamp[:8]
            if len(date_part) == 8:
                content_data["generation_date"] = (
                    f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
                )

        if "generation_date" not in content_data:
            content_data["generation_date"] = datetime.datetime.now().strftime(
                "%Y-%m-%d"
            )

    if "generation_timestamp" not in content_data:
        # HH:MM:SS 형식으로 변환
        if timestamp and "_" in timestamp:
            time_part = timestamp.split("_")[1]
            if len(time_part) >= 6:
                content_data["generation_timestamp"] = (
                    f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
                )

        if "generation_timestamp" not in content_data:
            content_data["generation_timestamp"] = datetime.datetime.now().strftime(
                "%H:%M:%S"
            )

    # 템플릿 렌더링에 필요한 추가 데이터 설정
    if "title_prefix" not in content_data:
        content_data["title_prefix"] = "주간 산업 동향 뉴스 클리핑"

    if "company_name" not in content_data:
        content_data["company_name"] = "산업통상자원 R&D 전략기획단"

    if "primary_color" not in content_data:
        content_data["primary_color"] = "#3498db"

    if "secondary_color" not in content_data:
        content_data["secondary_color"] = "#2c3e50"

    if "font_family" not in content_data:
        content_data["font_family"] = "Malgun Gothic, sans-serif"

    # Set output path with the improved timestamp
    if not output_html_path:
        # 통일된 파일명 생성 함수 사용
        from .file_naming import generate_unified_newsletter_filename

        topic = content_data.get("newsletter_topic", "test_newsletter")
        output_html_path = generate_unified_newsletter_filename(
            topic=f"test_{topic}",
            style="detailed",  # 기본 스타일
            timestamp=timestamp,
            use_current_date=True,
            generation_type="test",
        )

    # 템플릿 디렉토리 설정
    current_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    template_dir = os.path.join(current_dir, "templates")
    template_name = "newsletter_template.html"

    # 템플릿 디렉토리 존재 확인
    if not os.path.exists(template_dir):
        logger.warning(f"Template directory not found: {template_dir}")
        os.makedirs(template_dir, exist_ok=True)

    # 템플릿 파일 존재 확인
    template_path = os.path.join(template_dir, template_name)
    if not os.path.exists(template_path):
        logger.warning(f"Template file not found: {template_path}")
        # 기본 템플릿 생성
        with open(template_path, "w", encoding="utf-8") as f:
            f.write(
                """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>{{ title_prefix }} ({{ newsletter_topic }} - {{ generation_date }} {{ generation_timestamp }})</title>
</head>
<body>
    <h1>{{ newsletter_topic }}</h1>
    <p>Generated from test data: {{ data_file }}</p>
    <p>Generated at: {{ generation_date }} {{ generation_timestamp }}</p>
</body>
</html>"""
            )

    # 실제 템플릿 렌더링 수행
    try:
        html_content = compose_newsletter_html(
            content_data, template_dir, template_name
        )

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_html_path), exist_ok=True)

        # Write HTML content to file
        with open(output_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Test mode completed. Generated newsletter at {output_html_path}")
        return output_html_path
    except Exception as e:
        logger.error(f"Failed to render newsletter HTML: {e}")
        # 예외 발생 시 기본 HTML 생성
        basic_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{content_data.get('newsletter_topic', 'Test Newsletter')}</title>
</head>
<body>
    <h1>{content_data.get('newsletter_topic', 'Test Newsletter')}</h1>
    <p>Generated from test data: {data_file}</p>
    <p>Generated at: {timestamp}</p>
    <p>Error occurred during rendering: {str(e)}</p>
</body>
</html>"""

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_html_path), exist_ok=True)

        # Write basic HTML content to file
        with open(output_html_path, "w", encoding="utf-8") as f:
            f.write(basic_html)

        logger.info(f"Fallback HTML generated at {output_html_path} due to error")
        return output_html_path
