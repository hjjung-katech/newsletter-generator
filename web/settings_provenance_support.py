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


def _append_field_explanation(
    field_explanations: list[dict[str, Any]],
    *,
    axis: str,
    axis_label: str,
    field: str,
    field_label: str,
    expected_value: Any,
    current_value: Any,
    expected_label: str,
    current_label: str,
    summary: str,
    detail: str,
) -> None:
    explanation = {
        "axis": axis,
        "axis_label": axis_label,
        "field": field,
        "field_label": field_label,
        "expected_value": expected_value,
        "current_value": current_value,
        "expected_label": expected_label,
        "current_label": current_label,
        "summary": summary,
        "detail": detail,
    }
    if explanation not in field_explanations:
        field_explanations.append(explanation)


def _build_field_summary(field_explanations: list[dict[str, Any]]) -> str:
    summaries = [
        str(explanation.get("summary") or "").strip()
        for explanation in field_explanations
    ]
    unique_summaries = [summary for summary in summaries if summary]
    return " · ".join(unique_summaries[:2])


def _append_lineage_step(
    lineage_steps: list[dict[str, Any]],
    *,
    axis: str,
    axis_label: str,
    source_type: str,
    source_label: str,
    state: str,
    status_label: str,
    summary: str,
    detail: str,
    reference_timestamp: Any = None,
) -> None:
    step = {
        "axis": axis,
        "axis_label": axis_label,
        "source_type": source_type,
        "source_label": source_label,
        "state": state,
        "status_label": status_label,
        "summary": summary,
        "detail": detail,
        "reference_timestamp": reference_timestamp,
    }
    if step not in lineage_steps:
        lineage_steps.append(step)


def _build_lineage_summary(lineage_steps: list[dict[str, Any]]) -> str:
    summaries = [str(step.get("summary") or "").strip() for step in lineage_steps]
    return " -> ".join(summary for summary in summaries if summary)


def _build_effective_settings_lineage(
    *,
    effective_state: str,
    preset_name: str,
    preset_is_default: bool,
    preset_state: str,
    preset_type_label: str,
    source_policy_state: str,
    source_policy_label: str,
    source_policy_message: str,
    personalization_state: str,
    personalization_label: str,
    personalization_status_message: str,
    default_mode_label: str,
    linkage_state: str,
    linkage_label: str,
    linked_preset_count: int,
    linked_default_preset_count: int,
    has_personalization_context: bool,
    has_recent_execution: bool,
    recent_execution_label: str,
    recent_execution_message: str,
    recent_execution_timestamp: Any,
    override_count: int,
    override_labels: list[str],
) -> dict[str, Any]:
    lineage_steps: list[dict[str, Any]] = []

    if preset_name:
        preset_display_name = (
            f"{preset_name} (기본)" if preset_is_default else preset_name
        )
        preset_detail_tokens = []
        if preset_type_label:
            preset_detail_tokens.append(preset_type_label)
        if preset_state and preset_state != "available":
            preset_detail_tokens.append(f"상태 {preset_state}")
        preset_detail_tokens.append("현재 effective settings의 시작점")
        _append_lineage_step(
            lineage_steps,
            axis="preset",
            axis_label="프리셋",
            source_type="current_preset",
            source_label="현재 프리셋",
            state=preset_state,
            status_label=preset_display_name,
            summary=f"프리셋 {preset_display_name}",
            detail=" · ".join(preset_detail_tokens),
        )
    elif linked_preset_count > 0:
        _append_lineage_step(
            lineage_steps,
            axis="preset",
            axis_label="프리셋",
            source_type="linked_preset_reference",
            source_label="연결된 프리셋",
            state=linkage_state,
            status_label=f"연결 프리셋 {linked_preset_count}개",
            summary=f"프리셋 연결 {linked_preset_count}개",
            detail=(
                f"직접 선택된 preset은 없지만 연결된 preset {linked_preset_count}개"
                f"(기본 {linked_default_preset_count}개)가 provenance reference로 확인됩니다."
            ),
        )

    if (
        source_policy_label
        or source_policy_state != "unknown"
        or source_policy_message
        or linkage_state != "unknown"
    ):
        source_policy_detail = source_policy_message or (
            f"{linkage_label} · 연결된 preset {linked_preset_count}개"
        )
        _append_lineage_step(
            lineage_steps,
            axis="source_policy",
            axis_label="소스 정책",
            source_type="effective_source_policy",
            source_label="연결된 소스 정책",
            state=source_policy_state,
            status_label=source_policy_label,
            summary=f"소스 정책 {source_policy_label}",
            detail=source_policy_detail,
        )

    if has_personalization_context or personalization_state != "unknown":
        if override_count > 0:
            override_summary = f"override {override_count}개"
        elif personalization_state == "overridden":
            override_summary = "override 정보 있음"
        else:
            override_summary = "override 없음"
        if override_labels:
            override_summary += f" ({', '.join(override_labels)})"
        personalization_detail = personalization_status_message or (
            f"{default_mode_label} · {override_summary}"
        )
        _append_lineage_step(
            lineage_steps,
            axis="personalization",
            axis_label="개인화",
            source_type="effective_personalization",
            source_label="현재 개인화",
            state=personalization_state,
            status_label=personalization_label,
            summary=f"개인화 {personalization_label}",
            detail=personalization_detail,
        )

    if has_recent_execution:
        recent_execution_detail = recent_execution_message or (
            "가장 가까운 관련 실행 reference가 현재 settings lineage에 연결됩니다."
        )
        _append_lineage_step(
            lineage_steps,
            axis="recent_execution",
            axis_label="최근 실행",
            source_type="recent_execution_reference",
            source_label="최근 관련 실행",
            state="recent",
            status_label=recent_execution_label,
            summary=f"최근 실행 {recent_execution_label}",
            detail=recent_execution_detail,
            reference_timestamp=recent_execution_timestamp,
        )
    elif effective_state in {"effective", "overridden", "default", "detached"}:
        _append_lineage_step(
            lineage_steps,
            axis="recent_execution",
            axis_label="최근 실행",
            source_type="recent_execution_reference",
            source_label="최근 관련 실행",
            state="empty",
            status_label="연관 실행 없음",
            summary="최근 실행 연관 실행 없음",
            detail="현재 lineage는 최근 실행 reference 없이 current settings 기준으로만 재구성됩니다.",
            reference_timestamp=recent_execution_timestamp,
        )

    return {
        "summary": _build_lineage_summary(lineage_steps),
        "steps": lineage_steps,
    }


