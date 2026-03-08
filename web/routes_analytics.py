"""Protected analytics dashboard routes for the canonical web runtime."""

from __future__ import annotations

import logging

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue

try:
    from db_state import get_analytics_dashboard_data
except ImportError:
    from web.db_state import get_analytics_dashboard_data  # pragma: no cover

try:
    from ops_logging import log_exception, log_info
except ImportError:
    from web.ops_logging import log_exception, log_info  # pragma: no cover


logger = logging.getLogger("web.routes_analytics")


def register_analytics_routes(app: Flask, database_path: str) -> None:
    """Register analytics API routes on the given Flask app."""

    @app.route("/api/analytics", methods=["GET"])  # type: ignore[untyped-decorator]
    def analytics_dashboard() -> ResponseReturnValue:
        """Return aggregated metrics and recent analytics events."""
        try:
            raw_window_days = request.args.get("window_days", type=int)
            raw_recent_limit = request.args.get("recent_limit", type=int)
            window_days = 7 if raw_window_days is None else raw_window_days
            recent_limit = 25 if raw_recent_limit is None else raw_recent_limit
            payload = get_analytics_dashboard_data(
                database_path,
                window_days=max(1, min(window_days, 90)),
                recent_limit=max(1, min(recent_limit, 100)),
            )
            log_info(
                logger,
                "analytics.loaded",
                window_days=payload["window_days"],
                recent_count=len(payload["recent_events"]),
            )
            return jsonify(payload)
        except Exception as exc:
            log_exception(logger, "analytics.load_failed", exc)
            return jsonify({"error": f"Analytics load failed: {exc}"}), 500
