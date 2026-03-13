"""Route registration for approval inbox endpoints."""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any, cast

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue

try:
    from db_state import (
        APPROVAL_STATUS_APPROVED,
        APPROVAL_STATUS_PENDING,
        APPROVAL_STATUS_REJECTED,
        DELIVERY_STATUS_APPROVED,
        DELIVERY_STATUS_DRAFT,
        update_history_review_state,
    )
except ImportError:
    from web.db_state import (  # pragma: no cover
        APPROVAL_STATUS_APPROVED,
        APPROVAL_STATUS_PENDING,
        APPROVAL_STATUS_REJECTED,
        DELIVERY_STATUS_APPROVED,
        DELIVERY_STATUS_DRAFT,
        update_history_review_state,
    )

try:
    from ops_logging import log_exception, log_info
except ImportError:
    from web.ops_logging import log_exception, log_info  # pragma: no cover

try:
    from generation_route_support import (
        build_approval_entry,
        build_approval_visibility,
        build_execution_visibility,
    )
except ImportError:
    from web.generation_route_support import (  # pragma: no cover
        build_approval_entry,
        build_approval_visibility,
        build_execution_visibility,
    )

try:
    from time_utils import get_utc_now, to_iso_utc
except ImportError:
    from web.time_utils import get_utc_now, to_iso_utc  # pragma: no cover


logger = logging.getLogger("web.routes_approval")


def _parse_json(payload: str | None) -> dict[str, Any] | None:
    if not payload:
        return None
    parsed = json.loads(payload)
    if isinstance(parsed, dict):
        return cast(dict[str, Any], parsed)
    return None


