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
from typing import Any, cast

import redis
from flask import Flask, jsonify, render_template, request, send_file

# Add current directory to path for local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from cors_config import configure_cors
except ImportError:
    from web.cors_config import configure_cors  # pragma: no cover

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

try:
    from db_state import ensure_database_schema
except ImportError:
    from web.db_state import ensure_database_schema  # pragma: no cover

# Import web types module - will be loaded later to avoid conflicts


try:
    from sentry_integration import setup_sentry
except ImportError:
    from web.sentry_integration import setup_sentry  # pragma: no cover

set_sentry_user_context, set_sentry_tags = setup_sentry()


# Add the parent directory to the path to import newsletter modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 프로젝트 루트를 파이썬 패스에 추가
project_root = resolve_project_root()
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import task function for RQ
from tasks import generate_newsletter_task

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
configure_cors(app)

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
        print("Windows detected: Using direct processing instead of Redis Queue")
        redis_conn = None
        task_queue = None
    else:
        from rq import Queue

        redis_conn = redis.from_url(app.config["REDIS_URL"])
        redis_conn.ping()  # Test connection
        task_queue = Queue(QUEUE_NAME, connection=redis_conn)
        print("Redis connected successfully")
except Exception as e:
    print(f"Redis connection failed: {e}. Using in-memory processing.")
    redis_conn = None
    task_queue = None

# In-memory task storage for when Redis is unavailable
in_memory_tasks: dict[str, dict[str, Any]] = {}

# Database initialization
DATABASE_PATH = resolve_database_path()


def init_db() -> None:
    """Initialize SQLite database with required tables"""
    ensure_database_schema(DATABASE_PATH)


# Initialize database on startup
init_db()


@app.route("/")  # type: ignore[untyped-decorator]
def index() -> str | tuple[str, int]:
    """Main dashboard page"""
    try:
        print(f"Template folder: {app.template_folder}")
        print(f"App root path: {app.root_path}")
        template_path = os.path.join(app.template_folder, "index.html")
        print(f"Template path: {template_path}")
        print(f"Template exists: {os.path.exists(template_path)}")
        return cast(str, render_template("index.html"))
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
    app.run(host="0.0.0.0", port=port, debug=debug)
