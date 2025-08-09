#!/usr/bin/env python3
"""Build a standalone executable for the Flask web server using PyInstaller.

This script bundles Python, required modules, templates, static assets and the
newsletter templates into a single executable. The resulting binary can run on
Windows without a separate Python installation.
"""

import os
import shutil
import PyInstaller.__main__


def build():
    project_root = os.path.abspath(os.path.dirname(__file__))
    os.chdir(project_root)

    # PyInstaller 빌드에 포함할 내부 데이터 (exe 내부에 번들)
    datas = [
        f"templates{os.pathsep}templates",
        f"{os.path.join('web', 'templates')}{os.pathsep}templates",
        f"{os.path.join('web', 'static')}{os.pathsep}static",
        f"{os.path.join('web', 'web_types.py')}{os.pathsep}web",  # web_types.py를 web 디렉토리에 복사
        f"newsletter{os.pathsep}newsletter",  # newsletter 패키지 전체를 포함
    ]

    args = [
        os.path.join("web", "app.py"),
        "--onefile",
        "--name",
        "newsletter_web",
        "--hidden-import",
        "web.web_types",  # 명시적으로 web_types 모듈 포함
        "--hidden-import",
        "newsletter",  # newsletter 패키지 포함
        "--hidden-import",
        "newsletter.cli",  # CLI 모듈 포함
        "--hidden-import",
        "newsletter.main",  # main 모듈 포함
        "--hidden-import",
        "newsletter.settings",  # settings 모듈 포함
        "--hidden-import",
        "flask",  # Flask 포함
        "--hidden-import",
        "flask_cors",  # Flask-CORS 포함
        "--hidden-import",
        "werkzeug",  # Werkzeug 포함
        "--hidden-import",
        "jinja2",  # Jinja2 포함
        "--hidden-import",
        "sqlite3",  # SQLite 포함
        "--hidden-import",
        "redis",  # Redis 포함
        "--hidden-import",
        "pydantic",  # Pydantic 포함
        "--hidden-import",
        "rq",  # RQ 포함
        "--hidden-import",
        "sentry_sdk",  # Sentry SDK 포함
        "--collect-all",
        "newsletter",  # newsletter 패키지의 모든 모듈 수집
        "--collect-all",
        "web",  # web 패키지의 모든 모듈 수집
        "--runtime-hook",
        "web/runtime_hook.py",  # 런타임 훅 추가
        "--add-binary",
        f"{os.path.join('web', 'web_types.py')}{os.pathsep}web",  # 바이너리로도 추가
    ]

    for data in datas:
        args += ["--add-data", data]

    PyInstaller.__main__.run(args)

    print("Building completed successfully!")

    # 빌드 후 필요한 외부 파일들을 dist 디렉토리에 복사
    copy_external_files_to_dist()

    print("You can now run the executable: .\\dist\\newsletter_web.exe")


def copy_external_files_to_dist():
    """빌드 후 필요한 외부 파일들을 dist 디렉토리에 복사합니다."""
    project_root = os.path.abspath(os.path.dirname(__file__))
    dist_dir = os.path.join(project_root, "dist")

    # 복사할 파일 및 디렉토리 목록
    files_to_copy = [
        # 환경 설정 파일들
        (".env", ".env"),  # (소스, 대상)
        (".env.example", ".env.example"),
        ("config.yml", "config.yml"),
        # config 디렉토리 전체
        ("config", "config"),
        # 템플릿 파일들 (외부 수정 가능하도록)
        ("templates", "templates"),
        # 기타 필요한 파일들
        ("requirements.txt", "requirements.txt"),
    ]

    print("Copying external files to dist directory...")

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
                    print(f"  ✓ Copied directory: {src} -> dist/{dest}")
                else:
                    # 파일 복사
                    shutil.copy2(src_path, dest_path)
                    print(f"  ✓ Copied file: {src} -> dist/{dest}")
            except Exception as e:
                print(f"  ❌ Failed to copy {src}: {e}")
        else:
            print(f"  ⚠️  Source not found: {src}")

    print("External files copy completed!")


if __name__ == "__main__":
    build()