def _build_provenance_diagnostics(
    *,
    effective_state: str,
    preset_name: str,
    personalization_state: str,
    has_personalization_context: bool,
    source_policy_state: str,
    source_policy_label: str,
    linkage_state: str,
    linkage_label: str,
    linked_preset_count: int,
    linked_default_preset_count: int,
    has_recent_execution: bool,
    has_external_recent_execution: bool,
    override_count: int,
    override_labels: list[str],
) -> dict[str, Any]:
    reason_codes: list[str] = []
    details: list[str] = []
    field_explanations: list[dict[str, Any]] = []

    if effective_state == "empty":
        _append_diagnostic(
            reason_codes,
            details,
            "no_settings_context",
            "preset, source policy, personalization 중 provenance를 재구성할 수 있는 정보가 없어 empty로 표시됩니다.",
        )
        _append_field_explanation(
            field_explanations,
            axis="provenance",
            axis_label="설정 provenance",
            field="settings_context",
            field_label="설정 컨텍스트",
            expected_value="available",
            current_value="missing",
            expected_label="재구성 가능한 설정 컨텍스트",
            current_label="재구성 가능한 컨텍스트 없음",
            summary="설정 provenance 축에서 사용할 컨텍스트가 없습니다.",
            detail="preset, source policy, personalization 중 provenance를 재구성할 수 있는 입력이 없어 empty로 표시됩니다.",
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
        _append_field_explanation(
            field_explanations,
            axis="recent_execution",
            axis_label="최근 실행",
            field="settings_alignment",
            field_label="현재 설정 정합성",
            expected_value="aligned",
            current_value="mismatched",
            expected_label="최근 실행과 현재 설정이 같은 조합",
            current_label=f"최근 실행 있음 + 현재 linkage {linkage_label}",
            summary="최근 실행 축에서 현재 설정과 최근 실행의 정합성이 맞지 않습니다.",
            detail=(
                "최근 관련 실행은 있지만 현재 source policy/preset linkage가 "
                f"'{source_policy_label}' 상태라 같은 설정 조합으로 바로 해석할 수 없습니다."
            ),
        )

    if source_policy_state in {"detached", "none"} or linkage_state == "detached":
        if linked_preset_count == 0:
            _append_diagnostic(
                reason_codes,
                details,
                "source_policy_detached_from_presets",
                "현재 source policy와 직접 연결된 preset이 없어 detached로 표시됩니다.",
            )
            _append_field_explanation(
                field_explanations,
                axis="preset_linkage",
                axis_label="프리셋 연결",
                field="linked_preset_count",
                field_label="연결된 프리셋 수",
                expected_value=">=1",
                current_value=linked_preset_count,
                expected_label="연결된 preset 1개 이상",
                current_label=f"연결된 preset {linked_preset_count}개",
                summary="프리셋 연결 축에서 source policy와 연결된 preset이 없습니다.",
                detail="현재 source policy와 직접 연결된 preset이 0개라 detached로 표시됩니다.",
            )
        else:
            _append_diagnostic(
                reason_codes,
                details,
                "settings_linkage_partially_detached",
                f"연결된 preset {linked_preset_count}개만 확인되어 linkage가 부분적으로 분리된 상태로 보입니다.",
            )
            _append_field_explanation(
                field_explanations,
                axis="preset_linkage",
                axis_label="프리셋 연결",
                field="linked_default_preset_count",
                field_label="기본 프리셋 연결 수",
                expected_value="fully_linked",
                current_value=linked_default_preset_count,
                expected_label="기대한 preset/source policy 연결 유지",
                current_label=f"기본 프리셋 연결 {linked_default_preset_count}개",
                summary="프리셋 연결 축에서 일부 linkage만 남아 있습니다.",
                detail=(
                    f"연결된 preset은 {linked_preset_count}개지만 기본 프리셋 연결은 "
                    f"{linked_default_preset_count}개만 확인되어 부분 분리로 보입니다."
                ),
            )

    if has_personalization_context:
        if personalization_state == "overridden" and linkage_state != "linked":
            _append_diagnostic(
                reason_codes,
                details,
                "personalization_overridden_but_unlinked",
                "개인화 override는 있지만 preset/source policy linkage가 연결되지 않아 override가 현재 결과에 그대로 반영됐는지 즉시 확인하기 어렵습니다.",
            )
            override_label_summary = (
                f" ({', '.join(override_labels)})" if override_labels else ""
            )
            _append_field_explanation(
                field_explanations,
                axis="personalization",
                axis_label="개인화",
                field="source_policy_link_state",
                field_label="개인화 연결 상태",
                expected_value="linked",
                current_value=linkage_state,
                expected_label="override가 연결된 상태로 반영됨",
                current_label=linkage_label,
                summary="개인화 축에서 override는 있으나 연결 상태가 linked가 아닙니다.",
                detail=(
                    f"override {override_count}개{override_label_summary}가 있지만 "
                    f"현재 linkage는 '{linkage_label}' 이어서 현재 결과 반영 여부를 즉시 확정하기 어렵습니다."
                ),
            )
        elif personalization_state == "default":
            _append_diagnostic(
                reason_codes,
                details,
                "personalization_default_only",
                "개인화 override가 없어 default-only 상태로 해석됩니다.",
            )
            _append_field_explanation(
                field_explanations,
                axis="personalization",
                axis_label="개인화",
                field="override_count",
                field_label="개인화 오버라이드 수",
                expected_value=">=1",
                current_value=override_count,
                expected_label="오버라이드 1개 이상",
                current_label=f"오버라이드 {override_count}개",
                summary="개인화 축에서 override가 없어 default-only로 보입니다.",
                detail="개인화 override 수가 0개라 기본값만 유지되는 상태로 해석됩니다.",
            )
        elif personalization_state == "empty":
            _append_diagnostic(
                reason_codes,
                details,
                "personalization_empty",
                "표시 가능한 개인화 설정이 없어 personalization이 empty로 보입니다.",
            )
            _append_field_explanation(
                field_explanations,
                axis="personalization",
                axis_label="개인화",
                field="personalization_state",
                field_label="개인화 상태",
                expected_value="default_or_overridden",
                current_value=personalization_state,
                expected_label="기본값 또는 오버라이드 상태",
                current_label="empty",
                summary="개인화 축에서 표시 가능한 설정이 비어 있습니다.",
                detail="personalization payload에 표시 가능한 설정이 없어 empty로 보입니다.",
            )
        elif personalization_state == "unknown":
            _append_diagnostic(
                reason_codes,
                details,
                "personalization_unknown",
                "현재 payload만으로 개인화 적용 상태를 재구성할 수 없어 unknown으로 표시됩니다.",
            )
            _append_field_explanation(
                field_explanations,
                axis="personalization",
                axis_label="개인화",
                field="personalization_state",
                field_label="개인화 상태",
                expected_value="default_or_overridden",
                current_value=personalization_state,
                expected_label="기본값 또는 오버라이드 상태",
                current_label="unknown",
                summary="개인화 축에서 적용 상태를 재구성할 수 없습니다.",
                detail="현재 payload만으로 개인화가 default인지 overridden인지 결정할 수 없어 unknown으로 보입니다.",
            )

    if source_policy_state in {"unknown", "unavailable"}:
        _append_diagnostic(
            reason_codes,
            details,
            "source_policy_linkage_unresolved",
            "현재 정보만으로 source policy linkage를 재구성할 수 없어 unknown 성격으로 보입니다.",
        )
        _append_field_explanation(
            field_explanations,
            axis="source_policy",
            axis_label="소스 정책",
            field="source_policy_state",
            field_label="소스 정책 연결 상태",
            expected_value="resolved",
            current_value=source_policy_state,
            expected_label="재구성 가능한 linkage",
            current_label=source_policy_label,
            summary="소스 정책 축에서 linkage를 확정할 수 없습니다.",
            detail="현재 payload만으로 source policy linkage를 resolved 상태로 재구성할 수 없어 unknown 성격으로 표시됩니다.",
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
        _append_field_explanation(
            field_explanations,
            axis="recent_execution",
            axis_label="최근 실행",
            field="recent_execution_reference",
            field_label="최근 실행 참조",
            expected_value="present",
            current_value="missing",
            expected_label="최근 실행 참조 있음",
            current_label="최근 실행 참조 없음",
            summary="최근 실행 축에서 현재 설정과 비교할 참조가 없습니다.",
            detail="현재 설정 조합을 직접 비교할 최근 실행 reference가 없어 실행 기준 교차검증이 비어 있습니다.",
        )

    return {
        "primary_reason_code": reason_codes[0] if reason_codes else None,
        "reason_codes": reason_codes,
        "summary": details[0] if details else "",
        "details": details,
        "field_summary": _build_field_summary(field_explanations),
        "field_explanations": field_explanations,
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
        source_policy_label=source_policy_label,
        linkage_state=linkage_state,
        linkage_label=linkage_label,
        linked_preset_count=linked_preset_count,
        linked_default_preset_count=linked_default_preset_count,
        has_recent_execution=has_recent_execution,
        has_external_recent_execution=has_external_recent_execution,
        override_count=int(personalization_mapping.get("override_count") or 0),
        override_labels=[
            str(label).strip()
            for label in personalization_mapping.get("override_labels") or []
            if str(label).strip()
        ],
    )
    lineage = _build_effective_settings_lineage(
        effective_state=effective_state,
        preset_name=preset_name,
        preset_is_default=bool(preset_mapping.get("is_default", False)),
        preset_state=preset_state,
        preset_type_label=preset_type_label,
        source_policy_state=source_policy_state,
        source_policy_label=source_policy_label,
        source_policy_message=source_policy_message,
        personalization_state=str(
            personalization_mapping.get("personalization_state") or "unknown"
        ),
        personalization_label=str(
            personalization_mapping.get("status_label") or "개인화 상태 미상"
        ),
        personalization_status_message=str(
            personalization_mapping.get("status_message") or ""
        ),
        default_mode_label=default_mode_label,
        linkage_state=linkage_state,
        linkage_label=linkage_label,
        linked_preset_count=linked_preset_count,
        linked_default_preset_count=linked_default_preset_count,
        has_personalization_context=bool(personalization_mapping),
        has_recent_execution=has_recent_execution,
        recent_execution_label=str(
            execution_mapping.get("status_label")
            or ("최근 실행 있음" if has_recent_execution else "연관 실행 없음")
        ),
        recent_execution_message=str(execution_mapping.get("status_message") or ""),
        recent_execution_timestamp=execution_mapping.get("primary_timestamp")
        or latest_execution_mapping.get("created_at"),
        override_count=int(personalization_mapping.get("override_count") or 0),
        override_labels=[
            str(label).strip()
            for label in personalization_mapping.get("override_labels") or []
            if str(label).strip()
        ],
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
        "lineage": lineage,
        "diagnostics": diagnostics,
    }
