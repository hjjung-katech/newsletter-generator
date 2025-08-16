"""
안전한 subprocess 실행을 위한 유틸리티
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional


def get_executable_path(cmd: str) -> str:
    """
    명령어의 전체 경로를 안전하게 찾음

    Args:
        cmd: 실행할 명령어

    Returns:
        명령어의 전체 경로

    Raises:
        ValueError: 명령어를 찾을 수 없는 경우
    """
    path = shutil.which(cmd)
    if not path:
        raise ValueError(f"명령어를 찾을 수 없습니다: {cmd}")
    return path


# Bandit B404/B603: subprocess 사용 - 입력값(cmd)은 반드시 신뢰된 값만 전달할 것 (보안 검증됨)
def run_command_safely(
    cmd: List[str],
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    **kwargs,
) -> subprocess.CompletedProcess:
    """
    명령어를 안전하게 실행

    Args:
        cmd: 실행할 명령어와 인자들
        cwd: 작업 디렉토리
        env: 환경 변수
        timeout: 타임아웃 (초)
        **kwargs: subprocess.run에 전달할 추가 인자

    Returns:
        실행 결과

    Raises:
        subprocess.SubprocessError: 명령어 실행 실패시
        ValueError: 잘못된 명령어
    """
    if not cmd:
        raise ValueError("명령어가 비어있습니다")

    # 실행 파일의 전체 경로 확인
    executable = get_executable_path(cmd[0])
    safe_cmd = [executable] + cmd[1:]

    # 작업 디렉토리가 존재하는지 확인
    if cwd:
        cwd = str(Path(cwd).resolve())
        if not os.path.isdir(cwd):
            raise ValueError(f"작업 디렉토리가 존재하지 않습니다: {cwd}")

    # 환경 변수 복사 및 업데이트
    safe_env = os.environ.copy()
    if env:
        safe_env.update(env)

    return subprocess.run(
        safe_cmd, cwd=cwd, env=safe_env, timeout=timeout, check=True, **kwargs
    )
