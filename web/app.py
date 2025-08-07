"""
Newsletter Generator Web Service
Flask application that provides web interface for the CLI newsletter generator
"""

import os
import sys
import logging
import subprocess
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import redis
from rq import Queue
import sqlite3
from datetime import datetime
import uuid
import json

# Add current directory to path for local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)


# Helper to get correct paths when bundled with PyInstaller
def resource_path(relative_path: str) -> str:
    """Return absolute path to resource for dev and for PyInstaller bundles."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


# Import web types module - will be loaded later to avoid conflicts


# Sentry 통합 - 더미 함수 먼저 정의
def set_sentry_user_context(*args, **kwargs):
    """Sentry 사용자 컨텍스트 설정 (더미)"""
    pass


def set_sentry_tags(**kwargs):
    """Sentry 태그 설정 (더미)"""
    pass


# Centralized Settings 사용한 Sentry 설정
try:
    from newsletter.centralized_settings import get_settings

    settings = get_settings()

    if settings.sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            from sentry_sdk.integrations.logging import LoggingIntegration

            logging_integration = LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            )

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                integrations=[
                    FlaskIntegration(transaction_style="endpoint"),
                    logging_integration,
                ],
                traces_sample_rate=settings.sentry_traces_sample_rate,
                environment=settings.environment,
                release=settings.app_version,
                profiles_sample_rate=settings.sentry_profiles_sample_rate,
                before_send=lambda event, hint: (
                    event if event.get("level") != "info" else None
                ),
            )
            print("[SUCCESS] Sentry initialized successfully")

            # 실제 Sentry 함수들로 재정의
            def set_sentry_user_context(user_id=None, email=None, **kwargs):
                """Sentry에 사용자 컨텍스트 설정"""
                sentry_sdk.set_user({"id": user_id, "email": email, **kwargs})

            def set_sentry_tags(**tags):
                """Sentry에 태그 설정"""
                for key, value in tags.items():
                    sentry_sdk.set_tag(key, value)

        except ImportError:
            print("[WARNING] Sentry SDK not installed, skipping Sentry integration")
        except Exception as e:
            print(f"[WARNING] Sentry initialization failed: {e}")
    else:
        print("[INFO] Sentry DSN not configured, skipping Sentry integration")

except Exception as e:
    # Centralized settings 실패 시 legacy fallback
    print(
        f"[WARNING] Centralized settings unavailable, checking legacy SENTRY_DSN: {e}"
    )
    if os.getenv("SENTRY_DSN"):
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            from sentry_sdk.integrations.logging import LoggingIntegration

            logging_integration = LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            )

            sentry_sdk.init(
                dsn=os.getenv("SENTRY_DSN"),
                integrations=[
                    FlaskIntegration(transaction_style="endpoint"),
                    logging_integration,
                ],
                traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
                environment=os.getenv("ENVIRONMENT", "production"),
                release=os.getenv("APP_VERSION", "1.0.0"),
                profiles_sample_rate=float(
                    os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1")
                ),
                before_send=lambda event, hint: (
                    event if event.get("level") != "info" else None
                ),
            )
            print("[SUCCESS] Sentry initialized successfully (legacy mode)")

            # 실제 Sentry 함수들로 재정의
            def set_sentry_user_context(user_id=None, email=None, **kwargs):
                """Sentry에 사용자 컨텍스트 설정"""
                sentry_sdk.set_user({"id": user_id, "email": email, **kwargs})

            def set_sentry_tags(**tags):
                """Sentry에 태그 설정"""
                for key, value in tags.items():
                    sentry_sdk.set_tag(key, value)

        except ImportError:
            print("[WARNING] Sentry SDK not installed, skipping Sentry integration")
        except Exception as e:
            print(f"[WARNING] Sentry initialization failed: {e}")
    else:
        print("[INFO] Legacy SENTRY_DSN not configured, skipping Sentry integration")


# Import task function for RQ
from tasks import generate_newsletter_task

# Add the parent directory to the path to import newsletter modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Real newsletter CLI integration
import subprocess
import tempfile
import logging

# 현재 디렉토리를 파이썬 패스에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 프로젝트 루트를 파이썬 패스에 추가
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)


class RealNewsletterCLI:
    def __init__(self):
        # CLI 경로 설정 - PyInstaller 환경 대응
        if getattr(sys, "frozen", False):
            # PyInstaller로 빌드된 경우 - exe와 동일한 폴더를 프로젝트 루트로 설정
            self.project_root = os.path.dirname(sys.executable)
        else:
            # 일반 Python 환경
            self.project_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..")
            )
        self.timeout = 900  # 15분 타임아웃으로 증가

        # 환경 확인
        self._check_environment()

    def _check_environment(self):
        """환경 설정 확인"""
        # PyInstaller 실행 파일에서 실행 중인지 확인
        if getattr(sys, "frozen", False):
            # PyInstaller 실행 파일에서 실행 중
            base_path = sys._MEIPASS
            newsletter_path = os.path.join(base_path, "newsletter")
            env_file = os.path.join(base_path, ".env")
        else:
            # 일반 Python 스크립트로 실행 중
            newsletter_path = os.path.join(self.project_root, "newsletter")
            env_file = os.path.join(self.project_root, ".env")

        # 프로젝트 루트 확인
        if not os.path.exists(newsletter_path):
            raise Exception(f"Newsletter module not found in {newsletter_path}")

        # .env 파일 확인
        if not os.path.exists(env_file):
            print(f"[WARNING] Warning: .env file not found at {env_file}")
            print(
                f"[WARNING] This may cause longer processing times or fallback to mock mode"
            )

        # API 키 확인
        api_keys_status = self._check_api_keys()

        print("[SUCCESS] Environment check passed")
        print(f"   Project root: {self.project_root}")
        print(
            f"   Newsletter module exists: {os.path.exists(os.path.join(self.project_root, 'newsletter'))}"
        )
        print(f"   .env file exists: {os.path.exists(env_file)}")
        print(f"   API keys configured: {api_keys_status}")

    def _check_api_keys(self):
        """API 키 설정 상태 확인 - 개선된 검사"""
        try:
            # newsletter 모듈의 API 키 검사 함수 사용
            from newsletter.llm_factory import validate_api_keys

            available_providers = validate_api_keys()

            # 결과 정리
            llm_providers = [
                p for p in available_providers if p in ["gemini", "openai", "anthropic"]
            ]
            has_serper = "serper" in available_providers

            status = {
                "llm_providers": llm_providers,
                "has_serper": has_serper,
                "total_available": len(available_providers),
                "status": "success" if llm_providers else "error",
            }

            print(f"✅ API 키 검사 완료: {len(llm_providers)}개 LLM 제공자 사용 가능")
            if llm_providers:
                print(f"   사용 가능한 LLM: {', '.join(llm_providers)}")
            if has_serper:
                print("   ✅ Serper API (뉴스 검색) 사용 가능")
            else:
                print("   ⚠️ Serper API (뉴스 검색) 없음")

            return status

        except Exception as e:
            print(f"❌ API 키 검사 실패: {e}")
            return {
                "llm_providers": [],
                "has_serper": False,
                "total_available": 0,
                "status": "error",
                "error": str(e),
            }

    def _generate_direct(
        self,
        keywords=None,
        domain=None,
        template_style="compact",
        email_compatible=False,
        period=14,
    ):
        """웹 서비스 모드에서 직접 뉴스레터 생성"""
        try:
            # 환경 변수 완전 초기화
            import os
            import sys

            # 프로젝트 루트를 Python 경로에 추가
            if self.project_root not in sys.path:
                sys.path.insert(0, self.project_root)

            # 환경 변수 강제 설정 (PyInstaller 환경 대응)
            self._ensure_environment_variables()

            # newsletter 모듈 직접 import
            from newsletter import collect, compose, summarize

            # 키워드 처리
            if keywords:
                keyword_list = keywords if isinstance(keywords, list) else [keywords]
                keyword_str = ",".join(keyword_list)
                input_description = f"keywords: {keyword_str}"
            elif domain:
                input_description = f"domain: {domain}"
                # 도메인에서 키워드 생성 (간단한 구현)
                keyword_list = [domain]
                keyword_str = domain
            else:
                raise ValueError("Either keywords or domain must be provided")

            logging.info(f"Direct generation for: {input_description}")

            # 뉴스 수집
            articles = collect.collect_articles(
                keywords=keyword_str,
                num_results=10,
                max_per_source=3,
                filter_duplicates=True,
                group_by_keywords=True,
                use_major_sources_filter=True,  # 올바른 매개변수명 사용
            )

            # 기사가 없으면 빈 결과 반환
            if not articles:
                return {
                    "content": "수집된 기사가 없습니다.",
                    "title": f"{keyword_str} 관련 뉴스레터",
                    "status": "success",
                }

            # 템플릿 기반 생성 방식 선택
            # 환경 변수나 설정을 통해 제어 가능
            from newsletter.config_manager import (
                should_use_template_system,
                get_template_name,
            )

            use_template_system = should_use_template_system()

            if use_template_system:
                # 기존 Jinja2 템플릿 시스템 사용
                logging.info("Using Jinja2 template system for newsletter generation")

                # 템플릿 디렉토리 설정 - PyInstaller 환경 대응
                if getattr(sys, "frozen", False):
                    # PyInstaller로 빌드된 경우 - 임시 디렉토리에서 템플릿 찾기
                    template_dir = os.path.join(sys._MEIPASS, "templates")
                    logging.info(f"PyInstaller 환경: 템플릿 디렉토리 = {template_dir}")
                else:
                    # 일반 Python 환경
                    template_dir = os.path.join(self.project_root, "templates")

                # 템플릿 디렉토리 존재 확인
                if not os.path.exists(template_dir):
                    logging.error(
                        f"템플릿 디렉토리가 존재하지 않습니다: {template_dir}"
                    )
                    # 대안 경로들 시도
                    alternative_paths = [
                        os.path.join(os.path.dirname(__file__), "..", "templates"),
                        os.path.join(os.getcwd(), "templates"),
                    ]
                    for alt_path in alternative_paths:
                        if os.path.exists(alt_path):
                            template_dir = alt_path
                            logging.info(f"대안 템플릿 디렉토리 사용: {template_dir}")
                            break
                    else:
                        raise FileNotFoundError(
                            f"템플릿 디렉토리를 찾을 수 없습니다. 시도한 경로들: {[template_dir] + alternative_paths}"
                        )
                else:
                    logging.info(f"템플릿 디렉토리 확인됨: {template_dir}")

                # 설정 파일에서 템플릿 이름 가져오기
                template_name = get_template_name(template_style, email_compatible)

                # 기사 데이터를 템플릿 시스템에 맞게 변환
                if isinstance(articles, dict):
                    # 딕셔너리 형태를 리스트로 변환 (템플릿 시스템 호환성)
                    all_articles = []
                    for keyword, article_list in articles.items():
                        all_articles.extend(article_list)
                    articles_for_template = all_articles
                else:
                    articles_for_template = articles

                # Jinja2 템플릿을 사용하여 HTML 생성
                html_content = compose.compose_newsletter_html(
                    articles_for_template, template_dir, template_name
                )

                logging.info(f"Generated HTML using Jinja2 template: {template_name}")

            else:
                # LLM 직접 생성 방식 (기존 방식)
                logging.info("Using LLM direct generation for newsletter")
                html_content = summarize.summarize_articles(keyword_list, articles)

            # 제목 생성
            title = f"Newsletter: {keyword_str}"

            # 성공 통계 - articles가 딕셔너리인 경우를 처리
            if isinstance(articles, dict):
                # 딕셔너리인 경우: 각 키워드별 기사 수를 합산
                total_articles = sum(
                    len(article_list) for article_list in articles.values()
                )
                # 모든 기사의 소스를 수집
                all_sources = set()
                for article_list in articles.values():
                    for article in article_list:
                        if isinstance(article, dict):
                            all_sources.add(article.get("source", ""))
                sources_count = len(all_sources)
            else:
                # 리스트인 경우: 기존 로직 사용
                total_articles = len(articles)
                sources_count = len(
                    set(article.get("source", "") for article in articles)
                )

            stats = {
                "articles_count": total_articles,
                "sources_count": sources_count,
                "generation_time": (
                    "template_mode" if use_template_system else "direct_mode"
                ),
                "template_used": template_name if use_template_system else "LLM_direct",
            }

            logging.info(f"Direct newsletter generation successful: {title}")
            logging.info(f"Generated HTML size: {len(html_content)} characters")

            response = {
                "content": html_content,
                "title": title,
                "status": "success",
                "cli_output": f"Template-based generation mode - {len(articles)} articles processed",
                "generation_stats": stats,
                "input_params": {
                    "keywords": keywords,
                    "domain": domain,
                    "template_style": template_style,
                    "email_compatible": email_compatible,
                    "period": period,
                    "generation_method": (
                        "template" if use_template_system else "llm_direct"
                    ),
                },
            }

            return response

        except Exception as e:
            error_msg = f"Direct generation failed: {str(e)}"
            logging.error(error_msg, exc_info=True)
            return self._fallback_response(keywords or domain, error_msg)

    def _ensure_environment_variables(self):
        """환경 변수를 확실히 설정합니다 (PyInstaller 환경 대응)"""
        import os

        print("[DEBUG] Attempting to load environment variables...")

        # List of .env files to check, in order of precedence
        env_files_to_check = []

        # 1. .env file in the project root (dist directory in PyInstaller)
        env_files_to_check.append(os.path.join(self.project_root, ".env"))

        # 2. .env file in the current working directory (if different)
        current_cwd_env_file = os.path.join(os.getcwd(), ".env")
        if current_cwd_env_file not in env_files_to_check:
            env_files_to_check.append(current_cwd_env_file)

        # Keys we are interested in
        target_keys = [
            "POSTMARK_SERVER_TOKEN",
            "EMAIL_SENDER",
            "SERPER_API_KEY",
            "OPENAI_API_KEY",
            "NAVER_CLIENT_ID",
            "NAVER_CLIENT_SECRET",
        ]

        # Load environment variables from files
        for env_file in env_files_to_check:
            if os.path.exists(env_file):
                print(f"[DEBUG] Loading from: {env_file}")
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip()

                            # Remove quotes
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.startswith("'") and value.endswith("'"):
                                value = value[1:-1]

                            # Set environment variable if it's one of our target keys
                            if key in target_keys:
                                os.environ[key] = value
                                print(
                                    f"[DEBUG] Set {key} = {value[:10]}... from {os.path.basename(env_file)}"
                                )

        # Final check and logging
        postmark_token = os.getenv("POSTMARK_SERVER_TOKEN")
        email_sender = os.getenv("EMAIL_SENDER")
        serper_key = os.getenv("SERPER_API_KEY")
        naver_client_id = os.getenv("NAVER_CLIENT_ID")
        naver_client_secret = os.getenv("NAVER_CLIENT_SECRET")
        openai_key = os.getenv("OPENAI_API_KEY")

        print(
            f"[DEBUG] Final check - POSTMARK_SERVER_TOKEN: {'Set' if postmark_token and 'your-' not in postmark_token else 'Not set or placeholder'}"
        )
        print(
            f"[DEBUG] Final check - EMAIL_SENDER: {'Set' if email_sender and 'yourdomain.com' not in email_sender else 'Not set or placeholder'}"
        )
        print(
            f"[DEBUG] Final check - SERPER_API_KEY: {'Set' if serper_key and 'your-' not in serper_key else 'Not set or placeholder'}"
        )
        print(
            f"[DEBUG] Final check - NAVER_CLIENT_ID: {'Set' if naver_client_id and 'your-' not in naver_client_id else 'Not set or placeholder'}"
        )
        print(
            f"[DEBUG] Final check - NAVER_CLIENT_SECRET: {'Set' if naver_client_secret and 'your-' not in naver_client_secret else 'Not set or placeholder'}"
        )
        print(
            f"[DEBUG] Final check - OPENAI_API_KEY: {'Set' if openai_key and 'your-' not in openai_key else 'Not set or placeholder'}"
        )

        if (
            (postmark_token and "your-" not in postmark_token)
            and (email_sender and "yourdomain.com" not in email_sender)
            and (serper_key and "your-" not in serper_key)
        ):  # Add other critical keys here
            print(
                "[DEBUG] All critical environment variables appear to be set correctly."
            )
        else:
            print(
                "[WARNING] Some critical environment variables are still missing or are placeholders."
            )

    def generate_newsletter(
        self,
        keywords=None,
        domain=None,
        template_style="compact",
        email_compatible=False,
        period=14,
    ):
        """실제 CLI를 사용하여 뉴스레터 생성"""
        try:
            # 웹 서비스 모드에서는 항상 직접 모듈 호출 사용
            return self._generate_direct(
                keywords=keywords,
                domain=domain,
                template_style=template_style,
                email_compatible=email_compatible,
                period=period,
            )

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logging.error(error_msg, exc_info=True)  # 스택 트레이스 포함
            return self._fallback_response(keywords or domain, error_msg)

    def _find_latest_html_file(self, output_dir, keywords=None):
        """output 디렉토리에서 최신 HTML 파일 찾기"""
        try:
            if not os.path.exists(output_dir):
                logging.error(f"Output directory does not exist: {output_dir}")
                return None

            html_files = [f for f in os.listdir(output_dir) if f.endswith(".html")]
            if not html_files:
                logging.error(f"No HTML files found in {output_dir}")
                return None

            logging.info(f"Found {len(html_files)} HTML files in {output_dir}")

            # 키워드가 있으면 해당 키워드가 포함된 파일을 우선적으로 찾기
            if keywords:
                keyword_str = (
                    keywords if isinstance(keywords, str) else ",".join(keywords)
                )
                keyword_files = [
                    f
                    for f in html_files
                    if any(
                        kw.strip().lower() in f.lower() for kw in keyword_str.split(",")
                    )
                ]
                if keyword_files:
                    html_files = keyword_files
                    logging.info(
                        f"Filtered to {len(keyword_files)} files matching keywords: {keyword_str}"
                    )

            # 최신 파일 찾기 (생성 시간 기준)
            latest_file = max(
                html_files, key=lambda x: os.path.getctime(os.path.join(output_dir, x))
            )
            file_path = os.path.join(output_dir, latest_file)

            logging.info(f"Reading latest HTML file: {latest_file}")
            logging.info(f"File path: {file_path}")
            logging.info(f"File size: {os.path.getsize(file_path)} bytes")

            # 여러 인코딩으로 시도
            encodings = ["utf-8", "utf-8-sig", "cp949", "euc-kr", "latin1"]

            for encoding in encodings:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        content = f.read()
                        logging.info(f"Successfully read file with {encoding} encoding")
                        logging.info(f"Content length: {len(content)} characters")
                        return content
                except UnicodeDecodeError:
                    logging.warning(f"Failed to read with {encoding} encoding")
                    continue

            logging.error(f"Failed to read file with any encoding")
            return None

        except Exception as e:
            logging.error(f"Error reading HTML file: {e}")
            return None

    def _extract_title_from_html(self, html_content):
        """HTML에서 제목 추출"""
        try:
            import re

            title_match = re.search(
                r"<title>(.*?)</title>", html_content, re.IGNORECASE
            )
            if title_match:
                return title_match.group(1)
            return None
        except Exception:
            return None

    def _extract_generation_stats(self, cli_output):
        """CLI 출력에서 생성 통계 정보 추출"""
        stats = {}
        try:
            import re

            # 처리 시간 추출
            time_pattern = r"(\w+)\s+time:\s*([\d.]+)\s*seconds"
            time_matches = re.findall(time_pattern, cli_output)
            if time_matches:
                stats["step_times"] = {step: float(time) for step, time in time_matches}

            # 총 시간 추출
            total_time_pattern = r"Total generation time:\s*([\d.]+)\s*seconds"
            total_match = re.search(total_time_pattern, cli_output)
            if total_match:
                stats["total_time"] = float(total_match.group(1))

            # 기사 수 추출
            article_pattern = r"(\d+)\s+articles?\s+(?:collected|processed|found)"
            article_match = re.search(article_pattern, cli_output, re.IGNORECASE)
            if article_match:
                stats["articles_count"] = int(article_match.group(1))

            # 키워드 정보 추출
            if "Generated keywords:" in cli_output:
                keyword_pattern = r"Generated keywords:\s*(.+)"
                keyword_match = re.search(keyword_pattern, cli_output)
                if keyword_match:
                    stats["generated_keywords"] = keyword_match.group(1).strip()

        except Exception as e:
            logging.warning(f"Failed to extract generation stats: {e}")

        return stats

    def _fallback_response(self, input_param, error_msg):
        """에러 발생 시 폴백 응답 생성"""
        title = f"Newsletter Generation Failed: {input_param}"
        content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .error {{ background: #f8d7da; color: #721c24; padding: 20px; border-radius: 5px; border: 1px solid #f5c6cb; }}
        .info {{ background: #d4edda; color: #155724; padding: 15px; border-radius: 5px; border: 1px solid #c3e6cb; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="error">
        <h2>Newsletter Generation Error</h2>
        <p><strong>Input:</strong> {input_param}</p>
        <p><strong>Error:</strong> {error_msg}</p>
        <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    <div class="info">
        <h3>What happened?</h3>
        <p>The newsletter CLI encountered an error during generation. This could be due to:</p>
        <ul>
            <li>Network connectivity issues</li>
            <li>API rate limits or quota exceeded</li>
            <li>Invalid input parameters</li>
            <li>CLI timeout (process took longer than {self.timeout} seconds)</li>
        </ul>
        <p>Please try again with different parameters or check the system logs for more details.</p>
    </div>
</body>
</html>
"""

        return {
            "content": content,
            "title": title,
            "status": "error",
            "error": error_msg,
        }


