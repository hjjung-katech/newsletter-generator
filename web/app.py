# flake8: noqa
"""
Newsletter Generator Web Service
Flask application that provides web interface for the CLI newsletter generator
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from pathlib import Path
from typing import Any, cast

import redis
from flask import Flask, render_template

WEB_DIR = Path(__file__).resolve().parent
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

if __package__ in {None, ""}:
    REPO_ROOT = Path(__file__).resolve().parents[1]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

from newsletter_core.public.settings import get_setting_value
from web.access_control import configure_access_control
from web.cors_config import configure_cors
from web.db_state import ensure_database_schema
from web.newsletter_clients import create_newsletter_cli
from web.ops_logging import log_exception, log_info, log_warning
from web.routes_analytics import register_analytics_routes
from web.routes_approval import register_approval_routes
from web.routes_archive import register_archive_routes
from web.routes_email_api import register_email_api_routes
from web.routes_generation import register_generation_routes
from web.routes_health import register_health_route
from web.routes_newsletter_html import register_newsletter_html_route
from web.routes_ops import register_ops_routes
from web.routes_presets import register_preset_routes
from web.routes_send_email import register_send_email_route
from web.routes_source_policies import register_source_policy_routes
from web.runtime_paths import (
    resolve_database_path,
    resolve_static_dir,
    resolve_template_dir,
)
from web.sentry_integration import setup_sentry
from web.suggest import bp as suggest_bp

_set_sentry_user_context, _set_sentry_tags = setup_sentry()

QUEUE_NAME = str(get_setting_value("RQ_QUEUE", "default"))
DATABASE_PATH = resolve_database_path()
newsletter_cli = create_newsletter_cli()
redis_conn: Any = None
task_queue: Any = None
in_memory_tasks: dict[str, dict[str, Any]] = {}
logger = logging.getLogger("web.app")


def _configure_logging() -> logging.Logger:
    logging.basicConfig(
        level=str(get_setting_value("LOG_LEVEL", "INFO")).upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    configured_logger = logging.getLogger("web.app")
    log_info(
        configured_logger,
        "app.logging_configured",
        log_level=str(get_setting_value("LOG_LEVEL", "INFO")).upper(),
    )
    return configured_logger


def _create_task_queue(app: Flask) -> tuple[Any, Any]:
    redis_url = app.config["REDIS_URL"]

    try:
        if platform.system() == "Windows":
            log_warning(logger, "app.redis.disabled_for_windows")
            return None, None

        from rq import Queue

        connected_redis = redis.from_url(redis_url)
        connected_redis.ping()
        queue = Queue(QUEUE_NAME, connection=connected_redis)
        log_info(
            logger,
            "app.redis.connected",
            queue_name=QUEUE_NAME,
            redis_url=redis_url,
        )
        return connected_redis, queue
    except Exception as e:
        log_exception(
            logger,
            "app.redis.connection_failed",
            e,
            redis_url=redis_url,
        )
        return None, None


def _register_index_route(app: Flask) -> None:
    @app.route("/")  # type: ignore[untyped-decorator]
    def index() -> str | tuple[str, int]:
        """Main dashboard page."""
        try:
            return cast(str, render_template("index.html"))
        except Exception as e:
            template_path = os.path.join(app.template_folder, "index.html")
            log_exception(
                logger,
                "app.template.render_failed",
                e,
                template_folder=app.template_folder,
                template_path=template_path,
                template_exists=os.path.exists(template_path),
            )
            return f"Template error: {str(e)}", 500


def _register_routes(app: Flask) -> None:
    register_generation_routes(
        app=app,
        database_path=DATABASE_PATH,
        newsletter_cli=newsletter_cli,
        in_memory_tasks=in_memory_tasks,
        task_queue=task_queue,
        redis_conn=redis_conn,
        get_newsletter_cli=lambda: newsletter_cli,
    )
    register_health_route(
        app=app,
        database_path=DATABASE_PATH,
        redis_conn=redis_conn,
        newsletter_cli=newsletter_cli,
    )
    register_ops_routes(app, DATABASE_PATH)
    register_send_email_route(app, DATABASE_PATH)
    register_approval_routes(app, DATABASE_PATH)
    register_email_api_routes(app)
    register_preset_routes(app, DATABASE_PATH)
    register_source_policy_routes(app, DATABASE_PATH)
    register_analytics_routes(app, DATABASE_PATH)
    register_archive_routes(app, DATABASE_PATH)
    register_newsletter_html_route(app, DATABASE_PATH)
    app.register_blueprint(suggest_bp)


def create_app() -> Flask:
    global logger, redis_conn, task_queue

    logger = _configure_logging()

    app = Flask(
        __name__,
        template_folder=resolve_template_dir(),
        static_folder=resolve_static_dir(),
    )
    configure_cors(app)
    configure_access_control(app)

    app.config["SECRET_KEY"] = get_setting_value(
        "SECRET_KEY", "dev-key-change-in-production"
    )
    app.config["REDIS_URL"] = get_setting_value("REDIS_URL", "redis://localhost:6379/0")

    log_info(
        logger,
        "app.initialized",
        template_folder=resolve_template_dir(),
        static_folder=resolve_static_dir(),
        database_path=DATABASE_PATH,
    )

    ensure_database_schema(DATABASE_PATH)
    redis_conn, task_queue = _create_task_queue(app)
    _register_index_route(app)
    _register_routes(app)
    return app


app = create_app()


def _resolve_app_env() -> str:
    return os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "production"


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = _resolve_app_env() == "development"
    log_info(logger, "app.starting", host=host, port=port, debug=debug)
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
