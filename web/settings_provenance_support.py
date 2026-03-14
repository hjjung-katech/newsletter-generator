"""Bounded helpers for effective settings provenance across web surfaces."""

from __future__ import annotations

from typing import Any, Mapping


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _resolve_source_policy_fields(
    source_policy_visibility: Mapping[str, Any],
    personalization_visibility: Mapping[str, Any],
) -> tuple[str, str, str]:
    source_policy_state = (
        str(
            source_policy_visibility.get("link_state")
            or source_policy_visibility.get("visibility_state")
            or personalization_visibility.get("source_policy_link_state")
            or "unknown"
        ).strip()
        or "unknown"
    )
    source_policy_label = (
        str(
            source_policy_visibility.get("status_label")
            or source_policy_visibility.get("policy_type_label")
            or personalization_visibility.get("source_policy_message")
            or "소스 정책 상태 미상"
        ).strip()
        or "소스 정책 상태 미상"
    )
    source_policy_message = str(
        source_policy_visibility.get("status_message")
        or source_policy_visibility.get("message")
        or personalization_visibility.get("source_policy_message")
        or ""
    ).strip()
    return source_policy_state, source_policy_label, source_policy_message


def _resolve_default_mode(
    personalization_visibility: Mapping[str, Any],
) -> tuple[str, str]:
    personalization_state = (
        str(
            personalization_visibility.get("personalization_state") or "unknown"
        ).strip()
        or "unknown"
    )
    if personalization_state == "overridden":
        return "overridden", "오버라이드 적용"
    if personalization_state in {"default", "empty"}:
        return "default", "기본값 유지"
    return "unknown", "기본값 여부 미상"


def _resolve_linkage_state(
    source_policy_state: str, preset_name: str
) -> tuple[str, str]:
    if source_policy_state in {"matched", "applied", "enabled"}:
        return "linked", "설정 연결됨"
    if source_policy_state in {"detached", "none"}:
        return "detached", "연결 일부 분리"
    if source_policy_state == "unavailable":
        return "unavailable", "연결 확인 불가"
    if preset_name:
        return "linked", "프리셋 기준 연결"
    return "unknown", "연결 상태 미상"


def _resolve_effective_state(
    *,
    preset_name: str,
    default_mode_state: str,
    linkage_state: str,
    has_recent_execution: bool,
) -> tuple[str, str]:
    if (
        not preset_name
        and default_mode_state == "unknown"
        and linkage_state
        in {
            "unknown",
            "unavailable",
        }
        and not has_recent_execution
    ):
        return "empty", "설정 컨텍스트 없음"
    if linkage_state == "detached":
        return "detached", "부분 분리된 설정"
    if default_mode_state == "overridden":
        return "overridden", "오버라이드된 설정 조합"
    if preset_name or linkage_state == "linked" or has_recent_execution:
        return "effective", "현재 설정 조합 확인됨"
    if default_mode_state == "default":
        return "default", "기본 설정 조합"
    return "unknown", "설정 provenance 미상"


def _append_diagnostic(
    reason_codes: list[str], details: list[str], code: str, detail: str
) -> None:
    if code not in reason_codes:
        reason_codes.append(code)
    if detail and detail not in details:
        details.append(detail)