def register_approval_routes(app: Flask, database_path: str) -> None:
    """Register approval inbox routes on the given Flask app."""

    @app.route("/api/approvals")  # type: ignore[untyped-decorator]
    def get_approval_inbox() -> ResponseReturnValue:
        """Return pending approval items for manual review."""
        approval_status = request.args.get("approval_status", APPROVAL_STATUS_PENDING)
        if approval_status not in {
            APPROVAL_STATUS_PENDING,
            APPROVAL_STATUS_APPROVED,
            APPROVAL_STATUS_REJECTED,
            "all",
        }:
            return jsonify({"error": "Unsupported approval_status filter"}), 400

        conn = sqlite3.connect(database_path)
        try:
            cursor = conn.cursor()
            if approval_status == "all":
                cursor.execute(
                    """
                    SELECT
                        id,
                        params,
                        result,
                        created_at,
                        status,
                        approval_status,
                        delivery_status,
                        approved_at,
                        rejected_at,
                        approval_note
                    FROM history
                    WHERE approval_status != 'not_requested'
                    ORDER BY
                        CASE WHEN approval_status = 'pending' THEN 0 ELSE 1 END,
                        created_at DESC
                    LIMIT 50
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        id,
                        params,
                        result,
                        created_at,
                        status,
                        approval_status,
                        delivery_status,
                        approved_at,
                        rejected_at,
                        approval_note
                    FROM history
                    WHERE approval_status = ?
                    ORDER BY created_at DESC
                    LIMIT 50
                    """,
                    (approval_status,),
                )
            rows = cursor.fetchall()
        finally:
            conn.close()

        approvals = [
            build_approval_entry(
                row,
                parse_params=_parse_json,
                parse_result=_parse_json,
            )
            for row in rows
        ]

        log_info(logger, "approval.inbox.loaded", count=len(approvals))
        return jsonify(approvals)

    @app.route("/api/approvals/<job_id>/approve", methods=["POST"])  # type: ignore[untyped-decorator]
    def approve_history_item(job_id: str) -> ResponseReturnValue:
        """Approve a pending newsletter draft for manual delivery."""
        try:
            data = request.get_json(silent=True) or {}
            note = (data.get("note") or "").strip() or None

            conn = sqlite3.connect(database_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT status, approval_status, result
                    FROM history
                    WHERE id = ?
                    """,
                    (job_id,),
                )
                row = cursor.fetchone()
            finally:
                conn.close()

            if not row:
                return jsonify({"error": "작업을 찾을 수 없습니다"}), 404

            status, approval_status, result_json = row
            if status != "completed":
                return jsonify({"error": "완료된 작업만 승인할 수 있습니다"}), 400
            if approval_status != APPROVAL_STATUS_PENDING:
                return jsonify({"error": "승인 대기 중인 작업이 아닙니다"}), 400

            result = _parse_json(result_json) or {}
            if not result.get("html_content"):
                return jsonify({"error": "승인할 콘텐츠가 없습니다"}), 400

            approved_at = to_iso_utc(get_utc_now())
            update_history_review_state(
                db_path=database_path,
                job_id=job_id,
                approval_status=APPROVAL_STATUS_APPROVED,
                delivery_status=DELIVERY_STATUS_APPROVED,
                approved_at=approved_at,
                rejected_at=None,
                approval_note=note,
            )
            log_info(logger, "approval.item.approved", job_id=job_id)
            return jsonify(
                {
                    "success": True,
                    "job_id": job_id,
                    "approval_status": APPROVAL_STATUS_APPROVED,
                    "delivery_status": DELIVERY_STATUS_APPROVED,
                    "approved_at": approved_at,
                    "approval_note": note,
                    "execution_visibility": build_execution_visibility(
                        status=status,
                        approved_at=approved_at,
                        approval_status=APPROVAL_STATUS_APPROVED,
                        delivery_status=DELIVERY_STATUS_APPROVED,
                        result=result,
                    ),
                    "approval_visibility": build_approval_visibility(
                        status=status,
                        approval_status=APPROVAL_STATUS_APPROVED,
                        delivery_status=DELIVERY_STATUS_APPROVED,
                        approved_at=approved_at,
                        result=result,
                    ),
                }
            )
        except Exception as exc:
            log_exception(logger, "approval.item.approve_failed", exc, job_id=job_id)
            return jsonify({"error": f"승인 처리 실패: {str(exc)}"}), 500

    @app.route("/api/approvals/<job_id>/reject", methods=["POST"])  # type: ignore[untyped-decorator]
    def reject_history_item(job_id: str) -> ResponseReturnValue:
        """Reject a pending newsletter draft and keep it as a manual draft."""
        try:
            data = request.get_json(silent=True) or {}
            note = (data.get("note") or "").strip() or None

            conn = sqlite3.connect(database_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT status, approval_status FROM history WHERE id = ?",
                    (job_id,),
                )
                row = cursor.fetchone()
            finally:
                conn.close()

            if not row:
                return jsonify({"error": "작업을 찾을 수 없습니다"}), 404

            status, approval_status = row
            if status != "completed":
                return jsonify({"error": "완료된 작업만 반려할 수 있습니다"}), 400
            if approval_status != APPROVAL_STATUS_PENDING:
                return jsonify({"error": "승인 대기 중인 작업이 아닙니다"}), 400

            rejected_at = to_iso_utc(get_utc_now())
            update_history_review_state(
                db_path=database_path,
                job_id=job_id,
                approval_status=APPROVAL_STATUS_REJECTED,
                delivery_status=DELIVERY_STATUS_DRAFT,
                approved_at=None,
                rejected_at=rejected_at,
                approval_note=note,
            )
            log_info(logger, "approval.item.rejected", job_id=job_id)
            return jsonify(
                {
                    "success": True,
                    "job_id": job_id,
                    "approval_status": APPROVAL_STATUS_REJECTED,
                    "delivery_status": DELIVERY_STATUS_DRAFT,
                    "rejected_at": rejected_at,
                    "approval_note": note,
                    "execution_visibility": build_execution_visibility(
                        status=status,
                        rejected_at=rejected_at,
                        approval_status=APPROVAL_STATUS_REJECTED,
                        delivery_status=DELIVERY_STATUS_DRAFT,
                    ),
                    "approval_visibility": build_approval_visibility(
                        status=status,
                        approval_status=APPROVAL_STATUS_REJECTED,
                        delivery_status=DELIVERY_STATUS_DRAFT,
                        rejected_at=rejected_at,
                    ),
                }
            )
        except Exception as exc:
            log_exception(logger, "approval.item.reject_failed", exc, job_id=job_id)
            return jsonify({"error": f"반려 처리 실패: {str(exc)}"}), 500
