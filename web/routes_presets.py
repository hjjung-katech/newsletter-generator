"""Route registration for saved generation preset management."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from typing import Any

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue

try:
    from db_state import (
        create_generation_preset,
        delete_generation_preset,
        get_generation_preset,
        list_generation_presets,
        update_generation_preset,
    )
except ImportError:
    from web.db_state import (  # pragma: no cover
        create_generation_preset,
        delete_generation_preset,
        get_generation_preset,
        list_generation_presets,
        update_generation_preset,
    )

try:
    from ops_logging import log_exception, log_info
except ImportError:
    from web.ops_logging import log_exception, log_info  # pragma: no cover

try:
    from web.types import EMAIL_PATTERN
except ImportError:
    from .types import EMAIL_PATTERN  # pragma: no cover

logger = logging.getLogger("web.routes_presets")

VALID_TEMPLATE_STYLES = {"compact", "detailed", "modern"}
VALID_PERIODS = {1, 7, 14, 30}


def _normalize_keywords(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_keywords = value.split(",")
    elif isinstance(value, list):
        raw_keywords = value
    else:
        raise ValueError("keywords must be a string or list")

    keywords = [
        str(keyword).strip() for keyword in raw_keywords if str(keyword).strip()
    ]
    return keywords


def _normalize_preset_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_payload, dict):
        raise ValueError("params must be an object")

    keywords = _normalize_keywords(raw_payload.get("keywords"))
    domain = str(raw_payload.get("domain", "") or "").strip()
    if bool(keywords) == bool(domain):
        raise ValueError("Provide either keywords or domain")

    template_style = str(raw_payload.get("template_style", "compact") or "").strip()
    if template_style not in VALID_TEMPLATE_STYLES:
        raise ValueError("template_style must be one of: compact, detailed, modern")

    try:
        period = int(raw_payload.get("period", 14))
    except (TypeError, ValueError) as exc:
        raise ValueError("period must be an integer") from exc
    if period not in VALID_PERIODS:
        raise ValueError("period must be one of: 1, 7, 14, 30")

    email = str(raw_payload.get("email", "") or "").strip()
    if email and not EMAIL_PATTERN.match(email):
        raise ValueError("Invalid email format")

    rrule = str(raw_payload.get("rrule", "") or "").strip()
    if rrule:
        if not email:
            raise ValueError("Scheduled presets require an email address")
        if not rrule.startswith("FREQ="):
            raise ValueError("Invalid rrule format")

    normalized = {
        "template_style": template_style,
        "email_compatible": bool(raw_payload.get("email_compatible", False)),
        "period": period,
    }
    if keywords:
        normalized["keywords"] = keywords
    if domain:
        normalized["domain"] = domain
    if email:
        normalized["email"] = email
    if rrule:
        normalized["rrule"] = rrule
    return normalized


def _normalize_preset_metadata(payload: dict[str, Any]) -> tuple[str, str | None, bool]:
    name = str(payload.get("name", "") or "").strip()
    if not name:
        raise ValueError("name is required")
    if len(name) > 80:
        raise ValueError("name must be 80 characters or fewer")

    description = str(payload.get("description", "") or "").strip() or None
    if description and len(description) > 240:
        raise ValueError("description must be 240 characters or fewer")

    return name, description, bool(payload.get("is_default", False))


def register_preset_routes(app: Flask, database_path: str) -> None:
    """Register saved generation preset routes."""

    @app.route("/api/presets")  # type: ignore[untyped-decorator]
    def list_presets() -> ResponseReturnValue:
        try:
            return jsonify(list_generation_presets(database_path))
        except Exception as exc:
            log_exception(logger, "preset.list.failed", exc)
            return jsonify({"error": "프리셋 목록을 불러오지 못했습니다"}), 500

    @app.route("/api/presets", methods=["POST"])  # type: ignore[untyped-decorator]
    def create_preset() -> ResponseReturnValue:
        try:
            payload = request.get_json() or {}
            name, description, is_default = _normalize_preset_metadata(payload)
            params = _normalize_preset_payload(payload.get("params") or {})
            preset = create_generation_preset(
                db_path=database_path,
                preset_id=f"preset_{uuid.uuid4().hex[:12]}",
                name=name,
                description=description,
                params=params,
                is_default=is_default,
            )
            log_info(logger, "preset.create.completed", preset_id=preset["id"])
            return jsonify(preset), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except sqlite3.IntegrityError:
            return jsonify({"error": "같은 이름의 프리셋이 이미 존재합니다"}), 409
        except Exception as exc:
            log_exception(logger, "preset.create.failed", exc)
            return jsonify({"error": "프리셋 저장에 실패했습니다"}), 500

    @app.route("/api/presets/<preset_id>", methods=["PUT"])  # type: ignore[untyped-decorator]
    def update_preset(preset_id: str) -> ResponseReturnValue:
        try:
            payload = request.get_json() or {}
            name, description, is_default = _normalize_preset_metadata(payload)
            params = _normalize_preset_payload(payload.get("params") or {})
            preset = update_generation_preset(
                db_path=database_path,
                preset_id=preset_id,
                name=name,
                description=description,
                params=params,
                is_default=is_default,
            )
            if not preset:
                return jsonify({"error": "프리셋을 찾을 수 없습니다"}), 404
            log_info(logger, "preset.update.completed", preset_id=preset_id)
            return jsonify(preset)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except sqlite3.IntegrityError:
            return jsonify({"error": "같은 이름의 프리셋이 이미 존재합니다"}), 409
        except Exception as exc:
            log_exception(logger, "preset.update.failed", exc, preset_id=preset_id)
            return jsonify({"error": "프리셋 수정에 실패했습니다"}), 500

    @app.route("/api/presets/<preset_id>", methods=["DELETE"])  # type: ignore[untyped-decorator]
    def delete_preset(preset_id: str) -> ResponseReturnValue:
        try:
            preset = get_generation_preset(database_path, preset_id)
            if not preset:
                return jsonify({"error": "프리셋을 찾을 수 없습니다"}), 404

            deleted = delete_generation_preset(database_path, preset_id)
            if not deleted:
                return jsonify({"error": "프리셋을 찾을 수 없습니다"}), 404

            log_info(logger, "preset.delete.completed", preset_id=preset_id)
            return jsonify({"success": True, "deleted_id": preset_id})
        except Exception as exc:
            log_exception(logger, "preset.delete.failed", exc, preset_id=preset_id)
            return jsonify({"error": "프리셋 삭제에 실패했습니다"}), 500
