# flake8: noqa
"""
Newsletter Generator Web Service
Flask application that provides web interface for the CLI newsletter generator
"""

import json
import logging
import os
import sqlite3
import sys
import uuid
from datetime import datetime

import redis
from flask import Flask, jsonify, render_template, request, send_file
from flask_cors import CORS
from rq import Queue

# Add current directory to path for local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from runtime_paths import (
        resolve_database_path,
        resolve_env_file_path,
        resolve_project_root,
        resolve_static_dir,
        resolve_template_dir,
    )
except ImportError:
    from web.runtime_paths import (  # pragma: no cover
        resolve_database_path,
        resolve_env_file_path,
        resolve_project_root,
        resolve_static_dir,
        resolve_template_dir,
    )

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
    from newsletter_core.public.settings import get_settings

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
            print("✅ Sentry initialized successfully")

            # 실제 Sentry 함수들로 재정의
            def set_sentry_user_context(user_id=None, email=None, **kwargs):
                """Sentry에 사용자 컨텍스트 설정"""
                sentry_sdk.set_user({"id": user_id, "email": email, **kwargs})

            def set_sentry_tags(**tags):
                """Sentry에 태그 설정"""
                for key, value in tags.items():
                    sentry_sdk.set_tag(key, value)

        except ImportError:
            print("⚠️  Sentry SDK not installed, skipping Sentry integration")
        except Exception as e:
            print(f"⚠️  Sentry initialization failed: {e}")
    else:
        print("ℹ️  Sentry DSN not configured, skipping Sentry integration")

except Exception as e:
    # Centralized settings 실패 시 legacy fallback
    print(f"⚠️  Centralized settings unavailable, checking legacy SENTRY_DSN: {e}")
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
            print("✅ Sentry initialized successfully (legacy mode)")

            # 실제 Sentry 함수들로 재정의
            def set_sentry_user_context(user_id=None, email=None, **kwargs):
                """Sentry에 사용자 컨텍스트 설정"""
                sentry_sdk.set_user({"id": user_id, "email": email, **kwargs})

            def set_sentry_tags(**tags):
                """Sentry에 태그 설정"""
                for key, value in tags.items():
                    sentry_sdk.set_tag(key, value)

        except ImportError:
            print("⚠️  Sentry SDK not installed, skipping Sentry integration")
        except Exception as e:
            print(f"⚠️  Sentry initialization failed: {e}")
    else:
        print("ℹ️  Legacy SENTRY_DSN not configured, skipping Sentry integration")


# Import task function for RQ
from tasks import generate_newsletter_task

# Add the parent directory to the path to import newsletter modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# 현재 디렉토리를 파이썬 패스에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 프로젝트 루트를 파이썬 패스에 추가
project_root = resolve_project_root()
sys.path.insert(0, project_root)

try:
    from newsletter_clients import (
        MockNewsletterCLI,
        RealNewsletterCLI,
        create_newsletter_cli,
    )
except ImportError:
    from web.newsletter_clients import (  # pragma: no cover
        MockNewsletterCLI,
        RealNewsletterCLI,
        create_newsletter_cli,
    )

newsletter_cli = create_newsletter_cli()

app = Flask(
    __name__,
    template_folder=resolve_template_dir(),
    static_folder=resolve_static_dir(),
)
CORS(app)  # Enable CORS for frontend-backend communication

# Enable detailed logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
print("🔧 Flask app initialized with detailed logging")

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
        print("Windows detected: Using direct processing instead of Redis Queue")
        redis_conn = None
        task_queue = None
    else:
        redis_conn = redis.from_url(app.config["REDIS_URL"])
        redis_conn.ping()  # Test connection
        task_queue = Queue(QUEUE_NAME, connection=redis_conn)
        print("Redis connected successfully")
except Exception as e:
    print(f"Redis connection failed: {e}. Using in-memory processing.")
    redis_conn = None
    task_queue = None

# In-memory task storage for when Redis is unavailable
in_memory_tasks = {}

# Database initialization
DATABASE_PATH = resolve_database_path()


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


try:
    from routes_generation import register_generation_routes
except ImportError:
    from web.routes_generation import register_generation_routes  # pragma: no cover

register_generation_routes(
    app=app,
    database_path=DATABASE_PATH,
    newsletter_cli=newsletter_cli,
    in_memory_tasks=in_memory_tasks,
    task_queue=task_queue,
    redis_conn=redis_conn,
    get_newsletter_cli=lambda: newsletter_cli,
)


try:
    from routes_health import register_health_route
except ImportError:
    from web.routes_health import register_health_route  # pragma: no cover

register_health_route(
    app=app,
    database_path=DATABASE_PATH,
    redis_conn=redis_conn,
    newsletter_cli=newsletter_cli,
)


try:
    from routes_ops import register_ops_routes
except ImportError:
    from web.routes_ops import register_ops_routes  # pragma: no cover

register_ops_routes(app, DATABASE_PATH)


try:
    from routes_send_email import register_send_email_route
except ImportError:
    from web.routes_send_email import register_send_email_route  # pragma: no cover

register_send_email_route(app, DATABASE_PATH)


try:
    from routes_email_api import register_email_api_routes
except ImportError:
    from web.routes_email_api import register_email_api_routes  # pragma: no cover

register_email_api_routes(app)


try:
    from routes_newsletter_html import register_newsletter_html_route
except ImportError:
    from web.routes_newsletter_html import (
        register_newsletter_html_route,  # pragma: no cover
    )

register_newsletter_html_route(app, DATABASE_PATH)


# Blueprint imports
from suggest import bp as suggest_bp

# Register blueprints
app.register_blueprint(suggest_bp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    print(f"Starting Flask app on port {port}, debug={debug}")
    app.run(host="0.0.0.0", port=port, debug=True)
