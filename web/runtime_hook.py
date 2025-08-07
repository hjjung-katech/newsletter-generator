"""
Runtime hook for PyInstaller to handle module conflicts.
This hook ensures that the web_types module is properly loaded without conflicts.
"""

import sys
import os


def _setup_web_types():
    """Setup web_types module to avoid conflicts with Python's built-in types module."""
    try:
        # PyInstaller 실행 파일에서 실행될 때의 경로 처리
        if getattr(sys, "frozen", False):
            # PyInstaller로 빌드된 실행 파일에서 실행 중
            base_path = sys._MEIPASS
        else:
            # 일반 Python 스크립트로 실행 중
            base_path = os.path.dirname(os.path.abspath(__file__))

        # web_types.py 파일 경로 찾기
        web_types_path = os.path.join(base_path, "web", "web_types.py")

        if os.path.exists(web_types_path):
            # web_types.py 파일이 존재하면 직접 임포트
            import importlib.util

            spec = importlib.util.spec_from_file_location("web_types", web_types_path)
            web_types = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(web_types)

            # web 모듈 생성 및 web_types 할당
            if "web" not in sys.modules:
                import types

                web_module = types.ModuleType("web")
                sys.modules["web"] = web_module

            sys.modules["web"].web_types = web_types
            sys.modules["web.web_types"] = web_types

            print(
                f"[SUCCESS] web_types module loaded successfully from {web_types_path}"
            )
        else:
            # 파일이 없으면 현재 디렉토리에서 찾기
            current_web_types = os.path.join(os.path.dirname(__file__), "web_types.py")
            if os.path.exists(current_web_types):
                import importlib.util

                spec = importlib.util.spec_from_file_location(
                    "web_types", current_web_types
                )
                web_types = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(web_types)

                if "web" not in sys.modules:
                    import types

                    web_module = types.ModuleType("web")
                    sys.modules["web"] = web_module

                sys.modules["web"].web_types = web_types
                sys.modules["web.web_types"] = web_types

                print(
                    f"[SUCCESS] web_types module loaded from current directory: {current_web_types}"
                )
            else:
                print(
                    f"[WARNING] web_types.py not found in {web_types_path} or {current_web_types}"
                )

    except Exception as e:
        print(f"[ERROR] Error setting up web_types module: {e}")


def _setup_newsletter_module():
    """Setup newsletter module path for PyInstaller."""
    try:
        if getattr(sys, "frozen", False):
            # PyInstaller 실행 파일에서 실행 중
            base_path = sys._MEIPASS
            newsletter_path = os.path.join(base_path, "newsletter")

            if os.path.exists(newsletter_path):
                # newsletter 디렉토리를 sys.path에 추가
                if newsletter_path not in sys.path:
                    sys.path.insert(0, newsletter_path)
                print(f"[SUCCESS] newsletter module path added: {newsletter_path}")
            else:
                print(f"[WARNING] newsletter directory not found at: {newsletter_path}")

    except Exception as e:
        print(f"[ERROR] Error setting up newsletter module: {e}")


# 모듈 설정 실행
_setup_newsletter_module()
_setup_web_types()
