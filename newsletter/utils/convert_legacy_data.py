"""
Legacy 데이터 파일을 새로운 통합 형식으로 변환하는 유틸리티
"""

import argparse
import json
import logging
import os
from datetime import datetime
from glob import glob
from typing import Any, Dict, List, Optional

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_legacy_data(file_path: str) -> Dict[str, Any]:
    """
    레거시 데이터 파일 로드

    Args:
        file_path: 데이터 파일 경로

    Returns:
        로드된 데이터 딕셔너리
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Successfully loaded data from {file_path}")
        return data
    except Exception as e:
        logger.error(f"Failed to load data from {file_path}: {e}")
        raise


def extract_metadata_from_legacy(
    data: Dict[str, Any], file_path: str
) -> Dict[str, Any]:
    """
    레거시 데이터에서 메타데이터 추출

    Args:
        data: 레거시 데이터 딕셔너리
        file_path: 원본 파일 경로 (메타데이터 추출에 사용)

    Returns:
        통합형 데이터를 위한 _test_config 섹션
    """
    # 파일 이름에서 타임스탬프 추출 시도
    timestamp = None
    try:
        filename = os.path.basename(file_path)
        parts = filename.split("_")
        if len(parts) >= 3 and parts[0] == "render" and parts[1] == "data":
            timestamp = parts[2]
        else:
            # render_data_{timestamp}.json 형식이 아니면 현재 시간 사용
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    except Exception:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 뉴스레터 주제 추출
    topic = data.get("newsletter_topic", "")

    # 키워드 목록 추출
    keywords = []
    if "search_keywords" in data:
        if isinstance(data["search_keywords"], list):
            keywords = data["search_keywords"]
        elif isinstance(data["search_keywords"], str):
            keywords = [
                k.strip() for k in data["search_keywords"].split(",") if k.strip()
            ]

    # 언어 정보 (기본값 ko)
    language = data.get("language", "ko")

    # 데이터 수집 기간 (일 단위, 기본값 7)
    date_range = data.get("date_range", 7)

    # 테스트 구성 메타데이터 생성
    test_config = {
        "timestamp": timestamp,
        "keywords": keywords,
        "topic": topic,
        "language": language,
        "date_range": date_range,
    }

    return test_config


def convert_to_unified_format(data: Dict[str, Any], file_path: str) -> Dict[str, Any]:
    """
    레거시 데이터를 통합 형식으로 변환

    Args:
        data: 레거시 데이터
        file_path: 원본 파일 경로

    Returns:
        통합 형식의 데이터
    """
    # 이미 통합 형식인지 확인
    if "_test_config" in data:
        logger.info("File is already in unified format")
        return data

    # 메타데이터 추출
    test_config = extract_metadata_from_legacy(data, file_path)

    # 데이터 복사 후 테스트 구성 추가
    unified_data = data.copy()
    unified_data["_test_config"] = test_config

    return unified_data


def convert_file(input_file: str, output_file: Optional[str] = None) -> str:
    """
    단일 파일을 통합 형식으로 변환

    Args:
        input_file: 입력 파일 경로
        output_file: 출력 파일 경로 (지정하지 않으면 자동 생성)

    Returns:
        출력 파일 경로
    """
    # 데이터 로드
    data = load_legacy_data(input_file)

    # 통합 형식으로 변환
    unified_data = convert_to_unified_format(data, input_file)

    # 출력 경로 결정
    if not output_file:
        base_name, ext = os.path.splitext(input_file)
        output_file = f"{base_name}_unified{ext}"

    # 출력 디렉토리 생성
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # 변환된 데이터 저장
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(unified_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Successfully saved unified data to {output_file}")
    return output_file


def convert_directory(directory_path: str, recursive: bool = False) -> List[str]:
    """
    디렉토리 내 모든 render_data 파일을 변환

    Args:
        directory_path: 디렉토리 경로
        recursive: 하위 디렉토리도 처리할지 여부

    Returns:
        변환된 파일 경로 목록
    """
    # 변환할 파일 찾기
    pattern = os.path.join(
        directory_path, "**" if recursive else "", "render_data_*.json"
    )
    files = glob(pattern, recursive=recursive)

    # 변환된 파일 경로 저장용
    converted_files = []

    # 각 파일 변환
    for file_path in files:
        # 이미 변환된 파일은 건너뛰기
        if "_unified" in file_path:
            continue

        try:
            output_path = convert_file(file_path)
            converted_files.append(output_path)
        except Exception as e:
            logger.error(f"Failed to convert {file_path}: {e}")

    return converted_files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert legacy render_data files to unified format"
    )
    parser.add_argument("input", help="Input file or directory path")
    parser.add_argument(
        "--output", help="Output file path (for single file conversion)"
    )
    parser.add_argument(
        "--recursive", action="store_true", help="Process subdirectories"
    )

    args = parser.parse_args()

    if os.path.isdir(args.input):
        converted = convert_directory(args.input, args.recursive)
        logger.info(f"Converted {len(converted)} files")
    else:
        output = convert_file(args.input, args.output)
        logger.info(f"Converted file saved to {output}")
