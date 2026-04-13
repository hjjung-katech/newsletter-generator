"""Route registration for schedule drift visibility."""

from __future__ import annotations

import logging

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue

try:
    from schedule_drift import detect_schedule_drift
except ImportError:
    from web.schedule_drift import detect_schedule_drift  # pragma: no cover

try:
    from ops_logging import log_exception, log_info
except ImportError:
    from web.ops_logging import log_exception, log_info  # pragma: no cover


logger = logging.getLogger("web.routes_ops_schedule_drift")


def register_schedule_drift_routes(app: Flask, database_path: str) -> None:
    """Register the schedule drift visibility route on the given Flask app."""

    @app.route("/api/ops/schedule-drift", methods=["GET"])  # type: ignore[untyped-decorator]
    def ops_schedule_drift() -> ResponseReturnValue:
        """Return the current schedule drift report."""
        try:
            threshold = request.args.get("threshold_seconds", type=int)
            report = detect_schedule_drift(
                database_path,
                threshold_seconds=threshold,
            )
            payload = report.to_dict()
            log_info(
                logger,
                "ops.schedule_drift.listed",
                drifted_count=payload["drifted_count"],
                active_schedule_count=payload["active_schedule_count"],
                status=payload["status"],
            )
            return jsonify(payload)
        except Exception as exc:
            log_exception(logger, "ops.schedule_drift.list_failed", exc)
            return (
                jsonify({"error": f"Schedule drift lookup failed: {exc}"}),
                500,
            )
