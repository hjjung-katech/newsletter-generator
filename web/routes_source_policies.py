"""Route registration for source allow/block policy management."""

from __future__ import annotations

import logging
import sqlite3
import uuid

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue

from newsletter_core.public.source_policies import normalize_source_pattern

try:
    from db_state import (
        SOURCE_POLICY_ALLOW,
        SOURCE_POLICY_BLOCK,
        create_source_policy,
        delete_source_policy,
        get_source_policy,
        list_source_policies,
        update_source_policy,
    )
except ImportError:
    from web.db_state import (  # pragma: no cover
        SOURCE_POLICY_ALLOW,
        SOURCE_POLICY_BLOCK,
        create_source_policy,
        delete_source_policy,
        get_source_policy,
        list_source_policies,
        update_source_policy,
    )

try:
    from ops_logging import log_exception, log_info
except ImportError:
    from web.ops_logging import log_exception, log_info  # pragma: no cover

logger = logging.getLogger("web.routes_source_policies")

VALID_POLICY_TYPES = {SOURCE_POLICY_ALLOW, SOURCE_POLICY_BLOCK}


def _normalize_policy_payload(payload: dict) -> tuple[str, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")

    pattern = normalize_source_pattern(str(payload.get("pattern", "") or ""))
    if not pattern:
        raise ValueError("pattern is required")
    if len(pattern) > 255:
        raise ValueError("pattern must be 255 characters or fewer")

    policy_type = str(payload.get("policy_type", "") or "").strip().lower()
    if policy_type not in VALID_POLICY_TYPES:
        raise ValueError("policy_type must be one of: allow, block")

    return pattern, policy_type, bool(payload.get("is_active", True))


def register_source_policy_routes(app: Flask, database_path: str) -> None:
    """Register source allow/block policy CRUD routes."""

    @app.route("/api/source-policies")  # type: ignore[untyped-decorator]
    def list_source_policy_entries() -> ResponseReturnValue:
        try:
            return jsonify(list_source_policies(database_path))
        except Exception as exc:
            log_exception(logger, "source_policy.list.failed", exc)
            return jsonify({"error": "소스 정책 목록을 불러오지 못했습니다"}), 500

    @app.route("/api/source-policies", methods=["POST"])  # type: ignore[untyped-decorator]
    def create_source_policy_entry() -> ResponseReturnValue:
        try:
            payload = request.get_json() or {}
            pattern, policy_type, is_active = _normalize_policy_payload(payload)
            policy = create_source_policy(
                db_path=database_path,
                policy_id=f"policy_{uuid.uuid4().hex[:12]}",
                pattern=pattern,
                policy_type=policy_type,
                is_active=is_active,
            )
            log_info(
                logger,
                "source_policy.create.completed",
                policy_id=policy["id"],
                policy_type=policy_type,
            )
            return jsonify(policy), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except sqlite3.IntegrityError:
            return jsonify({"error": "같은 정책이 이미 존재합니다"}), 409
        except Exception as exc:
            log_exception(logger, "source_policy.create.failed", exc)
            return jsonify({"error": "소스 정책 저장에 실패했습니다"}), 500

    @app.route("/api/source-policies/<policy_id>", methods=["PUT"])  # type: ignore[untyped-decorator]
    def update_source_policy_entry(policy_id: str) -> ResponseReturnValue:
        try:
            payload = request.get_json() or {}
            pattern, policy_type, is_active = _normalize_policy_payload(payload)
            policy = update_source_policy(
                db_path=database_path,
                policy_id=policy_id,
                pattern=pattern,
                policy_type=policy_type,
                is_active=is_active,
            )
            if not policy:
                return jsonify({"error": "소스 정책을 찾을 수 없습니다"}), 404
            log_info(logger, "source_policy.update.completed", policy_id=policy_id)
            return jsonify(policy)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except sqlite3.IntegrityError:
            return jsonify({"error": "같은 정책이 이미 존재합니다"}), 409
        except Exception as exc:
            log_exception(
                logger, "source_policy.update.failed", exc, policy_id=policy_id
            )
            return jsonify({"error": "소스 정책 수정에 실패했습니다"}), 500

    @app.route("/api/source-policies/<policy_id>", methods=["DELETE"])  # type: ignore[untyped-decorator]
    def delete_source_policy_entry(policy_id: str) -> ResponseReturnValue:
        try:
            policy = get_source_policy(database_path, policy_id)
            if not policy:
                return jsonify({"error": "소스 정책을 찾을 수 없습니다"}), 404

            deleted = delete_source_policy(database_path, policy_id)
            if not deleted:
                return jsonify({"error": "소스 정책을 찾을 수 없습니다"}), 404

            log_info(logger, "source_policy.delete.completed", policy_id=policy_id)
            return jsonify({"success": True, "deleted_id": policy_id})
        except Exception as exc:
            log_exception(
                logger, "source_policy.delete.failed", exc, policy_id=policy_id
            )
            return jsonify({"error": "소스 정책 삭제에 실패했습니다"}), 500
