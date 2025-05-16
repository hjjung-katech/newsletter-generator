"""
Utilities for running the newsletter generator in test mode.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

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
    # Load data file
    data = load_intermediate_data(data_file)

    # Extract config if present (we may not use it now, but it's ready if needed)
    content_data, config_data = extract_config_from_data(data)

    # Determine generation timestamp
    timestamp = (
        config_data.get("timestamp", None)
        or content_data.get("generation_timestamp", None)
        or os.path.basename(data_file).split("_")[2]
        if "_" in os.path.basename(data_file)
        else None
    )

    # Set output path
    if not output_html_path:
        output_html_path = generate_newsletter_filename(
            content_data.get("newsletter_topic", "test_newsletter"), timestamp
        )

    # Here you would integrate with your HTML generation logic
    # For now, we'll create a very basic HTML file as a placeholder
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{content_data.get('newsletter_topic', 'Test Newsletter')}</title>
</head>
<body>
    <h1>{content_data.get('newsletter_topic', 'Test Newsletter')}</h1>
    <p>Generated from test data: {data_file}</p>
    <p>Generated at: {timestamp}</p>
</body>
</html>"""

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_html_path), exist_ok=True)

    # Write HTML content to file
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info(f"Test mode completed. Generated newsletter at {output_html_path}")
    return output_html_path
