#!/usr/bin/env python3
"""Enhanced Build script for standalone executable using PyInstaller hooks.

This script now uses centralized PyInstaller hooks for dependency management,
making the build process cleaner and easier to maintain.
"""

import os
import shutil
import PyInstaller.__main__


def build():
    project_root = os.path.abspath(os.path.dirname(__file__))
    os.chdir(project_root)
    
    # Debug mode control via environment variable
    debug_enabled = os.getenv('PYI_DEBUG', '').lower() in ['true', '1', 'yes']

    # Note: Data files are now managed by PyInstaller hooks
    # See pyinstaller_hooks/hook-newsletter.py for all data file configurations

    # Note: Hidden imports are now managed by PyInstaller hooks
    # See pyinstaller_hooks/hook-newsletter.py for all hidden import configurations

    # PyInstaller 인수 구성
    args = [
        os.path.join("web", "app.py"),
        "--onefile",
        "--name", "newsletter_web",
        "--console",  # 디버깅을 위해 콘솔 창 표시
        
        # Use PyInstaller hooks directory
        "--additional-hooks-dir", "pyinstaller_hooks",
        
        # Runtime hooks
        "--runtime-hook", "web/runtime_hook.py",
    ]

    # Note: Hidden imports and data files are now handled by hooks
    # This reduces the complexity of this build script significantly

    # 추가 옵션들
    additional_args = [
        "--noconfirm",  # 덮어쓰기 확인 안 함
        "--clean",  # 이전 빌드 정리
        "--distpath", "dist",  # 출력 디렉토리
        "--workpath", "build",  # 작업 디렉토리
        
        # 메모리 및 성능 최적화
        "--optimize", "2",  # Python 최적화 레벨
        
        # Debug options (controlled by PYI_DEBUG environment variable)
        # Note: --debug imports can cause excessive console output during runtime
        
        # UPX 압축 비활성화 (안정성을 위해)
        "--noupx",
        
        # Minimize console output (use ERROR to reduce PyiFrozenFinder logs)
        "--log-level", "ERROR",
    ]
    
    # Add debug options conditionally
    if debug_enabled:
        additional_args.extend(["--debug", "imports"])
        print("[DEBUG] PyInstaller debug mode enabled (imports)")
    else:
        print("[INFO] PyInstaller debug mode disabled (set PYI_DEBUG=true to enable)")
    
    args.extend(additional_args)

    print("[INFO] Starting PyInstaller build with hooks...")
    print(f"[INFO] Using hooks directory: pyinstaller_hooks/")
    print(f"[INFO] Build arguments: {len(args)} total")
    
    # 빌드 실행
    PyInstaller.__main__.run(args)

    print("[SUCCESS] PyInstaller build completed!")

    # 빌드 후 필요한 외부 파일들을 dist 디렉토리에 복사
    copy_external_files_to_dist()

    print("[SUCCESS] Enhanced build process completed successfully!")
    print("[INFO] You can now run: .\\dist\\newsletter_web.exe")


def copy_external_files_to_dist():
    """빌드 후 필요한 외부 파일들을 dist 디렉토리에 복사합니다."""
    project_root = os.path.abspath(os.path.dirname(__file__))
    dist_dir = os.path.join(project_root, "dist")

    # 복사할 파일 및 디렉토리 목록 (확장됨)
    files_to_copy = [
        # 환경 설정 파일들
        (".env", ".env"),
        (".env.example", ".env.example"), 
        ("config.yml", "config.yml"),
        
        # Config 디렉토리 전체
        ("config", "config"),
        
        # 템플릿 파일들 (외부 수정 가능하도록)
        ("templates", "templates"),
        
        # 필수 문서들
        ("README.md", "README.md"),
        ("requirements.txt", "requirements.txt"),
        
        # 로깅 및 출력 디렉토리 생성을 위한 빈 디렉토리들
        ("output", "output"),
        ("logs", "logs"), 
    ]

    print("[INFO] Copying external files to dist directory...")

    for src, dest in files_to_copy:
        src_path = os.path.join(project_root, src)
        dest_path = os.path.join(dist_dir, dest)

        if os.path.exists(src_path):
            try:
                if os.path.isdir(src_path):
                    # 디렉토리 복사
                    if os.path.exists(dest_path):
                        shutil.rmtree(dest_path)
                    shutil.copytree(src_path, dest_path)
                    print(f"  [OK] Copied directory: {src} -> dist/{dest}")
                else:
                    # 파일 복사
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.copy2(src_path, dest_path)
                    print(f"  [OK] Copied file: {src} -> dist/{dest}")
            except Exception as e:
                print(f"  [ERROR] Failed to copy {src}: {e}")
        else:
            # 존재하지 않는 디렉토리는 빈 디렉토리로 생성
            if src in ["output", "logs"]:
                os.makedirs(dest_path, exist_ok=True)
                print(f"  [OK] Created directory: dist/{dest}")
            else:
                print(f"  [WARNING] Source not found: {src}")

    # 추가: 실행 가이드 파일 생성
    guide_content = """
# Newsletter Generator 실행 가이드

## 1. 환경 변수 설정
.env 파일을 편집하여 필요한 API 키들을 설정하세요:
- SERPER_API_KEY: 뉴스 검색용
- GEMINI_API_KEY 또는 OPENAI_API_KEY: AI 처리용
- POSTMARK_SERVER_TOKEN: 이메일 발송용
- EMAIL_SENDER: 발송자 이메일

## 2. 실행
newsletter_web.exe

## 3. 웹 인터페이스 접속
http://localhost:5000

## 4. 문제 해결
- 로그 파일: logs/ 디렉토리 확인
- 생성된 뉴스레터: output/ 디렉토리 확인
- 환경 변수 문제: .env 파일 확인
"""
    
    try:
        guide_path = os.path.join(dist_dir, "실행가이드.txt")
        with open(guide_path, "w", encoding="utf-8") as f:
            f.write(guide_content.strip())
        print("  [SUCCESS] Created execution guide: dist/실행가이드.txt")
    except Exception as e:
        print(f"  [WARNING] Failed to create execution guide: {e}")

    print("[SUCCESS] External files copy completed!")


if __name__ == "__main__":
    build()