"""Route registration for debug and local test endpoints."""

import os
import sqlite3

from flask import Flask, jsonify, render_template
from flask.typing import ResponseReturnValue


def _should_enable_debug_routes(
    app: Flask, enable_debug_routes: bool | None = None
) -> bool:
    """Return whether debug/test helper routes should be exposed."""
    if enable_debug_routes is not None:
        return enable_debug_routes

    override = os.getenv("ENABLE_DEBUG_ROUTES")
    if override is not None:
        return override.strip().lower() in {"1", "true", "yes", "on"}

    if app.config.get("TESTING"):
        return True

    app_env = os.getenv("APP_ENV", "").strip().lower()
    flask_env = os.getenv("FLASK_ENV", "").strip().lower()
    return app_env == "development" or flask_env == "development"


def register_ops_routes(
    app: Flask,
    database_path: str,
    enable_debug_routes: bool | None = None,
) -> None:
    """Register operational routes on the given Flask app."""
    if not _should_enable_debug_routes(app, enable_debug_routes):
        return

    @app.route("/debug/history-table")  # type: ignore[untyped-decorator]
    def debug_history_table() -> ResponseReturnValue:
        """Debug endpoint to check history table status"""
        try:
            conn = sqlite3.connect(database_path)
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(history)")
            table_info = cursor.fetchall()

            cursor.execute("SELECT COUNT(*) FROM history")
            total_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT id, status, created_at FROM history ORDER BY created_at DESC LIMIT 5"
            )
            recent_records = cursor.fetchall()

            cursor.execute("SELECT status, COUNT(*) FROM history GROUP BY status")
            status_distribution = cursor.fetchall()

            conn.close()

            return jsonify(
                {
                    "table_info": table_info,
                    "total_records": total_count,
                    "recent_records": [
                        {"id": row[0], "status": row[1], "created_at": row[2]}
                        for row in recent_records
                    ],
                    "status_distribution": [
                        {"status": row[0], "count": row[1]}
                        for row in status_distribution
                    ],
                }
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/debug/clear-pending")  # type: ignore[untyped-decorator]
    def clear_pending_records() -> ResponseReturnValue:
        """Debug endpoint to clear pending records (개발용)"""
        try:
            conn = sqlite3.connect(database_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM history WHERE status = 'pending'")
            pending_count = cursor.fetchone()[0]

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

    @app.route("/test")  # type: ignore[untyped-decorator]
    def test() -> ResponseReturnValue:
        """Simple test route"""
        return "Flask is working! Template folder: " + str(app.template_folder)

    @app.route("/test-db")  # type: ignore[untyped-decorator]
    def test_db() -> ResponseReturnValue:
        """Serve the database test HTML page"""
        try:
            with open(
                os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), "test_api.html"
                ),
                "r",
            ) as handle:
                return handle.read()
        except FileNotFoundError:
            return "<h1>Test file not found</h1>", 404

    @app.route("/test-template")  # type: ignore[untyped-decorator]
    def test_template() -> ResponseReturnValue:
        """Test template rendering"""
        try:
            return render_template("test.html")
        except Exception as e:
            return f"Template error: {str(e)}", 500

    @app.route("/test-api")  # type: ignore[untyped-decorator]
    def test_api() -> ResponseReturnValue:
        """API test page"""
        return render_template("test.html")

    @app.route("/manual-test")  # type: ignore[untyped-decorator]
    def manual_test() -> ResponseReturnValue:
        """Manual test page for newsletter generation workflow"""
        return render_template("manual_test.html")