def _build_provenance_diagnostics(
    *,
    effective_state: str,
    preset_name: str,
    personalization_state: str,
    has_personalization_context: bool,
    source_policy_state: str,
    linkage_state: str,
    linked_preset_count: int,
    has_recent_execution: bool,
    has_external_recent_execution: bool,
) -> dict[str, Any]:
    reason_codes: list[str] = []
    details: list[str] = []

    if effective_state == "empty":
        _append_diagnostic(
            reason_codes,
            details,
            "no_settings_context",
            "preset, source policy, personalization 중 provenance를 재구성할 수 있는 정보가 없어 empty로 표시됩니다.",
        )

    if has_external_recent_execution and (
        source_policy_state in {"none", "detached", "unknown", "unavailable"}
        or linkage_state in {"detached", "unknown", "unavailable"}
        or (linked_preset_count == 0 and not preset_name)
    ):
        _append_diagnostic(
            reason_codes,
            details,
            "recent_execution_not_reflected_by_current_settings",
            "최근 관련 실행은 있지만 현재 linkage가 달라 같은 설정 조합으로 바로 해석할 수 없습니다.",
        )

    if source_policy_state in {"detached", "none"} or linkage_state == "detached":
        if linked_preset_count == 0:
            _append_diagnostic(
                reason_codes,
                details,
                "source_policy_detached_from_presets",
                "현재 source policy와 직접 연결된 preset이 없어 detached로 표시됩니다.",
            )
        else:
            _append_diagnostic(
                reason_codes,
                details,
                "settings_linkage_partially_detached",
                f"연결된 preset {linked_preset_count}개만 확인되어 linkage가 부분적으로 분리된 상태로 보입니다.",
            )

    if has_personalization_context:
        if personalization_state == "overridden" and linkage_state != "linked":
            _append_diagnostic(
                reason_codes,
                details,
                "personalization_overridden_but_unlinked",
                "개인화 override는 있지만 preset/source policy linkage가 연결되지 않아 override가 현재 결과에 그대로 반영됐는지 즉시 확인하기 어렵습니다.",
            )
        elif personalization_state == "default":
            _append_diagnostic(
                reason_codes,
                details,
                "personalization_default_only",
                "개인화 override가 없어 default-only 상태로 해석됩니다.",
            )
        elif personalization_state == "empty":
            _append_diagnostic(
                reason_codes,
                details,
                "personalization_empty",
                "표시 가능한 개인화 설정이 없어 personalization이 empty로 보입니다.",
            )
        elif personalization_state == "unknown":
            _append_diagnostic(
                reason_codes,
                details,
                "personalization_unknown",
                "현재 payload만으로 개인화 적용 상태를 재구성할 수 없어 unknown으로 표시됩니다.",
            )

    if source_policy_state in {"unknown", "unavailable"}:
        _append_diagnostic(
            reason_codes,
            details,
            "source_policy_linkage_unresolved",
            "현재 정보만으로 source policy linkage를 재구성할 수 없어 unknown 성격으로 보입니다.",
        )

    if not has_recent_execution and effective_state in {
        "effective",
        "overridden",
        "default",
    }:
        _append_diagnostic(
            reason_codes,
            details,
            "no_recent_execution_reference",
            "현재 설정 조합을 직접 비교할 최근 실행이 없어 provenance를 실행 기준으로 교차검증할 수 없습니다.",
        )

    return {
        "primary_reason_code": reason_codes[0] if reason_codes else None,
        "reason_codes": reason_codes,
        "summary": details[0] if details else "",
        "details": details,
    }


