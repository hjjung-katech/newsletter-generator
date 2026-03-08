"""Archive search and detail routes for prior newsletter editions."""

from __future__ import annotations

import logging

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue

try:
    from db_state import get_archive_entry, search_archive_entries
except ImportError:
    from web.db_state import (  # pragma: no cover
        get_archive_entry,
        search_archive_entries,
    )

try:
    from ops_logging import log_exception, log_info
except ImportError:
    from web.ops_logging import log_exception, log_info  # pragma: no cover


logger = logging.getLogger("web.routes_archive")


def register_archive_routes(app: Flask, database_path: str) -> None:
    """Register read-only archive search and detail endpoints."""

    @app.route("/api/archive/search")  # type: ignore[untyped-decorator]
    def search_archive() -> ResponseReturnValue:
        raw_limit = request.args.get("limit", type=int)
        limit = 10 if raw_limit is None else raw_limit
        normalized_limit = max(1, min(limit, 50))
        query = (request.args.get("q") or "").strip()

        try:
            results = search_archive_entries(
                database_path,
                query=query or None,
                limit=normalized_limit,
            )
            log_info(
                logger,
                "archive.search.completed",
                query=query,
                limit=normalized_limit,
                count=len(results),
            )
            return jsonify(
                {
                    "query": query,
                    "count": len(results),
                    "results": results,
                }
            )
        except Exception as exc:  # pragma: no cover - defensive route wrapper
            log_exception(logger, "archive.search.failed", exc, query=query)
            return jsonify({"error": f"Archive search failed: {str(exc)}"}), 500

    @app.route("/api/archive/<job_id>")  # type: ignore[untyped-decorator]
    def get_archive(job_id: str) -> ResponseReturnValue:
        try:
            entry = get_archive_entry(database_path, job_id)
            if entry is None:
                return jsonify({"error": "Archive entry not found"}), 404

            log_info(logger, "archive.detail.loaded", job_id=job_id)
            return jsonify(entry)
        except Exception as exc:  # pragma: no cover - defensive route wrapper
            log_exception(logger, "archive.detail.failed", exc, job_id=job_id)
            return jsonify({"error": f"Archive lookup failed: {str(exc)}"}), 500
