"""Bounded visibility helpers for preset lifecycle web routes."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from newsletter_core.public.source_policies import normalize_source_pattern

try:
    import db_core as _db_core
except ImportError:
    from web import db_core as _db_core  # pragma: no cover

try:
    from generation_route_support import build_execution_visibility
except ImportError:
    from web.generation_route_support import (  # pragma: no cover
        build_execution_visibility,
    )


def _parse_json_mapping(raw_value: str | None) -> dict[str, Any]:
    if not raw_value:
        return {}

    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}

    if isinstance(payload, dict):
        return payload
    return {}


def _normalize_keywords(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        raw_keywords = value.split(",")
    elif isinstance(value, list):
        raw_keywords = value
    else:
        raw_keywords = []

    return tuple(
        str(keyword).strip().lower() for keyword in raw_keywords if str(keyword).strip()
    )


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _normalize_match_params(params: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = params if isinstance(params, Mapping) else {}

    try:
        period = int(payload.get("period", 14))
    except (TypeError, ValueError):
        period = None

    return {
        "keywords": _normalize_keywords(payload.get("keywords")),
        "domain": normalize_source_pattern(str(payload.get("domain", "") or "")),
        "template_style": str(payload.get("template_style", "compact") or "").strip()
        or "compact",
        "email_compatible": bool(payload.get("email_compatible", False)),
        "period": period,
        "email": str(payload.get("email", "") or "").strip().lower(),
    }


def _matches_source_pattern(candidate: str, pattern: str) -> bool:
    if not candidate or not pattern:
        return False

    if "." in pattern:
        return candidate == pattern or candidate.endswith(f".{pattern}")

    return pattern in candidate


def _matches_preset_history(
    preset_params: Mapping[str, Any] | None, history_params: Mapping[str, Any] | None
) -> bool:
    normalized_preset = _normalize_match_params(preset_params)
    normalized_history = _normalize_match_params(history_params)

    return normalized_preset == normalized_history


def _load_recent_history_rows(
    db_path: str, *, limit: int = 200
) -> list[dict[str, Any]]:
    conn = _db_core.connect_db(db_path)
    try:
        cursor = conn.cursor()
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
                rejected_at
            FROM history
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    history_rows: list[dict[str, Any]] = []
    for row in rows:
        result = _parse_json_mapping(row[2])
        history_rows.append(
            {
                "id": row[0],
                "params": _parse_json_mapping(row[1]),
                "result": result,
                "created_at": row[3],
                "status": row[4],
                "approval_status": row[5],
                "delivery_status": row[6],
                "approved_at": row[7],
                "rejected_at": row[8],
                "execution_visibility": build_execution_visibility(
                    status=row[4],
                    created_at=row[3],
                    approved_at=row[7],
                    rejected_at=row[8],
                    approval_status=row[5],
                    delivery_status=row[6],
                    result=result,
                ),
            }
        )
    return history_rows


def _load_active_source_policy_groups(db_path: str) -> dict[str, list[str]]:
    conn = _db_core.connect_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT pattern, policy_type
            FROM source_policies
            WHERE is_active = 1
            ORDER BY policy_type ASC, updated_at DESC
            """
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    allowlist: list[str] = []
    blocklist: list[str] = []
    for pattern, policy_type in rows:
        normalized_pattern = normalize_source_pattern(str(pattern or ""))
        if not normalized_pattern:
            continue
        if policy_type == "allow":
            allowlist.append(normalized_pattern)
        elif policy_type == "block":
            blocklist.append(normalized_pattern)
    return {"allowlist": allowlist, "blocklist": blocklist}


def find_latest_related_execution(
    preset: Mapping[str, Any], history_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any] | None:
    preset_params = preset.get("params")
    for history_row in history_rows:
        result_mapping = _mapping_or_empty(history_row.get("result"))
        if _matches_preset_history(preset_params, history_row.get("params")):
            return {
                "job_id": history_row.get("id"),
                "created_at": history_row.get("created_at"),
                "status": history_row.get("status"),
                "approval_status": history_row.get("approval_status"),
                "delivery_status": history_row.get("delivery_status"),
                "title": result_mapping.get("title"),
                "execution_visibility": history_row.get("execution_visibility"),
            }
    return None