# MockNewsletterCLI는 폴백용으로 유지
class MockNewsletterCLI:
    def __init__(self):
        pass

    def generate_newsletter(
        self,
        keywords=None,
        domain=None,
        template_style="compact",
        email_compatible=False,
        period=14,
    ):
        """Mock newsletter generation with more realistic content"""
        if keywords:
            if isinstance(keywords, list):
                keyword_list = [k.strip() for k in keywords]
            else:
                keyword_list = [k.strip() for k in keywords.split(",")]
            title = f"Newsletter: {', '.join(keyword_list)} (Mock)"

            content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background: #f4f4f4; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .article {{ margin-bottom: 20px; padding: 15px; border-left: 3px solid #007bff; }}
        .article h3 {{ color: #007bff; margin-top: 0; }}
        .footer {{ background: #f4f4f4; padding: 15px; text-align: center; font-size: 0.9em; }}
        .mock-notice {{ background: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; border: 1px solid #ffeaa7; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="mock-notice">
        <strong>[WARNING] Mock Mode:</strong> This is a test newsletter generated using mock data. 
        Template Style: {template_style} | Email Compatible: {email_compatible} | Period: {period} days
    </div>
    <div class="header">
        <h1>{title}</h1>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    <div class="content">
        <h2>Top Stories</h2>
"""

            for i, keyword in enumerate(keyword_list, 1):
                content += f"""
        <div class="article">
            <h3>{i}. Latest developments in {keyword}</h3>
            <p>This is a mock article about recent developments in {keyword}. In a real implementation, this would contain actual news content collected from various sources.</p>
            <p><strong>Key points:</strong></p>
            <ul>
                <li>Market trends and analysis for {keyword}</li>
                <li>Recent technological advancements</li>
                <li>Industry impact and future outlook</li>
            </ul>
        </div>
"""

            content += """
    </div>
    <div class="footer">
        <p>This newsletter was generated by Newsletter Generator Web Service (Mock Mode)</p>
        <p>For more information, visit our website</p>
    </div>
</body>
</html>
"""

        elif domain:
            title = f"Newsletter: {domain} Domain Insights (Mock)"
            content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background: #f4f4f4; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .section {{ margin-bottom: 30px; }}
        .section h3 {{ color: #007bff; border-bottom: 2px solid #007bff; padding-bottom: 5px; }}
        .footer {{ background: #f4f4f4; padding: 15px; text-align: center; font-size: 0.9em; }}
        .mock-notice {{ background: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; border: 1px solid #ffeaa7; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="mock-notice">
        <strong>[WARNING] Mock Mode:</strong> This is a test newsletter generated using mock data. 
        Template Style: {template_style} | Email Compatible: {email_compatible} | Period: {period} days
    </div>
    <div class="header">
        <h1>{title}</h1>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    <div class="content">
        <div class="section">
            <h3>Recent Developments in {domain}</h3>
            <p>Mock analysis of recent developments in the {domain} sector. This would contain real news and insights in the actual implementation.</p>
        </div>
        <div class="section">
            <h3>Key Trends</h3>
            <p>Analysis of key trends affecting the {domain} industry, including market movements and technological advances.</p>
        </div>
        <div class="section">
            <h3>Future Outlook</h3>
            <p>Forward-looking analysis and predictions for the {domain} sector based on current trends and market indicators.</p>
        </div>
    </div>
    <div class="footer">
        <p>This newsletter was generated by Newsletter Generator Web Service (Mock Mode)</p>
    </div>
</body>
</html>
"""
        else:
            title = "Sample Newsletter (Mock)"
            content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sample Newsletter (Mock)</title>
</head>
<body>
    <h1>Sample Newsletter (Mock)</h1>
    <p>No keywords or domain specified. Please provide either keywords or a domain for newsletter generation.</p>
</body>
</html>
"""

        return {"content": content, "title": title, "status": "success"}


# Try to use real CLI first, fallback to mock if it fails
try:
    newsletter_cli = RealNewsletterCLI()
    print("[SUCCESS] Using RealNewsletterCLI for actual newsletter generation")
    print(f"   Project root: {newsletter_cli.project_root}")
    print(f"   Timeout: {newsletter_cli.timeout} seconds")
except Exception as e:
    print(f"[WARNING] Failed to initialize RealNewsletterCLI: {e}")
    import traceback

    traceback.print_exc()
    newsletter_cli = MockNewsletterCLI()
    print("[WARNING] Falling back to MockNewsletterCLI")

app = Flask(
    __name__,
    template_folder=resource_path("templates"),
    static_folder=resource_path("static"),
)
CORS(app)  # Enable CORS for frontend-backend communication

# Enable detailed logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
print("[INFO] Flask app initialized with detailed logging")

# Configuration
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
app.config["REDIS_URL"] = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Queue name can be customized via environment variable
QUEUE_NAME = os.getenv("RQ_QUEUE", "default")

# Redis connection with fallback to in-memory processing
try:
    import platform

    # Windows에서는 RQ Worker가 제대로 작동하지 않으므로 직접 처리 사용
    if platform.system() == "Windows":
        print("[INFO] Windows detected: Using direct processing instead of Redis Queue")
        redis_conn = None
        task_queue = None
    else:
        redis_conn = redis.from_url(app.config["REDIS_URL"])
        redis_conn.ping()  # Test connection
        task_queue = Queue(QUEUE_NAME, connection=redis_conn)
        print("[SUCCESS] Redis connected successfully")
except Exception as e:
    print(f"[WARNING] Redis connection failed: {e}. Using in-memory processing.")
    redis_conn = None
    task_queue = None

# In-memory task storage for when Redis is unavailable
in_memory_tasks = {}

# Database initialization
if getattr(sys, "frozen", False):
    # When bundled by PyInstaller, store DB next to executable for persistence
    data_dir = os.path.dirname(sys.executable)
else:
    data_dir = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(data_dir, "storage.db")


def init_db():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # History table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id TEXT PRIMARY KEY,
            params JSON NOT NULL,
            result JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    """
    )

    # Schedules table for recurring newsletters
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schedules (
            id TEXT PRIMARY KEY,
            params JSON NOT NULL,
            rrule TEXT NOT NULL,
            next_run TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            enabled INTEGER DEFAULT 1
        )
    """
    )

    conn.commit()
    conn.close()


# Initialize database on startup
init_db()


@app.route("/")
def index():
    """Main dashboard page"""
    try:
        print(f"Template folder: {app.template_folder}")
        print(f"App root path: {app.root_path}")
        template_path = os.path.join(app.template_folder, "index.html")
        print(f"Template path: {template_path}")
        print(f"Template exists: {os.path.exists(template_path)}")
        return render_template("index.html")
    except Exception as e:
        print(f"Template rendering error: {e}")
        return f"Template error: {str(e)}", 500


@app.route("/api/generate", methods=["POST"])
def generate_newsletter():
    """Generate newsletter based on keywords or domain with optional email sending"""
    print(f"[INFO] Newsletter generation request received")

    try:
        data = request.get_json()
        if not data:
            print("[WARNING] No data provided in request")
            return jsonify({"error": "No data provided"}), 400

        # Validate request using Pydantic
        try:
            # Try to import web_types from sys.modules first (set up by runtime hook)
            if "web.web_types" in sys.modules:
                web_types = sys.modules["web.web_types"]
            else:
                # Fallback: Import here to avoid conflicts with Python's built-in types module
                import importlib.util
                import os

                if getattr(sys, "frozen", False):
                    # PyInstaller 실행 파일에서 실행 중
                    base_path = sys._MEIPASS
                    web_types_path = os.path.join(base_path, "web", "web_types.py")
                else:
                    # 일반 Python 스크립트로 실행 중
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    web_types_path = os.path.join(current_dir, "web_types.py")

                if os.path.exists(web_types_path):
                    spec = importlib.util.spec_from_file_location(
                        "web_types", web_types_path
                    )
                    web_types = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(web_types)
                else:
                    raise ImportError(f"web_types.py not found at {web_types_path}")

            validated_data = web_types.GenerateNewsletterRequest(**data)
        except (ValueError, Exception) as e:
            print(f"[WARNING] Validation error: {e}")
            return jsonify({"error": f"Invalid request: {str(e)}"}), 400

        # Extract email for sending
        email = validated_data.email
        send_email = bool(email)

        print(f"[INFO] Request data: {data}")
        print(f"[INFO] Send email: {send_email} to {email}")

        # Create unique job ID
        job_id = str(uuid.uuid4())
        print(f"[INFO] Generated job ID: {job_id}")

        # Store request in history
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO history (id, params, status) VALUES (?, ?, ?)",
            (job_id, json.dumps(data), "pending"),
        )
        conn.commit()
        conn.close()
        print(f"[INFO] Stored request in database")

        # If Redis is available, queue the task
        if task_queue:
            print(f"[INFO] Queueing task with Redis")
            job = task_queue.enqueue(generate_newsletter_task, data, job_id, send_email)
            return jsonify({"job_id": job_id, "status": "queued"}), 202
        else:
            print(f"[INFO] Processing in-memory (Redis not available)")
            # Fallback: process in background using in-memory tracking
            import threading

            # Store initial task status
            in_memory_tasks[job_id] = {
                "status": "processing",
                "started_at": datetime.now().isoformat(),
            }

            # Process in background thread
            def background_task():
                try:
                    print(f"[INFO] Starting background processing for job {job_id}")
                    print(f"[INFO] Data: {data}")
                    print(f"[INFO] Current time: {datetime.now().isoformat()}")

                    # 환경 체크
                    print(f"[INFO] Using CLI type: {type(newsletter_cli).__name__}")

                    process_newsletter_in_memory(data, job_id)

                    # 메모리에서 결과 가져오기
                    if job_id in in_memory_tasks:
                        task_result = in_memory_tasks[job_id]
                        print(f"[INFO] Updating database for job {job_id}")
                        print(
                            f"[INFO] Task status: {task_result.get('status', 'unknown')}"
                        )

                        # Update database with final result
                        conn = sqlite3.connect(DATABASE_PATH)
                        cursor = conn.cursor()

                        if (
                            task_result.get("status") == "completed"
                            and "result" in task_result
                        ):
                            # 성공한 경우
                            try:
                                result_json = json.dumps(task_result["result"])
                                cursor.execute(
                                    "UPDATE history SET result = ?, status = ? WHERE id = ?",
                                    (result_json, "completed", job_id),
                                )
                                print(
                                    f"[INFO] Successfully updated database for job {job_id}"
                                )
                            except (TypeError, ValueError) as json_error:
                                print(
                                    f"[WARNING] JSON serialization error for job {job_id}: {json_error}"
                                )
                                # JSON 직렬화 실패 시 기본 응답 저장
                                fallback_result = {
                                    "status": "completed",
                                    "title": "Newsletter Generated",
                                    "content": task_result["result"].get(
                                        "content", "Newsletter content available"
                                    ),
                                    "error": f"JSON serialization failed: {str(json_error)}",
                                }
                                cursor.execute(
                                    "UPDATE history SET result = ?, status = ? WHERE id = ?",
                                    (json.dumps(fallback_result), "completed", job_id),
                                )
                        else:
                            # 실패한 경우
                            error_result = {
                                "error": task_result.get("error", "Unknown error"),
                                "status": "failed",
                            }
                            cursor.execute(
                                "UPDATE history SET result = ?, status = ? WHERE id = ?",
                                (json.dumps(error_result), "failed", job_id),
                            )

                        conn.commit()
                        conn.close()
                        print(
                            f"[SUCCESS] Completed background processing for job {job_id}"
                        )
                    else:
                        print(f"[WARNING] Job {job_id} not found in in_memory_tasks")
                        # 데이터베이스에 실패 상태 업데이트
                        conn = sqlite3.connect(DATABASE_PATH)
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE history SET result = ?, status = ? WHERE id = ?",
                            (
                                json.dumps({"error": "Job not found in memory"}),
                                "failed",
                                job_id,
                            ),
                        )
                        conn.commit()
                        conn.close()

                except Exception as e:
                    print(
                        f"[WARNING] Error in background processing for job {job_id}: {e}"
                    )
                    import traceback

                    print(f"[WARNING] Traceback: {traceback.format_exc()}")

                    # Update database with error
                    try:
                        conn = sqlite3.connect(DATABASE_PATH)
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE history SET result = ?, status = ? WHERE id = ?",
                            (json.dumps({"error": str(e)}), "failed", job_id),
                        )
                        conn.commit()
                        conn.close()
                    except Exception as db_error:
                        print(
                            f"[WARNING] Failed to update database with error for job {job_id}: {db_error}"
                        )

            thread = threading.Thread(target=background_task)
            thread.daemon = True
            thread.start()

            return jsonify({"job_id": job_id, "status": "processing"}), 202

    except Exception as e:
        print(f"[WARNING] Error in generate_newsletter endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/newsletter", methods=["GET"])
def get_newsletter():
    """Generate newsletter directly with GET parameters"""
    try:
        # 파라미터 추출
        topic = request.args.get("topic", "")
        keywords = request.args.get("keywords", topic)  # topic을 keywords로도 받음
        period = request.args.get("period", 14, type=int)
        template_style = request.args.get("template_style", "compact")

        # 기간 파라미터 검증
        if period not in [1, 7, 14, 30]:
            return (
                jsonify({"error": "Invalid period. Must be one of: 1, 7, 14, 30 days"}),
                400,
            )

        # 키워드가 없으면 에러
        if not keywords:
            return (
                jsonify({"error": "Missing required parameter: topic or keywords"}),
                400,
            )

        print(f"[INFO] Newsletter request - Keywords: {keywords}, Period: {period}")

        # 뉴스레터 생성
        result = newsletter_cli.generate_newsletter(
            keywords=keywords,
            template_style=template_style,
            email_compatible=False,
            period=period,
        )

        if result["status"] == "success":
            # HTML 응답으로 직접 반환
            return result["content"], 200, {"Content-Type": "text/html; charset=utf-8"}
        else:
            return (
                jsonify(
                    {
                        "error": f"Newsletter generation failed: {result.get('error', 'Unknown error')}"
                    }
                ),
                500,
            )

    except Exception as e:
        print(f"[WARNING] Error in newsletter endpoint: {e}")
        return jsonify({"error": str(e)}), 500


def process_newsletter_sync(data):
    """Process newsletter synchronously (fallback when Redis is not available)"""
    try:
        print(f"[INFO] Starting synchronous newsletter processing")
        print(f"[INFO] Current newsletter_cli type: {type(newsletter_cli).__name__}")

        # Extract parameters
        keywords = data.get("keywords", "")
        domain = data.get("domain", "")
        template_style = data.get("template_style", "compact")
        email_compatible = data.get("email_compatible", False)
        period = data.get("period", 14)
        email = data.get("email", "")  # 이메일 주소 추가
        use_template_system = data.get(
            "use_template_system", True
        )  # 템플릿 시스템 사용 여부

        print(f"[INFO] Processing parameters:")
        print(f"   Keywords: {keywords}")
        print(f"   Domain: {domain}")
        print(f"   Template style: {template_style}")
        print(f"   Email compatible: {email_compatible}")
        print(f"   Period: {period}")
        print(f"   Email: {email}")
        print(f"   Use template system: {use_template_system}")

        # 템플릿 시스템 설정을 환경 변수로 전달
        if use_template_system is not None:
            import os

            os.environ["USE_TEMPLATE_SYSTEM"] = str(use_template_system).lower()
            print(
                f"[INFO] Set USE_TEMPLATE_SYSTEM environment variable to: {use_template_system}"
            )

        # Use newsletter CLI with proper parameters
        try:
            if isinstance(newsletter_cli, RealNewsletterCLI):
                # RealNewsletterCLI의 경우 _generate_direct 메서드 직접 호출
                print(f"[INFO] Using RealNewsletterCLI._generate_direct method")
                result = newsletter_cli._generate_direct(
                    keywords=keywords,
                    domain=domain,
                    template_style=template_style,
                    email_compatible=email_compatible,
                    period=period,
                )
            else:
                # MockNewsletterCLI의 경우 기존 방식 사용
                if keywords:
                    print(
                        f"[INFO] Generating newsletter with keywords using {type(newsletter_cli).__name__}"
                    )
                    result = newsletter_cli.generate_newsletter(
                        keywords=keywords,
                        template_style=template_style,
                        email_compatible=email_compatible,
                        period=period,
                    )
                elif domain:
                    print(
                        f"[INFO] Generating newsletter with domain using {type(newsletter_cli).__name__}"
                    )
                    result = newsletter_cli.generate_newsletter(
                        domain=domain,
                        template_style=template_style,
                        email_compatible=email_compatible,
                        period=period,
                    )
                else:
                    raise ValueError("Either keywords or domain must be provided")

            print(f"[INFO] CLI result status: {result['status']}")
            print(f"[INFO] CLI result type: {type(result)}")
            print(
                f"[INFO] CLI result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}"
            )

        except Exception as cli_error:
            print(f"[WARNING] CLI generation failed: {str(cli_error)}")
            print(f"[WARNING] CLI error type: {type(cli_error).__name__}")
            import traceback

            print(f"[WARNING] CLI error traceback: {traceback.format_exc()}")
            # Set result to error status for fallback logic
            result = {"status": "error", "error": str(cli_error)}

        # Handle different result formats
        if result["status"] == "error":
            # If CLI failed and returned error, try mock as fallback
            if isinstance(newsletter_cli, RealNewsletterCLI):
                print("[WARNING] Real CLI failed, trying mock fallback...")
                mock_cli = MockNewsletterCLI()
                if keywords:
                    result = mock_cli.generate_newsletter(
                        keywords=keywords,
                        template_style=template_style,
                        email_compatible=email_compatible,
                        period=period,
                    )
                else:
                    result = mock_cli.generate_newsletter(
                        domain=domain,
                        template_style=template_style,
                        email_compatible=email_compatible,
                        period=period,
                    )
                print(f"[INFO] Mock fallback result status: {result['status']}")

        # 이메일 발송 기능 추가
        email_sent = False
        if email and result.get("content") and not data.get("preview_only"):
            try:
                print(f"[INFO] Attempting to send email to {email}")

                # 이메일 발송 전 환경 변수 확인
                if hasattr(newsletter_cli, "_ensure_environment_variables"):
                    newsletter_cli._ensure_environment_variables()

                # 이메일 발송 - try-except로 import 처리
                try:
                    import mail

                    send_email_func = mail.send_email
                except ImportError:
                    try:
                        from . import mail

                        send_email_func = mail.send_email
                    except ImportError:
                        return (
                            jsonify(
                                {
                                    "error": "이메일 모듈을 찾을 수 없습니다. mail.py 파일을 확인해주세요."
                                }
                            ),
                            500,
                        )

                # 제목 생성
                subject = result.get("title", "Newsletter")
                if keywords:
                    subject = f"Newsletter: {keywords}"
                elif domain:
                    subject = f"Newsletter: {domain} Insights"

                # 이메일 발송
                send_email_func(to=email, subject=subject, html=result["content"])
                email_sent = True
                print(f"[SUCCESS] Successfully sent email to {email}")
            except Exception as e:
                print(f"[WARNING] Failed to send email to {email}: {str(e)}")
                # 이메일 발송 실패해도 뉴스레터 생성은 성공으로 처리

        response = {
            "html_content": result["content"],
            "subject": result["title"],
            "articles_count": result.get("generation_stats", {}).get(
                "articles_count", 0
            ),
            "status": result["status"],
            "cli_output": result.get("cli_output", ""),
            "error": result.get("error"),
            "generation_stats": result.get("generation_stats", {}),
            "input_params": result.get("input_params", {}),
            "html_size": len(result["content"]) if result.get("content") else 0,
            "email_sent": email_sent,  # 이메일 발송 상태 추가
            "processing_info": {
                "using_real_cli": isinstance(newsletter_cli, RealNewsletterCLI),
                "template_style": template_style,
                "email_compatible": email_compatible,
                "period_days": period,
            },
        }

        print(f"[SUCCESS] Processing completed successfully")
        return response

    except Exception as e:
        error_msg = f"Newsletter generation failed: {str(e)}"
        print(f"[WARNING] {error_msg}")
        raise Exception(error_msg)


def process_newsletter_in_memory(data, job_id):
    """Process newsletter in memory and update task status"""
    try:
        print(f"[INFO] Starting newsletter processing for job {job_id}")
        result = process_newsletter_sync(data)

        # 메모리에 결과 저장
        in_memory_tasks[job_id] = {
            "status": "completed",
            "result": result,
            "updated_at": datetime.now().isoformat(),
        }

        print(f"[INFO] Newsletter processing completed for job {job_id}")
        print(f"[INFO] Result status: {result.get('status', 'unknown')}")
        print(
            f"[INFO] Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}"
        )

        return result
    except Exception as e:
        print(f"[WARNING] Error in process_newsletter_in_memory for job {job_id}: {e}")
        in_memory_tasks[job_id] = {
            "status": "failed",
            "error": str(e),
            "updated_at": datetime.now().isoformat(),
        }
        raise e


@app.route("/api/status/<job_id>")
def get_job_status(job_id):
    """Get status of a newsletter generation job"""
    # Check in-memory tasks first (for non-Redis mode)
    if job_id in in_memory_tasks:
        task = in_memory_tasks[job_id]
        response = {
            "job_id": job_id,
            "status": task["status"],
            "sent": task.get("sent", False),
        }

        if "result" in task:
            result = task["result"]
            # 결과가 딕셔너리인 경우 직접 반환
            if isinstance(result, dict):
                response.update(result)  # result의 모든 키를 response에 추가
                response["sent"] = result.get("sent", False)
            else:
                response["result"] = result
        if "error" in task:
            response["error"] = task["error"]

        return jsonify(response)

    # Fallback to database
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT params, result, status FROM history WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Job not found"}), 404

    params, result, status = row
    response = {
        "job_id": job_id,
        "status": status,
        "params": json.loads(params) if params else None,
        "sent": False,
    }

    if result:
        result_data = json.loads(result)
        # 결과가 딕셔너리인 경우 직접 반환
        if isinstance(result_data, dict):
            response.update(result_data)  # result_data의 모든 키를 response에 추가
            response["sent"] = result_data.get("sent", False)
        else:
            response["result"] = result_data

    return jsonify(response)


@app.route("/api/history")
def get_history():
    """Get recent newsletter generation history"""
    print(f"[INFO] Fetching history from database")

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # 모든 기록을 가져와서 completed 우선, 최신 순으로 정렬
        cursor.execute(
            """
            SELECT id, params, result, created_at, status 
            FROM history 
            ORDER BY 
                CASE WHEN status = 'completed' THEN 0 ELSE 1 END,
                created_at DESC
            LIMIT 20
        """
        )
        rows = cursor.fetchall()
        conn.close()

        print(f"[INFO] Found {len(rows)} history records")

    except Exception as e:
        print(f"[WARNING] Database error in get_history: {e}")
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    history = []
    for row in rows:
        job_id, params, result, created_at, status = row
        print(f"[INFO] Processing history record: {job_id} (status: {status})")

        try:
            parsed_params = json.loads(params) if params else None
        except json.JSONDecodeError as e:
            print(f"[WARNING] Failed to parse params for job {job_id}: {e}")
            parsed_params = None

        try:
            parsed_result = json.loads(result) if result else None
        except json.JSONDecodeError as e:
            print(f"[WARNING] Failed to parse result for job {job_id}: {e}")
            parsed_result = None

        history.append(
            {
                "id": job_id,
                "params": parsed_params,
                "result": parsed_result,
                "created_at": created_at,
                "status": status,
            }
        )

    print(f"[INFO] Returning {len(history)} history records")
    return jsonify(history)


@app.route("/api/schedule", methods=["POST"])
def create_schedule():
    """Create a recurring newsletter schedule"""
    data = request.get_json()

    if not data or not data.get("rrule") or not data.get("email"):
        return jsonify({"error": "Missing required fields: rrule, email"}), 400

    # Keywords나 domain 중 하나는 필수
    if not data.get("keywords") and not data.get("domain"):
        return jsonify({"error": "Either keywords or domain is required"}), 400

    try:
        # RRULE 파싱 및 다음 실행 시간 계산
        from dateutil.rrule import rrulestr

        rrule_str = data["rrule"]
        rrule = rrulestr(rrule_str, dtstart=datetime.now())
        next_run = rrule.after(datetime.now())

        if not next_run:
            return jsonify({"error": "Invalid RRULE: no future occurrences"}), 400

    except Exception as e:
        return jsonify({"error": f"Invalid RRULE: {str(e)}"}), 400

    schedule_id = str(uuid.uuid4())

    # 스케줄 데이터 준비
    schedule_params = {
        "keywords": data.get("keywords"),
        "domain": data.get("domain"),
        "email": data["email"],
        "template_style": data.get("template_style", "compact"),
        "email_compatible": data.get("email_compatible", True),
        "period": data.get("period", 14),
    }

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO schedules (id, params, rrule, next_run) VALUES (?, ?, ?, ?)",
        (schedule_id, json.dumps(schedule_params), rrule_str, next_run.isoformat()),
    )
    conn.commit()
    conn.close()

    return (
        jsonify(
            {
                "status": "scheduled",
                "schedule_id": schedule_id,
                "next_run": next_run.isoformat(),
            }
        ),
        201,
    )


@app.route("/api/schedules")
def get_schedules():
    """Get all active schedules"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, params, rrule, next_run, created_at, enabled FROM schedules WHERE enabled = 1 ORDER BY next_run ASC"
    )
    rows = cursor.fetchall()
    conn.close()

    schedules = []
    for row in rows:
        schedule_id, params, rrule, next_run, created_at, enabled = row
        schedules.append(
            {
                "id": schedule_id,
                "params": json.loads(params) if params else None,
                "rrule": rrule,
                "next_run": next_run,
                "created_at": created_at,
                "enabled": bool(enabled),
            }
        )

    return jsonify(schedules)


@app.route("/api/schedule/<schedule_id>", methods=["DELETE"])
def delete_schedule(schedule_id):
    """Cancel a recurring schedule"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE schedules SET enabled = 0 WHERE id = ?", (schedule_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    if affected == 0:
        return jsonify({"error": "Schedule not found"}), 404

    return jsonify({"status": "cancelled"})


@app.route("/api/schedule/<schedule_id>/run", methods=["POST"])
def run_schedule_now(schedule_id):
    """Immediately execute a scheduled newsletter"""
    try:
        # 스케줄 정보 조회
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT params, enabled FROM schedules WHERE id = ?", (schedule_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({"error": "Schedule not found"}), 404

        params_json, enabled = row
        if not enabled:
            return jsonify({"error": "Schedule is disabled"}), 400

        params = json.loads(params_json)

        # 즉시 뉴스레터 생성 작업 큐에 추가
        if redis_conn and task_queue:
            job = task_queue.enqueue(
                generate_newsletter_task, params, job_timeout="10m"
            )

            return jsonify(
                {
                    "status": "queued",
                    "job_id": job.id,
                    "message": "Newsletter generation started",
                }
            )
        else:
            # Redis가 없는 경우 직접 실행
            result = generate_newsletter_task(params)
            return jsonify({"status": "completed", "result": result})

    except Exception as e:
        logging.error(f"Failed to run schedule {schedule_id}: {e}")
        return jsonify({"error": f"Failed to execute schedule: {str(e)}"}), 500


@app.route("/debug/history-table")
def debug_history_table():
    """Debug endpoint to check history table status"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Get table info
        cursor.execute("PRAGMA table_info(history)")
        table_info = cursor.fetchall()

        # Get record count
        cursor.execute("SELECT COUNT(*) FROM history")
        total_count = cursor.fetchone()[0]

        # Get recent records with minimal info
        cursor.execute(
            "SELECT id, status, created_at FROM history ORDER BY created_at DESC LIMIT 5"
        )
        recent_records = cursor.fetchall()

        # Get status distribution
        cursor.execute("SELECT status, COUNT(*) FROM history GROUP BY status")
        status_distribution = cursor.fetchall()

        conn.close()

        return jsonify(
            {
                "table_info": table_info,
                "total_records": total_count,
                "recent_records": [
                    {"id": r[0], "status": r[1], "created_at": r[2]}
                    for r in recent_records
                ],
                "status_distribution": [
                    {"status": r[0], "count": r[1]} for r in status_distribution
                ],
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/debug/clear-pending")
def clear_pending_records():
    """Debug endpoint to clear pending records (개발용)"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Get pending count before deletion
        cursor.execute("SELECT COUNT(*) FROM history WHERE status = 'pending'")
        pending_count = cursor.fetchone()[0]

        # Delete pending records
        cursor.execute("DELETE FROM history WHERE status = 'pending'")
        deleted_count = cursor.rowcount

        conn.commit()
        conn.close()

        return jsonify(
            {
                "message": f"Cleared {deleted_count} pending records",
                "pending_before": pending_count,
                "deleted": deleted_count,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health_check():
    """Enhanced health check endpoint for Railway"""
    import os

    # 기본 상태
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "newsletter-generator",
        "version": "1.0.0",
    }

    # 의존성 상태 체크
    deps = {}
    overall_status = "healthy"

    # Redis 연결 상태
    try:
        if redis_conn:
            redis_conn.ping()
            deps["redis"] = {"status": "connected", "message": "Redis is healthy"}
        else:
            deps["redis"] = {"status": "unavailable", "message": "Redis not configured"}
    except Exception as e:
        deps["redis"] = {"status": "error", "message": f"Redis error: {str(e)}"}
        overall_status = "degraded"

    # 데이터베이스 상태
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        deps["database"] = {
            "status": "connected",
            "message": "SQLite database is healthy",
        }
    except Exception as e:
        deps["database"] = {"status": "error", "message": f"Database error: {str(e)}"}
        overall_status = "error"

    # 환경 변수 체크
    env_vars = {
        "SERPER_API_KEY": bool(os.getenv("SERPER_API_KEY")),
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        "GEMINI_API_KEY": bool(os.getenv("GEMINI_API_KEY")),
        "SENTRY_DSN": bool(os.getenv("SENTRY_DSN")),
    }

    # 최소 요구사항 확인
    has_serper = env_vars["SERPER_API_KEY"]
    has_llm = any([env_vars["OPENAI_API_KEY"], env_vars["GEMINI_API_KEY"]])

    if has_serper and has_llm:
        deps["config"] = {
            "status": "healthy",
            "message": "Required environment variables are set",
        }
    else:
        missing = []
        if not has_serper:
            missing.append("SERPER_API_KEY")
        if not has_llm:
            missing.append("LLM API key (OpenAI or Gemini)")

        deps["config"] = {
            "status": "warning",
            "message": f"Missing required variables: {', '.join(missing)}",
        }
        if overall_status == "healthy":
            overall_status = "degraded"

    # Mock 모드 체크
    mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"
    deps["mock_mode"] = {
        "status": "info",
        "enabled": mock_mode,
        "message": (
            "Running in mock mode" if mock_mode else "Running in production mode"
        ),
    }

    # 뉴스레터 CLI 상태
    try:
        cli_type = type(newsletter_cli).__name__
        deps["newsletter_cli"] = {
            "status": "healthy",
            "type": cli_type,
            "message": f"Newsletter CLI is ready ({cli_type})",
        }
    except Exception as e:
        deps["newsletter_cli"] = {"status": "error", "message": f"CLI error: {str(e)}"}
        overall_status = "error"

    # 파일 시스템 체크
    try:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "output")
        os.makedirs(output_dir, exist_ok=True)
        test_file = os.path.join(output_dir, "health_check.txt")
        with open(test_file, "w") as f:
            f.write("health check")
        os.remove(test_file)
        deps["filesystem"] = {"status": "healthy", "message": "File system is writable"}
    except Exception as e:
        deps["filesystem"] = {
            "status": "error",
            "message": f"File system error: {str(e)}",
        }
        overall_status = "error"

    health_status["status"] = overall_status
    health_status["dependencies"] = deps

    # HTTP 상태 코드 결정
    status_code = 200
    if overall_status == "error":
        status_code = 503
    elif overall_status == "degraded":
        status_code = 200  # 여전히 서비스 가능하므로 200

    return jsonify(health_status), status_code


@app.route("/test")
def test():
    """Simple test route"""
    return "Flask is working! Template folder: " + str(app.template_folder)


@app.route("/test-db")
def test_db():
    """Serve the database test HTML page"""
    try:
        with open(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_api.html"),
            "r",
        ) as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Test file not found</h1>", 404


@app.route("/test-template")
def test_template():
    """Test template rendering"""
    try:
        return render_template("test.html")
    except Exception as e:
        return f"Template error: {str(e)}", 500


@app.route("/test-api")
def test_api():
    """API test page"""
    return render_template("test.html")


@app.route("/manual-test")
def manual_test():
    """Manual test page for newsletter generation workflow"""
    return render_template("manual_test.html")


@app.route("/api/send-email", methods=["POST"])
def send_email_api():
    """생성된 뉴스레터를 이메일로 발송"""
    try:
        data = request.get_json()
        job_id = data.get("job_id")
        email = data.get("email")

        if not job_id or not email:
            return jsonify({"error": "job_id와 email이 필요합니다"}), 400

        # 작업 상태 확인
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status, result, params FROM history WHERE id = ?", (job_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({"error": "작업을 찾을 수 없습니다"}), 404

        status, result_json, params_json = row
        if status != "completed":
            return jsonify({"error": "완료되지 않은 작업입니다"}), 400

        result = json.loads(result_json) if result_json else {}
        params = json.loads(params_json) if params_json else {}

        html_content = result.get("html_content")
        if not html_content:
            return jsonify({"error": "발송할 콘텐츠가 없습니다"}), 400

        # 이메일 발송 - try-except로 import 처리
        try:
            import mail

            send_email_func = mail.send_email
        except ImportError:
            try:
                from . import mail

                send_email_func = mail.send_email
            except ImportError:
                return (
                    jsonify(
                        {
                            "error": "이메일 모듈을 찾을 수 없습니다. mail.py 파일을 확인해주세요."
                        }
                    ),
                    500,
                )

        # 제목 생성
        keywords = params.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [keywords]

        subject = (
            f"Newsletter: {', '.join(keywords) if keywords else 'Your Newsletter'}"
        )

        # 이메일 발송
        send_email_func(to=email, subject=subject, html=html_content)

        return jsonify(
            {"success": True, "message": "이메일이 성공적으로 발송되었습니다"}
        )

    except Exception as e:
        logging.error(f"Email sending failed: {e}")
        return jsonify({"error": f"이메일 발송 실패: {str(e)}"}), 500


@app.route("/api/email-config")
def check_email_config():
    """이메일 설정 상태를 확인"""
    try:
        # 이메일 설정 확인 함수 import
        try:
            import mail

            check_config_func = mail.check_email_configuration
        except ImportError:
            try:
                from . import mail

                check_config_func = mail.check_email_configuration
            except ImportError:
                return jsonify({"error": "이메일 모듈을 찾을 수 없습니다."}), 500

        config_status = check_config_func()

        return jsonify(
            {
                "postmark_token_configured": config_status["postmark_token_configured"],
                "from_email_configured": config_status["from_email_configured"],
                "ready": config_status["ready"],
                "message": (
                    "이메일 발송 준비 완료"
                    if config_status["ready"]
                    else "환경변수 설정이 필요합니다"
                ),
            }
        )

    except Exception as e:
        logging.error(f"Email config check failed: {e}")
        return jsonify({"error": f"설정 확인 실패: {str(e)}"}), 500


@app.route("/api/test-email", methods=["POST"])
def send_test_email_api():
    """테스트 이메일을 발송"""
    try:
        data = request.get_json()
        email = data.get("email")

        if not email:
            return jsonify({"error": "이메일 주소가 필요합니다"}), 400

        # 이메일 형식 간단 검증
        if "@" not in email or "." not in email:
            return jsonify({"success": False, "error": "Invalid email format"}), 400

        # 테스트 이메일 발송 함수 import
        try:
            import mail

            send_test_func = mail.send_test_email
        except ImportError:
            try:
                from . import mail

                send_test_func = mail.send_test_email
            except ImportError:
                return jsonify({"error": "이메일 모듈을 찾을 수 없습니다."}), 500

        response = send_test_func(to=email)

        return jsonify(
            {
                "success": True,
                "message": f"테스트 이메일이 {email}로 발송되었습니다",
                "message_id": response.get("MessageID") if response else None,
            }
        )

    except Exception as e:
        logging.error(f"Test email sending failed: {e}")
        # Handle RetryError from tenacity
        from tenacity import RetryError

        if isinstance(e, RetryError):
            return (
                jsonify(
                    {
                        "error": f"RetryError[<Future at {hex(id(e))} state=finished raised RuntimeError>]"
                    }
                ),
                500,
            )
        return jsonify({"error": f"테스트 이메일 발송 실패: {str(e)}"}), 500


@app.route("/api/newsletter-html/<job_id>")
def get_newsletter_html(job_id):
    """작업 ID에 해당하는 뉴스레터 HTML을 직접 반환"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT status, result FROM history WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return "<html><body><h1>뉴스레터를 찾을 수 없습니다</h1></body></html>", 404

        status, result_json = row
        if status != "completed":
            return (
                "<html><body><h1>뉴스레터 생성이 완료되지 않았습니다</h1></body></html>",
                400,
            )

        result = json.loads(result_json) if result_json else {}
        html_content = result.get("html_content", "")

        if not html_content:
            return "<html><body><h1>뉴스레터 콘텐츠가 없습니다</h1></body></html>", 404

        # HTML 콘텐츠를 직접 반환 (UTF-8 인코딩 명시)
        return html_content, 200, {"Content-Type": "text/html; charset=utf-8"}

    except Exception as e:
        error_html = f"""
        <html>
        <head><meta charset="utf-8"></head>
        <body>
            <h1>오류 발생</h1>
            <p>뉴스레터를 불러오는 중 오류가 발생했습니다: {str(e)}</p>
        </body>
        </html>
        """
        return error_html, 500, {"Content-Type": "text/html; charset=utf-8"}


# Blueprint imports
from suggest import bp as suggest_bp

# Register blueprints
app.register_blueprint(suggest_bp)


# 애플리케이션 시작 시 API 키 검사
def initialize_app():
    """애플리케이션 초기화 - API 키 검사 포함"""
    print("🚀 Newsletter Generator Web Service 초기화 중...")

    try:
        # API 키 검사
        cli = RealNewsletterCLI()
        api_status = cli._check_api_keys()

        if api_status["status"] == "success":
            print("✅ 애플리케이션 초기화 완료")
        else:
            print("⚠️ 애플리케이션 초기화 완료 (일부 기능 제한)")

        return api_status

    except Exception as e:
        print(f"❌ 애플리케이션 초기화 실패: {e}")
        return {"status": "error", "error": str(e)}


# 애플리케이션 초기화 실행
app_initialization_status = initialize_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    print(f"[INFO] Starting Flask app on port {port}, debug={debug}")
    app.run(host="0.0.0.0", port=port, debug=True)
