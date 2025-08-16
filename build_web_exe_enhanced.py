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
    debug_enabled = os.getenv("PYI_DEBUG", "").lower() in ["true", "1", "yes"]

    # Note: Data files are now managed by PyInstaller hooks
    # See pyinstaller_hooks/hook-newsletter.py for all data file configurations

    # Note: Hidden imports are now managed by PyInstaller hooks
    # See pyinstaller_hooks/hook-newsletter.py for all hidden import configurations

    # PyInstaller 인수 구성
    args = [
        os.path.join("web", "app.py"),
        "--onefile",
        "--name",
        "newsletter_web",
        "--console",  # 디버깅을 위해 콘솔 창 표시
        # Use PyInstaller hooks directory
        "--additional-hooks-dir",
        "pyinstaller_hooks",
        # Runtime hooks
        "--runtime-hook",
        "web/runtime_hook.py",
    ]

    # Note: Hidden imports and data files are now handled by hooks
    # This reduces the complexity of this build script significantly

    # 추가 옵션들
    additional_args = [
        "--noconfirm",  # 덮어쓰기 확인 안 함
        "--clean",  # 이전 빌드 정리
        "--distpath",
        "dist",  # 출력 디렉토리
        "--workpath",
        "build",  # 작업 디렉토리
        # 메모리 및 성능 최적화
        "--optimize",
        "2",  # Python 최적화 레벨
        # Debug options (controlled by PYI_DEBUG environment variable)
        # Note: --debug imports can cause excessive console output during runtime
        # UPX 압축 비활성화 (안정성을 위해)
        "--noupx",
        # Minimize console output (use ERROR to reduce PyiFrozenFinder logs)
        "--log-level",
        "ERROR",
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
    """빌드 후 필수 파일들과 문서들을 dist 디렉토리에 복사합니다.

    CLI 호환성을 위한 기존 파일들과 사용자 가이드 문서들을 포함합니다.
    """
    project_root = os.path.abspath(os.path.dirname(__file__))
    dist_dir = os.path.join(project_root, "dist")

    print("[INFO] Setting up deployment environment with full compatibility...")

    # Step 1: Create .env.example if it doesn't exist
    env_example_path = os.path.join(project_root, ".env.example")
    if not os.path.exists(env_example_path):
        create_env_example(env_example_path)

    # Step 2: Copy essential configuration files
    essential_files = [
        # Environment and configuration files
        (".env.example", ".env.example"),
        (".env", ".env"),  # Copy actual .env file if exists
        ("config.yml", "config.yml"),
        # CLI compatibility - templates and configs (essential for CLI mode)
        ("templates", "templates"),  # Newsletter templates (CLI 호환성)
        ("config", "config"),  # Config directory (CLI 호환성)
        ("newsletter/templates", "newsletter/templates"),  # Newsletter module templates
    ]

    # Step 3: Copy documentation files for user reference (.txt format)
    docs_files = [
        ("web/docs/USER_GUIDE.txt", "사용자가이드.txt"),
        ("web/docs/QUICK_START.txt", "빠른시작가이드.txt"),
    ]

    # Step 4: Create necessary directory structure
    create_directory_structure(dist_dir)

    # Copy essential files
    for src, dest in essential_files:
        src_path = os.path.join(project_root, src)
        dest_path = os.path.join(dist_dir, dest)

        if os.path.exists(src_path):
            try:
                if os.path.isdir(src_path):
                    # Copy directory
                    if os.path.exists(dest_path):
                        shutil.rmtree(dest_path)
                    shutil.copytree(src_path, dest_path)
                    print(f"  [OK] Copied directory: {src} -> {dest}")
                else:
                    # Copy file
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.copy2(src_path, dest_path)
                    print(f"  [OK] Copied file: {src} -> {dest}")
            except Exception as e:
                print(f"  [ERROR] Failed to copy {src}: {e}")
        else:
            print(f"  [WARNING] Not found: {src}")

    # Copy documentation files with port info
    copy_documentation_files(project_root, dist_dir, docs_files)

    # Create user-friendly README
    create_dist_readme(dist_dir)

    print("[SUCCESS] Full deployment setup completed!")
    print("[INFO] Includes CLI compatibility files, templates, and user documentation")
    print("[INFO] Runtime folders will be auto-created on first run")


def create_directory_structure(dist_dir):
    """Create necessary directory structure for the application."""
    directories = [
        "output",
        "logs",
        "config",
        "docs",
        "templates",
        "output/intermediate_processing",
    ]

    for dir_name in directories:
        dir_path = os.path.join(dist_dir, dir_name)
        os.makedirs(dir_path, exist_ok=True)
        print(f"  [OK] Created directory: {dir_name}")


def get_port_info():
    """Get port information from the web app configuration."""
    try:
        # First check .env file for PORT setting
        env_path = os.path.join(os.path.dirname(__file__), "dist", ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()
                for line in content.split("\n"):
                    if line.startswith("PORT="):
                        port_value = line.split("=")[1].strip()
                        if port_value.isdigit():
                            return int(port_value)

        # Fallback to reading from web/app.py
        app_py_path = os.path.join(os.path.dirname(__file__), "web", "app.py")
        if os.path.exists(app_py_path):
            with open(app_py_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Find the port setting line
                for line in content.split("\n"):
                    if 'port = int(os.environ.get("PORT"' in line:
                        # Extract default port number (8000 preferred)
                        if "8000" in line:
                            return 8000
                        elif "5000" in line:
                            return 5000
    except Exception as e:
        print(f"  [WARNING] Could not determine port from config files: {e}")

    # Default fallback (now 8000)
    return 8000


def copy_documentation_files(project_root, dist_dir, docs_files):
    """Copy documentation files with dynamic port information."""
    port = get_port_info()

    print(f"  [INFO] Using port {port} for documentation")

    for src, dest in docs_files:
        src_path = os.path.join(project_root, src)
        dest_path = os.path.join(dist_dir, dest)

        if os.path.exists(src_path):
            try:
                with open(src_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Replace port information dynamically
                content = content.replace(
                    "http://localhost:5000", f"http://localhost:{port}"
                )
                content = content.replace(
                    "http://127.0.0.1:5000", f"http://127.0.0.1:{port}"
                )

                # Add current build information
                from datetime import datetime

                build_info = f"""---
**빌드 정보:**
- 생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 웹 포트: {port}
- 버전: Newsletter Generator Web
---

"""
                content = build_info + content

                with open(dest_path, "w", encoding="utf-8") as f:
                    f.write(content)

                print(f"  [OK] Created documentation: {dest} (with port {port})")

            except Exception as e:
                print(f"  [ERROR] Failed to copy documentation {src}: {e}")
        else:
            print(f"  [WARNING] Documentation not found: {src}")


def create_env_example(env_example_path):
    """Create a template .env.example file with all necessary API keys."""
    env_template = """# Newsletter Generator Configuration
# Copy this file to .env and configure your API keys

# === Required API Keys ===
# Get your Gemini API key from https://aistudio.google.com/
GEMINI_API_KEY=your_gemini_api_key_here

# Get your Serper API key from https://serper.dev/
SERPER_API_KEY=your_serper_api_key_here

# === Optional API Keys ===
# OpenAI API (alternative to Gemini)
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic Claude API (alternative to Gemini)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# === Email Configuration ===
# Get Postmark token from https://postmarkapp.com/
POSTMARK_SERVER_TOKEN=your_postmark_server_token_here
EMAIL_SENDER=your_email@example.com

# === Optional Services ===
# Google Cloud credentials for Drive upload
GOOGLE_APPLICATION_CREDENTIALS=path/to/google-credentials.json

# Naver API (for Korean news)
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret

# === Application Settings ===
# Set to true to enable mock mode for testing
MOCK_MODE=false

# Redis URL for background job processing (optional)
REDIS_URL=redis://localhost:6379/0
"""

    try:
        with open(env_example_path, "w", encoding="utf-8") as f:
            f.write(env_template)
        print(f"  [OK] Created .env.example template")
    except Exception as e:
        print(f"  [ERROR] Failed to create .env.example: {e}")


def create_dist_readme(dist_dir):
    """Create a simple README file for the distribution with dynamic port info."""
    port = get_port_info()

    readme_content = f"""# Newsletter Generator

AI 기반 뉴스레터 생성 도구입니다.

## 🚀 빠른 시작

1. **API 키 설정**:
   - `.env.example`을 `.env`로 복사
   - 필요한 API 키들을 설정

2. **프로그램 실행**:
   ```
   newsletter_web.exe
   ```

3. **웹 접속**:
   http://localhost:{port}

## 📚 문서

함께 제공되는 문서들:
- `빠른시작가이드.txt`: 5분 안에 첫 뉴스레터 생성
- `사용자가이드.txt`: 전체 기능 상세 설명

프로그램 실행 후 웹 인터페이스에서도 도움말을 확인할 수 있습니다.

## 🔑 필수 API 키

- **Gemini API**: AI 뉴스레터 생성 (https://aistudio.google.com/)
- **Serper API**: 뉴스 검색 (https://serper.dev/)

## 📁 폴더 구조

프로그램에 포함된 폴더들:
- `templates/`: 뉴스레터 템플릿 (CLI 호환성)
- `config/`: 설정 파일들
- `newsletter/templates/`: 내부 템플릿들

실행 후 자동 생성되는 폴더들:
- `output/`: 생성된 뉴스레터 저장
- `logs/`: 프로그램 실행 로그

## 🆘 문제 해결

문제가 있으면:
1. `logs/` 폴더의 최신 로그 파일 확인
2. `빠른시작가이드.txt` 문제해결 섹션 참조
3. `.env` 파일의 API 키 확인
"""

    try:
        readme_path = os.path.join(dist_dir, "README.txt")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content.strip())
        print(f"  [OK] Created README.txt with port {port}")
    except Exception as e:
        print(f"  [WARNING] Failed to create README.txt: {e}")


if __name__ == "__main__":
    build()