def build_effective_settings_provenance(
    *,
    preset: Mapping[str, Any] | None = None,
    preset_visibility: Mapping[str, Any] | None = None,
    preset_linkage_visibility: Mapping[str, Any] | None = None,
    source_policy_visibility: Mapping[str, Any] | None = None,
    personalization_visibility: Mapping[str, Any] | None = None,
    latest_related_execution: Mapping[str, Any] | None = None,
    execution_visibility: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    preset_mapping = _mapping_or_empty(preset)
    preset_visibility_mapping = _mapping_or_empty(preset_visibility)
    preset_linkage_mapping = _mapping_or_empty(preset_linkage_visibility)
    source_policy_mapping = _mapping_or_empty(source_policy_visibility)
    personalization_mapping = _mapping_or_empty(personalization_visibility)
    latest_execution_mapping = _mapping_or_empty(latest_related_execution)
    execution_mapping = _mapping_or_empty(
        execution_visibility or latest_execution_mapping.get("execution_visibility")
    )

    preset_name = str(preset_mapping.get("name") or "").strip()
    preset_state = (
        str(
            preset_visibility_mapping.get("availability_state")
            or ("available" if preset_name else "unavailable")
        ).strip()
        or "unavailable"
    )
    preset_type_label = str(
        preset_visibility_mapping.get("preset_type_label") or ""
    ).strip()
    (
        source_policy_state,
        source_policy_label,
        source_policy_message,
    ) = _resolve_source_policy_fields(source_policy_mapping, personalization_mapping)
    default_mode_state, default_mode_label = _resolve_default_mode(
        personalization_mapping
    )
    linkage_state, linkage_label = _resolve_linkage_state(
        source_policy_state,
        preset_name,
    )
    has_recent_execution = bool(
        latest_execution_mapping.get("job_id")
        or execution_mapping.get("primary_timestamp")
    )
    has_external_recent_execution = bool(latest_execution_mapping.get("job_id"))
    effective_state, status_label = _resolve_effective_state(
        preset_name=preset_name,
        default_mode_state=default_mode_state,
        linkage_state=linkage_state,
        has_recent_execution=has_recent_execution,
    )

    linked_preset_count = int(
        source_policy_mapping.get("linked_preset_count")
        or preset_linkage_mapping.get("linked_preset_count")
        or 0
    )
    linked_default_preset_count = int(
        source_policy_mapping.get("linked_default_preset_count")
        or preset_linkage_mapping.get("linked_default_preset_count")
        or 0
    )

    summary_tokens: list[str] = []
    if preset_name:
        preset_token = preset_name
        if bool(preset_mapping.get("is_default")):
            preset_token += " (기본)"
        summary_tokens.append(f"프리셋: {preset_token}")
    elif linked_preset_count > 0:
        summary_tokens.append(f"프리셋 연결: {linked_preset_count}개")

    summary_tokens.append(
        f"개인화: {str(personalization_mapping.get('status_label') or '상태 미상')}"
    )
    summary_tokens.append(f"기본값/오버라이드: {default_mode_label}")
    summary_tokens.append(f"소스 정책: {source_policy_label}")
    if has_recent_execution:
        summary_tokens.append(
            f"최근 실행: {str(execution_mapping.get('status_label') or '상태 미상')}"
        )

    if effective_state == "detached":
        status_message = "현재 설정 조합의 일부가 연결에서 분리되어 있어 결과 해석에 주의가 필요합니다."
    elif effective_state == "overridden":
        status_message = "기본값 대비 오버라이드가 적용된 현재 설정 조합을 기준으로 결과를 해석할 수 있습니다."
    elif effective_state == "default":
        status_message = "현재 결과는 기본 설정 조합을 기준으로 해석됩니다."
    elif effective_state == "effective":
        status_message = "현재 결과를 만든 설정 조합이 확인되었습니다."
    elif effective_state == "empty":
        status_message = "표시 가능한 설정 provenance 정보가 아직 없습니다."
    else:
        status_message = "현재 설정 provenance를 완전히 해석할 수 없습니다."

    if source_policy_message:
        status_message = f"{status_message} {source_policy_message}".strip()

    diagnostics = _build_provenance_diagnostics(
        effective_state=effective_state,
        preset_name=preset_name,
        personalization_state=str(
            personalization_mapping.get("personalization_state") or "unknown"
        ),
        has_personalization_context=bool(personalization_mapping),
        source_policy_state=source_policy_state,
        linkage_state=linkage_state,
        linked_preset_count=linked_preset_count,
        has_recent_execution=has_recent_execution,
        has_external_recent_execution=has_external_recent_execution,
    )

    return {
        "effective_state": effective_state,
        "status_label": status_label,
        "status_message": status_message,
        "preset_name": preset_name or None,
        "preset_state": preset_state,
        "preset_type_label": preset_type_label or None,
        "preset_is_default": bool(preset_mapping.get("is_default", False)),
        "source_policy_state": source_policy_state,
        "source_policy_label": source_policy_label,
        "source_policy_message": source_policy_message,
        "personalization_state": str(
            personalization_mapping.get("personalization_state") or "unknown"
        ),
        "personalization_label": str(
            personalization_mapping.get("status_label") or "개인화 상태 미상"
        ),
        "default_mode_state": default_mode_state,
        "default_mode_label": default_mode_label,
        "linkage_state": linkage_state,
        "linkage_label": linkage_label,
        "linked_preset_count": linked_preset_count,
        "linked_default_preset_count": linked_default_preset_count,
        "has_recent_execution": has_recent_execution,
        "recent_execution_state": str(
            execution_mapping.get("status_category")
            or ("recent" if has_recent_execution else "empty")
        ),
        "recent_execution_label": str(
            execution_mapping.get("status_label")
            or ("최근 실행 있음" if has_recent_execution else "연관 실행 없음")
        ),
        "recent_execution_message": str(execution_mapping.get("status_message") or ""),
        "recent_execution_timestamp": execution_mapping.get("primary_timestamp")
        or latest_execution_mapping.get("created_at"),
        "summary_tokens": summary_tokens,
        "diagnostics": diagnostics,
    }
