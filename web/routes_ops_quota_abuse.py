"""Operational route for quota and rate-limit abuse observability.

Exposes aggregated rate-limit violation events recorded by the
``_QuotaAbuseTracker`` that ``configure_access_control()`` attaches to
``app.extensions["quota_abuse_tracker"]``.  Protected under the standard
``/api/ops`` prefix (requires ``SCOPE_OPS`` token).

The tracker is in-process and resets on restart.  It is not persisted to the
database.  For persistent audit logs, correlate with the structured WARNING
lines emitted by ``access_control._record_abuse_event``.
"""

from __future__ import annotations

import logging

from flask import Flask, current_app, jsonify
from flask.typing import ResponseReturnValue

try:
    from ops_logging import log_exception, log_info
except ImportError:  # pragma: no cover
    from web.ops_logging import log_exception, log_info

logger = logging.getLogger("web.routes_ops_quota_abuse")


def register_quota_abuse_routes(app: Flask, database_path: str) -> None:
    """Register quota/abuse visibility routes on the given Flask app.

    ``database_path`` is accepted for API consistency with other route
    registration functions but is not used — events are in-memory only.
    """

    @app.route("/api/ops/quota-abuse", methods=["GET"])  # type: ignore[untyped-decorator]
    def ops_quota_abuse() -> ResponseReturnValue:
        """Return recent rate-limit violation events and summary statistics."""
        try:
            tracker = current_app.extensions.get("quota_abuse_tracker")
            if tracker is None:
                return jsonify(
                    {
                        "events": [],
                        "summary": {
                            "returned": 0,
                            "total_recorded": 0,
                            "tracker_enabled": False,
                        },
                    }
                )

            events = tracker.recent(limit=100)
            payload = {
                # most-recent first so operators see the latest violations at top
                "events": [
                    {
                        "timestamp": e.timestamp,
                        "client_id": e.client_id,
                        "path": e.path,
                        "retry_after_seconds": e.retry_after_seconds,
                    }
                    for e in reversed(events)
                ],
                "summary": {
                    "returned": len(events),
                    "total_recorded": tracker.total_recorded,
                    "tracker_enabled": True,
                },
            }
            log_info(
                logger,
                "ops.quota_abuse.listed",
                returned=len(events),
                total_recorded=tracker.total_recorded,
            )
            return jsonify(payload)
        except Exception as exc:
            log_exception(logger, "ops.quota_abuse.list_failed", exc)
            return (
                jsonify({"error": f"Quota abuse listing failed: {exc}"}),
                500,
            )
