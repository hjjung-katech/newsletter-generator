"""Bounded visibility helpers for source policy web routes."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from newsletter_core.public.source_policies import normalize_source_pattern

try:
    from db_state import list_generation_presets
except ImportError:
    from web.db_state import list_generation_presets  # pragma: no cover

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


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _normalize_source_patterns(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()

    normalized: list[str] = []
    for candidate in value:
        pattern = normalize_source_pattern(str(candidate or ""))
        if pattern:
            normalized.append(pattern)
    return tuple(normalized)


def _load_recent_history_rows(
    db_path: str,
    *,
    limit: int = 200,
) -> list[dict[str, Any]]:
    try:
        import db_core as _db_core
    except ImportError:
        from web import db_core as _db_core  # pragma: no cover

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


def _matches_source_pattern(candidate: str, pattern: str) -> bool:
    if not candidate or not pattern:
        return False

    if "." in pattern:
        return candidate == pattern or candidate.endswith(f".{pattern}")

    return pattern in candidate


def _find_linked_presets(
    policy: Mapping[str, Any],
    presets: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    normalized_pattern = normalize_source_pattern(str(policy.get("pattern", "") or ""))
    if not normalized_pattern:
        return []

    linked_presets: list[dict[str, Any]] = []
    for preset in presets:
        params = _mapping_or_empty(preset.get("params"))
        normalized_domain = normalize_source_pattern(
            str(params.get("domain", "") or "")
        )
        if not normalized_domain:
            continue
        if not _matches_source_pattern(normalized_domain, normalized_pattern):
            continue
        linked_presets.append(
            {
                "id": preset.get("id"),
                "name": preset.get("name"),
                "is_default": bool(preset.get("is_default", False)),
                "domain": normalized_domain,
            }
        )
    return linked_presets


def find_latest_related_execution(
    policy: Mapping[str, Any],
    history_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    normalized_pattern = normalize_source_pattern(str(policy.get("pattern", "") or ""))
    policy_type = str(policy.get("policy_type", "") or "").strip().lower()
    if not normalized_pattern or policy_type not in {"allow", "block"}:
        return None

    lookup_key = "source_allowlist" if policy_type == "allow" else "source_blocklist"
    for history_row in history_rows:
        result_mapping = _mapping_or_empty(history_row.get("result"))
        input_params = _mapping_or_empty(result_mapping.get("input_params"))
        normalized_patterns = _normalize_source_patterns(input_params.get(lookup_key))
        if normalized_pattern not in normalized_patterns:
            continue
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
    policy: Mapping[str, Any],
    *,
    linked_presets: Sequence[Mapping[str, Any]] | None = None,
    latest_related_execution: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    linked_entries = list(linked_presets or [])
    linked_count = len(linked_entries)
    linked_default_count = sum(
        1 for preset in linked_entries if preset.get("is_default")
    )
    is_active = bool(policy.get("is_active", False))
    has_recent_execution = bool(latest_related_execution)
    pattern = str(policy.get("pattern", "") or "")
    policy_type = str(policy.get("policy_type", "") or "").strip().lower()

    if not is_active:
        visibility_state = "disabled"
        status_label = "비활성"
        status_message = "비활성 상태라 현재 실행에는 적용되지 않습니다."
    elif has_recent_execution:
        visibility_state = "applied"
        status_label = "최근 반영"
        status_message = "최근 실행에서 이 정책이 실제로 반영되었습니다."
    elif linked_count > 0:
        visibility_state = "enabled"
        status_label = "활성"
        status_message = f"연결된 프리셋 {linked_count}개에 대해 다음 실행 시 적용될 수 있습니다."
    elif pattern:
        visibility_state = "detached"
        status_label = "연결 없음"
        status_message = "활성 정책이지만 연결된 프리셋이나 최근 적용 이력이 없습니다."
    else:
        visibility_state = "unknown"
        status_label = "상태 미상"
        status_message = "정책 상태를 해석할 수 없습니다."

    return {
        "visibility_state": visibility_state,
        "status_label": status_label,
        "status_message": status_message,
        "policy_type_label": "Allow 정책" if policy_type == "allow" else "Block 정책",
        "linked_preset_count": linked_count,
        "linked_default_preset_count": linked_default_count,
        "linked_preset_names": [
            str(entry.get("name", "") or "")
            for entry in linked_entries
            if entry.get("name")
        ],
        "recent_usage_state": "recent" if has_recent_execution else "empty",
        "has_latest_related_execution": has_recent_execution,
    }


def build_preset_linkage_visibility(
    linked_presets: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    linked_entries = list(linked_presets or [])
    linked_count = len(linked_entries)
    linked_default_count = sum(
        1 for preset in linked_entries if preset.get("is_default")
    )

    if linked_count == 0:
        return {
            "link_state": "none",
            "message": "직접 연결된 도메인 프리셋이 없습니다.",
            "linked_preset_count": 0,
            "linked_default_preset_count": 0,
        }

    default_suffix = f", 기본 프리셋 {linked_default_count}개" if linked_default_count else ""
    return {
        "link_state": "matched",
        "message": f"연결된 도메인 프리셋 {linked_count}개{default_suffix}",
        "linked_preset_count": linked_count,
        "linked_default_preset_count": linked_default_count,
    }


def enrich_source_policy_entry(
    db_path: str,
    policy: Mapping[str, Any],
    *,
    presets: Sequence[Mapping[str, Any]] | None = None,
    history_rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    preset_entries = (
        list(presets) if presets is not None else list_generation_presets(db_path)
    )
    recent_history_rows = (
        list(history_rows)
        if history_rows is not None
        else _load_recent_history_rows(db_path)
    )
    linked_presets = _find_linked_presets(policy, preset_entries)
    latest_related_execution = find_latest_related_execution(
        policy, recent_history_rows
    )

    enriched = dict(policy)
    enriched["linked_presets"] = linked_presets
    enriched["latest_related_execution"] = latest_related_execution
    enriched["preset_linkage_visibility"] = build_preset_linkage_visibility(
        linked_presets
    )
    enriched["source_policy_visibility"] = build_source_policy_visibility(
        policy,
        linked_presets=linked_presets,
        latest_related_execution=latest_related_execution,
    )
    return enriched


def enrich_source_policy_entries(
    db_path: str,
    policies: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    presets = list_generation_presets(db_path)
    history_rows = _load_recent_history_rows(db_path)
    return [
        enrich_source_policy_entry(
            db_path,
            policy,
            presets=presets,
            history_rows=history_rows,
        )
        for policy in policies
    ]
