"""
Enhanced Runtime hook for PyInstaller to handle all module conflicts and setup.
This hook ensures comprehensive module loading and environment setup for binary execution.
"""

import sys
import os
import logging


def _setup_comprehensive_environment():
    """Comprehensive environment setup for PyInstaller binary."""
    try:
        # Binary compatibility module 로드
        if getattr(sys, "frozen", False):
            base_path = sys._MEIPASS
            
            # binary_compatibility 모듈 경로 추가
            web_path = os.path.join(base_path, "web")
            if web_path not in sys.path:
                sys.path.insert(0, web_path)
            
            # binary_compatibility 모듈 import 및 실행
            try:
                import binary_compatibility
                diagnostics = binary_compatibility.run_comprehensive_diagnostics()
                print(f"[SUCCESS] Binary compatibility diagnostics completed: {diagnostics['overall_status']}")
            except ImportError as e:
                print(f"[WARNING] Could not import binary_compatibility: {e}")
                # Fallback to basic setup
                _fallback_basic_setup()
                
        else:
            print("[INFO] Running in development mode - skipping binary compatibility setup")
            
    except Exception as e:
        print(f"[ERROR] Error in comprehensive environment setup: {e}")
        # Fallback to basic setup
        _fallback_basic_setup()


def _fallback_basic_setup():
    """Fallback basic setup when comprehensive setup fails."""
    print("[INFO] Running fallback basic setup...")
    _setup_newsletter_module()
    _setup_web_types()
    _setup_basic_paths()


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


def _setup_basic_paths():
    """Setup basic paths for PyInstaller environment."""
    try:
        if getattr(sys, "frozen", False):
            base_path = sys._MEIPASS
            
            # 중요한 경로들을 sys.path에 추가
            important_paths = [
                base_path,
                os.path.join(base_path, "newsletter"),
                os.path.join(base_path, "web"),
                os.path.join(base_path, "templates"),
            ]
            
            for path in important_paths:
                if os.path.exists(path) and path not in sys.path:
                    sys.path.insert(0, path)
                    print(f"[SUCCESS] Added to sys.path: {path}")
                    
    except Exception as e:
        print(f"[ERROR] Error setting up basic paths: {e}")


def _setup_environment_variables():
    """Setup environment variables for binary execution."""
    try:
        # Google Cloud 인증 비활성화 (binary에서 문제 발생 방지)
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
        os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
        os.environ.pop("CLOUDSDK_CONFIG", None)
        
        # UTF-8 인코딩 강제 설정 (Windows 환경)
        if sys.platform.startswith("win"):
            os.environ["PYTHONIOENCODING"] = "utf-8"
            os.environ["PYTHONUTF8"] = "1"
        
        # 🔴 CRITICAL FIX: .env 파일 로딩
        if getattr(sys, "frozen", False):
            # PyInstaller로 빌드된 경우 - exe와 동일한 디렉토리에서 .env 파일 찾기
            exe_dir = os.path.dirname(sys.executable)
            env_file = os.path.join(exe_dir, ".env")
            
            if os.path.exists(env_file):
                print(f"[SUCCESS] Loading .env file from exe directory: {env_file}")
                try:
                    # python-dotenv 사용하여 .env 파일 로딩
                    from dotenv import load_dotenv
                    load_dotenv(env_file)
                    print("[SUCCESS] .env file loaded successfully via runtime hook")
                    
                    # 환경 변수 확인
                    critical_vars = ['SERPER_API_KEY', 'GEMINI_API_KEY', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY']
                    for var in critical_vars:
                        value = os.environ.get(var)
                        if value and value not in ['SERPER_API_KEY', 'GEMINI_API_KEY', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY']:
                            print(f"[🔴 LOADED] {var}: {'*' * 10}...{value[-5:] if len(value) > 5 else 'SHORT'}")
                        else:
                            print(f"[🔴 WARNING] {var}: NOT SET OR PLACEHOLDER")
                            
                except ImportError:
                    print("[🔴 ERROR] python-dotenv not available, manual .env parsing")
                    # Manual .env parsing as fallback
                    _manual_env_parsing(env_file)
                except Exception as e:
                    print(f"[🔴 ERROR] Error loading .env file: {e}")
                    _manual_env_parsing(env_file)
            else:
                print(f"[🔴 ERROR] .env file not found at: {env_file}")
        
        print("[SUCCESS] Environment variables configured for binary execution")
        
    except Exception as e:
        print(f"[ERROR] Error setting up environment variables: {e}")


def _manual_env_parsing(env_file):
    """Manual .env file parsing as fallback."""
    try:
        print(f"[🔴 FALLBACK] Manual parsing of .env file: {env_file}")
        with open(env_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")  # Remove quotes
                    
                    if key and value:
                        os.environ[key] = value
                        if key.endswith('_API_KEY'):
                            print(f"[🔴 MANUAL] {key}: {'*' * 10}...{value[-5:] if len(value) > 5 else 'SHORT'}")
                        
        print("[🔴 SUCCESS] Manual .env parsing completed")
    except Exception as e:
        print(f"[🔴 ERROR] Manual .env parsing failed: {e}")


def _setup_logging_early():
    """Early logging setup for runtime hook debugging."""
    try:
        # 기본 로깅 설정 (파일이 아직 준비되지 않았을 수 있으므로 콘솔만)
        logging.basicConfig(
            level=logging.INFO,
            format='[RUNTIME-HOOK] %(asctime)s - %(levelname)s - %(message)s',
            stream=sys.stdout
        )
        print("[SUCCESS] Early logging setup completed")
        
    except Exception as e:
        print(f"[ERROR] Error setting up early logging: {e}")


# === RUNTIME HOOK EXECUTION ===
print("[INFO] ===== PyInstaller Runtime Hook Started =====")

# 1. 기본 로깅 설정
_setup_logging_early()

# 2. 환경 변수 설정
_setup_environment_variables()

# 3. 종합 환경 설정 (또는 fallback 기본 설정)
_setup_comprehensive_environment()

print("[INFO] ===== PyInstaller Runtime Hook Completed =====")

# 최종 환경 확인
print(f"[INFO] Python executable: {sys.executable}")
print(f"[INFO] Frozen: {getattr(sys, 'frozen', False)}")
if hasattr(sys, '_MEIPASS'):
    print(f"[INFO] MEIPASS: {sys._MEIPASS}")
print(f"[INFO] sys.path entries: {len(sys.path)}")
