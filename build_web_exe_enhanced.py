#!/usr/bin/env python3
"""Enhanced Build script for standalone executable with comprehensive hidden imports.

This script addresses all the missing dependencies that cause the EXE to fail
after news scraping, particularly LangChain and related AI modules.
"""

import os
import shutil
import PyInstaller.__main__


def build():
    project_root = os.path.abspath(os.path.dirname(__file__))
    os.chdir(project_root)

    # PyInstaller 빌드에 포함할 내부 데이터 (exe 내부에 번들)
    datas = [
        f"{os.path.join(project_root, 'templates')}{os.pathsep}templates",
        f"{os.path.join(project_root, 'web', 'templates')}{os.pathsep}templates",
        f"{os.path.join(project_root, 'web', 'static')}{os.pathsep}static",
        f"{os.path.join(project_root, 'web', 'web_types.py')}{os.pathsep}web",
        f"{os.path.join(project_root, 'newsletter')}{os.pathsep}newsletter",  # newsletter 패키지 전체
        f"{os.path.join(project_root, 'config.yml')}{os.pathsep}.",  # config 파일
        f"{os.path.join(project_root, 'config')}{os.pathsep}config",  # config 디렉토리
        f"{os.path.join(project_root, '.env')}{os.pathsep}.",  # 환경 설정 파일 (중요!)
    ]

    # 📋 COMPREHENSIVE HIDDEN IMPORTS
    # 기본 필수 모듈들
    basic_imports = [
        # Web Framework
        "flask", "flask_cors", "werkzeug", "jinja2", "jinja2.runtime", "jinja2.loaders", "jinja2.utils",
        
        # Database & Storage
        "sqlite3", "redis", "rq", "rq.worker", "rq.job", "rq.queue",
        
        # Configuration & Environment
        "pydantic", "pydantic_settings", "python_dotenv", "dotenv",
        "yaml", "PyYAML",
        
        # HTTP & Web Scraping
        "requests", "requests.adapters", "urllib3", "urllib3.util.retry",
        "beautifulsoup4", "bs4", "feedparser",
        
        # Date & Time
        "dateutil", "dateutil.rrule", "dateutil.parser", "dateutil.tz",
        
        # Utilities
        "rich", "rich.console", "typer", "uuid", "json", "re", "time",
        "threading", "multiprocessing", "concurrent.futures",
    ]

    # 🤖 AI/LLM Core Modules (가장 중요!)
    ai_core_imports = [
        # LangChain Core
        "langchain", "langchain_core", "langchain_community",
        "langchain.callbacks", "langchain.callbacks.base",
        "langchain.prompts", "langchain.tools", "langchain.chains",
        "langchain.llms", "langchain.chat_models",
        "langchain_core.messages", "langchain_core.output_parsers", 
        "langchain_core.runnables", "langchain_core.tools",
        "langchain_core.outputs", "langchain_core.callbacks",
        
        # LangGraph
        "langgraph", "langgraph.graph", "langgraph.prebuilt",
        
        # LangSmith (monitoring)
        "langsmith", "langsmith.client",
    ]

    # 🌐 LLM Provider Specific Modules
    llm_providers = [
        # Google Gemini
        "langchain_google_genai", 
        "google", "google.generativeai", "google.ai", "google.ai.generativelanguage",
        "google.api_core", "google.auth", "google.cloud",
        "google.generativeai", "google.generativeai.client",
        "google.generativeai.types", "google.generativeai.models",
        
        # OpenAI
        "langchain_openai",
        "openai", "openai.api_resources", "openai.error",
        
        # Anthropic
        "langchain_anthropic",
        "anthropic", "anthropic.client", "anthropic.types",
        
        # API clients common modules
        "httpx", "httpx._client", "httpx._config", "httpx._models",
        "aiohttp", "aiohttp.client", "aiohttp.connector",
    ]

    # 📧 Email & Communication
    email_imports = [
        "postmarker", "postmarker.core", "postmarker.models",
        "premailer", "markdownify", "tenacity", "tenacity.stop", "tenacity.wait",
    ]

    # 🔍 Data Processing & Analysis
    data_processing = [
        "pandas", "numpy", 
        "chromadb", "faiss", "faiss.swigfaiss",
        "sentence_transformers",  # If used for embeddings
    ]

    # 🔒 Security & Monitoring
    security_monitoring = [
        "sentry_sdk", "sentry_sdk.integrations", "sentry_sdk.integrations.flask",
        "sentry_sdk.integrations.logging",
    ]

    # 🔧 System & OS specific
    system_imports = [
        "platform", "subprocess", "pathlib", "tempfile", "shutil",
        "signal", "atexit", "traceback", "logging", "logging.config",
    ]

    # ⚙️ Newsletter specific modules (업데이트됨 - 최신 기능 반영)
    newsletter_modules = [
        "newsletter", "newsletter.cli", "newsletter.main", "newsletter.settings",
        "newsletter.collect", "newsletter.sources", "newsletter.article_filter",
        "newsletter.compose", "newsletter.deliver", "newsletter.summarize",
        "newsletter.chains", "newsletter.graph", "newsletter.tools",
        "newsletter.llm_factory", "newsletter.cost_tracking", "newsletter.scoring",
        "newsletter.config", "newsletter.config_manager", "newsletter.centralized_settings",
        "newsletter.template_manager", "newsletter.date_utils", "newsletter.html_utils",
        "newsletter.compat_env", "newsletter.logging_conf",
        "newsletter.security", "newsletter.security.config", 
        "newsletter.security.middleware", "newsletter.security.logging",
        "newsletter.security.validation",
        "newsletter.utils", "newsletter.utils.logger", "newsletter.utils.error_handling",
        "newsletter.utils.file_naming", "newsletter.utils.subprocess_utils",
        "newsletter.utils.test_mode", "newsletter.utils.convert_legacy_data",
        
        # 최신 추가 모듈들 (email_compatible 및 template 기능)
        "newsletter.template_config", "newsletter.email_processing",
        "newsletter.file_utils", "newsletter.validation",
    ]

    # 🌐 Web specific modules (업데이트됨 - 최신 웹 기능 반영)
    web_modules = [
        "web", "web.app", "web.tasks", "web.mail", "web.suggest", 
        "web.worker", "web.schedule_runner", "web.web_types",
        
        # 바이너리 호환성 모듈 (중요!)
        "web.binary_compatibility", "binary_compatibility",
    ]

    # 🔄 모든 hidden imports를 하나로 합치기
    all_hidden_imports = (
        basic_imports + ai_core_imports + llm_providers + email_imports +
        data_processing + security_monitoring + system_imports +
        newsletter_modules + web_modules
    )

    # PyInstaller 인수 구성
    args = [
        os.path.join("web", "app.py"),
        "--onefile",
        "--name", "newsletter_web",
        "--console",  # 디버깅을 위해 콘솔 창 표시
        
        # Runtime hooks
        "--runtime-hook", "web/runtime_hook.py",
        
        # 모든 newsletter와 web 패키지 수집
        "--collect-all", "newsletter",
        "--collect-all", "web", 
        "--collect-all", "langchain",
        "--collect-all", "langchain_core",
        "--collect-all", "langchain_google_genai",
        "--collect-all", "langchain_openai",
        "--collect-all", "langchain_anthropic",
        "--collect-all", "langgraph",
        
        # Binary files
        "--add-binary", f"{os.path.join(project_root, 'web', 'web_types.py')}{os.pathsep}web",
        
        # 추가 중요한 바이너리/데이터들
        "--collect-binaries", "google",
        "--collect-binaries", "grpc",
        "--collect-binaries", "grpcio",
        
        # 바이너리 호환성 모듈 추가
        "--add-binary", f"{os.path.join(project_root, 'web', 'binary_compatibility.py')}{os.pathsep}web",
    ]

    # Hidden imports 추가
    for module in all_hidden_imports:
        args.extend(["--hidden-import", module])

    # Data files 추가
    for data in datas:
        args.extend(["--add-data", data])

    # 추가 옵션들
    additional_args = [
        "--noconfirm",  # 덮어쓰기 확인 안 함
        "--clean",  # 이전 빌드 정리
        "--distpath", "dist",  # 출력 디렉토리
        "--workpath", "build",  # 작업 디렉토리
        
        # 메모리 및 성능 최적화
        "--optimize", "2",  # Python 최적화 레벨
        
        # 디버깅을 위한 추가 정보 포함
        "--debug", "imports",  # import 디버깅 활성화
        
        # UPX 압축 비활성화 (안정성을 위해)
        "--noupx",
        
        # 경고 억제 (너무 많은 경고 방지)
        "--log-level", "WARN",
    ]
    
    args.extend(additional_args)

    print("[INFO] Starting enhanced PyInstaller build...")
    print(f"[INFO] Total hidden imports: {len(all_hidden_imports)}")
    print(f"[INFO] Total data files: {len(datas)}")
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