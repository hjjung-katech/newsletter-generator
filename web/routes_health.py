"""Route registration for service health endpoint."""

import os
import sqlite3
from datetime import datetime
from typing import Any

from flask import Flask, jsonify
from flask.typing import ResponseReturnValue

from newsletter_core.public.settings import get_setting_value


def register_health_route(
    app: Flask,
    database_path: str,
    redis_conn: Any,
    newsletter_cli: Any,
) -> None:
    """Register health route on the given Flask app."""

    @app.route("/health")  # type: ignore[untyped-decorator]
    def health_check() -> ResponseReturnValue:
        """Enhanced health check endpoint for Railway"""
        health_status: dict[str, Any] = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "newsletter-generator",
            "version": "1.0.0",
        }

        deps: dict[str, dict[str, Any]] = {}
        overall_status = "healthy"

        try:
            if redis_conn:
                redis_conn.ping()
                deps["redis"] = {"status": "connected", "message": "Redis is healthy"}
            else:
                deps["redis"] = {
                    "status": "unavailable",
                    "message": "Redis not configured",
                }
        except Exception as e:
            deps["redis"] = {"status": "error", "message": f"Redis error: {str(e)}"}
            overall_status = "degraded"

        try:
            conn = sqlite3.connect(database_path)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()
            deps["database"] = {
                "status": "connected",
                "message": "SQLite database is healthy",
            }
        except Exception as e:
            deps["database"] = {
                "status": "error",
                "message": f"Database error: {str(e)}",
            }
            overall_status = "error"

        env_vars = {
            "SERPER_API_KEY": bool(get_setting_value("SERPER_API_KEY")),
            "OPENAI_API_KEY": bool(get_setting_value("OPENAI_API_KEY")),
            "GEMINI_API_KEY": bool(get_setting_value("GEMINI_API_KEY")),
            "SENTRY_DSN": bool(get_setting_value("SENTRY_DSN")),
        }

        mock_mode = bool(get_setting_value("MOCK_MODE", False))
        testing_mode = bool(app.config.get("TESTING"))
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
            if overall_status == "healthy" and not (mock_mode or testing_mode):
                overall_status = "degraded"

        deps["mock_mode"] = {
            "status": "info",
            "enabled": mock_mode,
            "message": (
                "Running in mock mode" if mock_mode else "Running in production mode"
            ),
        }

        try:
            cli_type = type(newsletter_cli).__name__
            deps["newsletter_cli"] = {
                "status": "healthy",
                "type": cli_type,
                "message": f"Newsletter CLI is ready ({cli_type})",
            }
        except Exception as e:
            deps["newsletter_cli"] = {
                "status": "error",
                "message": f"CLI error: {str(e)}",
            }
            overall_status = "error"

        try:
            output_dir = os.path.join(os.path.dirname(__file__), "..", "output")
            os.makedirs(output_dir, exist_ok=True)
            test_file = os.path.join(output_dir, "health_check.txt")
            with open(test_file, "w") as handle:
                handle.write("health check")
            os.remove(test_file)
            deps["filesystem"] = {
                "status": "healthy",
                "message": "File system is writable",
            }
        except Exception as e:
            deps["filesystem"] = {
                "status": "error",
                "message": f"File system error: {str(e)}",
            }
            overall_status = "error"

        health_status["status"] = overall_status
        health_status["dependencies"] = deps

        status_code = 200
        if overall_status == "error":
            status_code = 503
        elif overall_status == "degraded":
            status_code = 200

        return jsonify(health_status), status_code
