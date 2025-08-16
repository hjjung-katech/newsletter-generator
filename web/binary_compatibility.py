"""
Binary Compatibility Module
PyInstaller 바이너리 환경에서의 호환성을 위한 유틸리티들
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Setup logger
logger = logging.getLogger(__name__)


def is_frozen() -> bool:
    """PyInstaller로 빌드된 바이너리에서 실행 중인지 확인"""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_base_path() -> str:
    """실행 환경에 따른 기본 경로 반환"""
    if is_frozen():
        # PyInstaller 바이너리 환경
        return sys._MEIPASS
    else:
        # 일반 Python 개발 환경
        return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(relative_path: str) -> str:
    """리소스 파일의 절대 경로 반환 (바이너리/개발 환경 자동 감지)"""
    base = get_base_path()
    return os.path.join(base, relative_path)


def get_external_resource_path(relative_path: str) -> str:
    """외부 리소스 파일 경로 반환 (바이너리 실행 시 exe와 동일한 디렉토리)"""
    if is_frozen():
        # 바이너리 실행 시: exe 파일과 같은 디렉토리
        exe_dir = os.path.dirname(sys.executable)
        return os.path.join(exe_dir, relative_path)
    else:
        # 개발 환경: 프로젝트 루트
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(project_root, relative_path)


def setup_binary_environment() -> Dict[str, Any]:
    """바이너리 환경 초기 설정 및 상태 반환"""
    env_info = {
        "is_frozen": is_frozen(),
        "base_path": get_base_path(),
        "executable_path": sys.executable if is_frozen() else None,
        "python_path": sys.executable if not is_frozen() else None,
        "working_directory": os.getcwd(),
        "paths_configured": False,
        "environment_loaded": False,
    }

    if is_frozen():
        logger.info("PyInstaller 바이너리 환경 감지됨")
        logger.info(f"   Base path: {env_info['base_path']}")
        logger.info(f"   Executable: {env_info['executable_path']}")

        # 바이너리 환경에서 필요한 경로들을 sys.path에 추가
        binary_paths = [
            get_base_path(),
            get_resource_path("newsletter"),
            get_resource_path("web"),
        ]

        for path in binary_paths:
            if os.path.exists(path) and path not in sys.path:
                sys.path.insert(0, path)
                logger.debug(f"   Added to sys.path: {path}")

        env_info["paths_configured"] = True
    else:
        logger.info("Python 개발 환경에서 실행 중")
        logger.info(f"   Working directory: {env_info['working_directory']}")

    return env_info


def load_environment_variables(
    env_files: Optional[List[str]] = None,
) -> Dict[str, bool]:
    """환경 변수 파일들을 로드 (.env 파일들)"""
    if env_files is None:
        env_files = [".env"]

    loaded_files = {}

    for env_file in env_files:
        # 외부 리소스 경로에서 .env 파일 찾기
        env_path = get_external_resource_path(env_file)

        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            try:
                                key, value = line.split("=", 1)
                                key = key.strip()
                                value = value.strip()

                                # 따옴표 제거
                                if value.startswith('"') and value.endswith('"'):
                                    value = value[1:-1]
                                elif value.startswith("'") and value.endswith("'"):
                                    value = value[1:-1]

                                # 환경 변수 설정 (기존 값이 없는 경우만)
                                if key not in os.environ:
                                    os.environ[key] = value

                            except ValueError as e:
                                logger.warning(
                                    f"   Invalid line {line_num} in {env_file}: {e}"
                                )

                loaded_files[env_file] = True
                logger.info(f"Loaded environment file: {env_path}")

            except Exception as e:
                loaded_files[env_file] = False
                logger.error(f"Failed to load {env_path}: {e}")
        else:
            loaded_files[env_file] = False
            logger.warning(f"Environment file not found: {env_path}")

    return loaded_files


def verify_critical_modules() -> Dict[str, bool]:
    """핵심 모듈들의 로드 가능성 검증"""
    critical_modules = {
        # 기본 모듈들
        "flask": False,
        "requests": False,
        "sqlite3": False,
        # 뉴스레터 핵심 모듈들
        "newsletter": False,
        "newsletter.collect": False,
        "newsletter.chains": False,
        "newsletter.llm_factory": False,
        # AI/LLM 모듈들
        "langchain": False,
        "langchain_core": False,
        "langchain_google_genai": False,
        "langchain_openai": False,
        "langchain_anthropic": False,
        "langgraph": False,
        # 유틸리티 모듈들
        "feedparser": False,
        "beautifulsoup4": False,
        "jinja2": False,
        "postmarker": False,
    }

    logger.info("핵심 모듈 가용성 검증 중...")

    for module_name in critical_modules.keys():
        try:
            if module_name == "beautifulsoup4":
                import bs4
            else:
                __import__(module_name)
            critical_modules[module_name] = True
            logger.debug(f"   [OK] {module_name}")
        except ImportError as e:
            critical_modules[module_name] = False
            logger.error(f"   {module_name}: {e}")
        except Exception as e:
            critical_modules[module_name] = False
            logger.warning(f"   {module_name}: {e}")

    # 결과 요약
    available_count = sum(critical_modules.values())
    total_count = len(critical_modules)
    success_rate = (available_count / total_count) * 100

    logger.info(f"모듈 가용성: {available_count}/{total_count} ({success_rate:.1f}%)")

    # 필수 모듈 체크
    essential_modules = ["flask", "requests", "newsletter"]
    missing_essential = [m for m in essential_modules if not critical_modules.get(m)]

    if missing_essential:
        logger.warning(f"필수 모듈 누락: {missing_essential}")
        return False

    return critical_modules


def create_necessary_directories() -> List[str]:
    """필요한 디렉토리들 생성"""
    directories = [
        "output",
        "logs",
        "temp",
        "cache",
    ]

    created_dirs = []
    base_path = get_external_resource_path("")

    for dir_name in directories:
        dir_path = os.path.join(base_path, dir_name)
        try:
            os.makedirs(dir_path, exist_ok=True)
            created_dirs.append(dir_path)
            logger.debug(f"Directory ready: {dir_path}")
        except Exception as e:
            logger.error(f"Failed to create directory {dir_path}: {e}")

    return created_dirs


def setup_logging_for_binary():
    """바이너리 환경에 맞는 로깅 설정"""
    log_dir = get_external_resource_path("logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "newsletter_web.log")

    # 기본 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger.info(f"Logging configured: {log_file}")
    return log_file


def run_comprehensive_diagnostics() -> Dict[str, Any]:
    """종합 진단 실행"""
    logger.info("=== 바이너리 호환성 종합 진단 시작 ===")

    # 1. 환경 설정
    env_info = setup_binary_environment()

    # 2. 로깅 설정
    log_file = setup_logging_for_binary()

    # 3. 환경 변수 로드
    env_loaded = load_environment_variables()
    env_info["environment_loaded"] = any(env_loaded.values())

    # 4. 디렉토리 생성
    created_dirs = create_necessary_directories()

    # 5. 모듈 검증
    module_status = verify_critical_modules()

    # 6. 결과 종합
    diagnostics_result = {
        "environment_info": env_info,
        "log_file": log_file,
        "environment_files_loaded": env_loaded,
        "directories_created": created_dirs,
        "module_availability": module_status,
        "overall_status": (
            "ready"
            if env_info["paths_configured"] and any(env_loaded.values())
            else "partial"
        ),
    }

    logger.info("=== 바이너리 호환성 진단 완료 ===")
    logger.info(f"전체 상태: {diagnostics_result['overall_status'].upper()}")

    return diagnostics_result


# 자동 초기화 (모듈이 import될 때 실행)
if __name__ == "__main__":
    run_comprehensive_diagnostics()