def build_source_policy_visibility(
    preset: Mapping[str, Any],
    active_source_policies: Mapping[str, list[str]] | None = None,
) -> dict[str, Any]:
    params = _mapping_or_empty(preset.get("params"))
    normalized_domain = normalize_source_pattern(str(params.get("domain", "") or ""))

    if not normalized_domain:
        return {
            "link_state": "unavailable",
            "message": "키워드 프리셋이라 직접 연결된 소스 정책을 확인할 수 없습니다.",
            "match_count": 0,
            "allow_match_count": 0,
            "block_match_count": 0,
        }

    policies = active_source_policies or {"allowlist": [], "blocklist": []}
    allow_matches = [
        pattern
        for pattern in policies.get("allowlist", [])
        if _matches_source_pattern(normalized_domain, pattern)
    ]
    block_matches = [
        pattern
        for pattern in policies.get("blocklist", [])
        if _matches_source_pattern(normalized_domain, pattern)
    ]
    match_count = len(allow_matches) + len(block_matches)

    if match_count:
        return {
            "link_state": "matched",
            "message": f"활성 소스 정책 {match_count}개와 연결됩니다. (allow {len(allow_matches)} / block {len(block_matches)})",
            "match_count": match_count,
            "allow_match_count": len(allow_matches),
            "block_match_count": len(block_matches),
        }

    return {
        "link_state": "none",
        "message": "이 프리셋 도메인과 일치하는 활성 소스 정책이 없습니다.",
        "match_count": 0,
        "allow_match_count": 0,
        "block_match_count": 0,
    }


def build_preset_visibility(
    preset: Mapping[str, Any],
    *,
    latest_related_execution: Mapping[str, Any] | None = None,
    source_policy_visibility: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    params = _mapping_or_empty(preset.get("params"))

    if params.get("rrule"):
        preset_type = "scheduled"
        preset_type_label = "예약 프리셋"
    elif params.get("domain"):
        preset_type = "domain"
        preset_type_label = "도메인 프리셋"
    else:
        preset_type = "keywords"
        preset_type_label = "키워드 프리셋"

    recent_execution = _mapping_or_empty(latest_related_execution)
    source_policy = _mapping_or_empty(source_policy_visibility)
    execution_visibility = _mapping_or_empty(
        recent_execution.get("execution_visibility")
    )

    has_recent_execution = bool(recent_execution.get("job_id"))
    return {
        "availability_state": "available",
        "availability_label": "사용 가능",
        "preset_type": preset_type,
        "preset_type_label": preset_type_label,
        "is_scheduled": bool(params.get("rrule")),
        "has_recent_related_execution": has_recent_execution,
        "recent_usage_state": "recent" if has_recent_execution else "empty",
        "recent_usage_label": "최근 연관 실행 있음" if has_recent_execution else "연관 실행 없음",
        "recent_usage_timestamp": recent_execution.get("created_at"),
        "recent_usage_message": execution_visibility.get(
            "status_message", "이 프리셋과 일치하는 최근 실행 이력이 없습니다."
        ),
        "has_source_policy_link": source_policy.get("link_state") == "matched",
    }


def build_preset_entry(
    preset: Mapping[str, Any],
    *,
    history_rows: Sequence[Mapping[str, Any]] | None = None,
    active_source_policies: Mapping[str, list[str]] | None = None,
) -> dict[str, Any]:
    preset_copy = dict(preset)
    latest_related_execution = find_latest_related_execution(
        preset_copy, history_rows or []
    )
    source_policy_visibility = build_source_policy_visibility(
        preset_copy, active_source_policies
    )
    preset_copy["latest_related_execution"] = latest_related_execution
    preset_copy["source_policy_visibility"] = source_policy_visibility
    preset_copy["preset_visibility"] = build_preset_visibility(
        preset_copy,
        latest_related_execution=latest_related_execution,
        source_policy_visibility=source_policy_visibility,
    )
    return preset_copy


def enrich_preset_entry(db_path: str, preset: Mapping[str, Any]) -> dict[str, Any]:
    history_rows = _load_recent_history_rows(db_path)
    active_source_policies = _load_active_source_policy_groups(db_path)
    return build_preset_entry(
        preset,
        history_rows=history_rows,
        active_source_policies=active_source_policies,
    )


def enrich_preset_entries(
    db_path: str, presets: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    history_rows = _load_recent_history_rows(db_path)
    active_source_policies = _load_active_source_policy_groups(db_path)
    return [
        build_preset_entry(
            preset,
            history_rows=history_rows,
            active_source_policies=active_source_policies,
        )
        for preset in presets
    ]
