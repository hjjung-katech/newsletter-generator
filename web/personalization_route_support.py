"""Bounded visibility helpers for personalization-related web surfaces."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from newsletter_core.public.source_policies import normalize_source_pattern

DEFAULT_TEMPLATE_STYLE = "compact"
DEFAULT_PERIOD = 14
DEFAULT_EMAIL_COMPATIBLE = False


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _normalize_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value in {None, ""}:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _normalize_period(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return DEFAULT_PERIOD


def _normalize_archive_reference_ids(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()

    return tuple(str(item).strip() for item in value if str(item).strip())


def _normalize_source_patterns(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()

    normalized: list[str] = []
    for candidate in value:
        pattern = normalize_source_pattern(str(candidate or ""))
        if pattern:
            normalized.append(pattern)
    return tuple(normalized)


def _build_override_labels(
    *,
    template_style: str,
    email_compatible: bool,
    period: int,
    archive_reference_count: int,
    source_policy_override_count: int,
) -> list[str]:
    labels: list[str] = []
    if template_style != DEFAULT_TEMPLATE_STYLE:
        labels.append("템플릿 스타일")
    if email_compatible != DEFAULT_EMAIL_COMPATIBLE:
        labels.append("이메일 호환 모드")
    if period != DEFAULT_PERIOD:
        labels.append("기간")
    if archive_reference_count > 0:
        labels.append("아카이브 컨텍스트")
    if source_policy_override_count > 0:
        labels.append("소스 정책 오버라이드")
    return labels


def build_personalization_visibility(
    params: Mapping[str, Any] | None,
    *,
    source_policy_visibility: Mapping[str, Any] | None = None,
    latest_related_execution: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _mapping_or_empty(params)
    source_policy = _mapping_or_empty(source_policy_visibility)
    recent_execution = _mapping_or_empty(latest_related_execution)

    if not payload:
        return {
            "personalization_state": "empty",
            "status_label": "개인화 비어 있음",
            "status_message": "현재 표시할 개인화 설정이 없어 기본값 기준으로 해석됩니다.",
            "effective_template_style": DEFAULT_TEMPLATE_STYLE,
            "effective_period": DEFAULT_PERIOD,
            "email_compatible": DEFAULT_EMAIL_COMPATIBLE,
            "email_mode_label": "기본 모드",
            "override_count": 0,
            "override_labels": [],
            "has_archive_context": False,
            "archive_reference_count": 0,
            "source_policy_override_count": 0,
            "source_policy_link_state": str(
                source_policy.get("link_state")
                or source_policy.get("visibility_state")
                or "unknown"
            ),
            "source_policy_message": str(
                source_policy.get("message")
                or source_policy.get("status_message")
                or ""
            ),
            "has_recent_related_execution": bool(recent_execution.get("job_id")),
            "recent_usage_state": "recent"
            if recent_execution.get("job_id")
            else "empty",
            "recent_usage_label": "최근 연관 실행 있음"
            if recent_execution.get("job_id")
            else "연관 실행 없음",
            "recent_usage_timestamp": recent_execution.get("created_at"),
        }

    template_style = (
        str(payload.get("template_style", DEFAULT_TEMPLATE_STYLE) or "").strip()
        or DEFAULT_TEMPLATE_STYLE
    )
    period = _normalize_period(payload.get("period", DEFAULT_PERIOD))
    email_compatible = _normalize_bool(
        payload.get("email_compatible", DEFAULT_EMAIL_COMPATIBLE),
        default=DEFAULT_EMAIL_COMPATIBLE,
    )
    archive_reference_ids = _normalize_archive_reference_ids(
        payload.get("archive_reference_ids")
    )
    source_allowlist = _normalize_source_patterns(payload.get("source_allowlist"))
    source_blocklist = _normalize_source_patterns(payload.get("source_blocklist"))
    source_policy_override_count = len(source_allowlist) + len(source_blocklist)
    override_labels = _build_override_labels(
        template_style=template_style,
        email_compatible=email_compatible,
        period=period,
        archive_reference_count=len(archive_reference_ids),
        source_policy_override_count=source_policy_override_count,
    )
    override_count = len(override_labels)

    if override_count == 0:
        personalization_state = "default"
        status_label = "기본 개인화"
        status_message = "현재 개인화 설정은 기본값으로 유지됩니다."
    else:
        personalization_state = "overridden"
        status_label = "오버라이드 적용"
        status_message = f"기본값 대비 개인화 오버라이드 {override_count}개가 적용됩니다."

    source_policy_link_state = str(
        source_policy.get("link_state") or source_policy.get("visibility_state") or ""
    ).strip()
    source_policy_message = str(
        source_policy.get("message") or source_policy.get("status_message") or ""
    ).strip()

    return {
        "personalization_state": personalization_state,
        "status_label": status_label,
        "status_message": status_message,
        "effective_template_style": template_style,
        "effective_period": period,
        "email_compatible": email_compatible,
        "email_mode_label": "이메일 호환 모드" if email_compatible else "기본 모드",
        "override_count": override_count,
        "override_labels": override_labels,
        "has_archive_context": bool(archive_reference_ids),
        "archive_reference_count": len(archive_reference_ids),
        "source_policy_override_count": source_policy_override_count,
        "source_policy_link_state": source_policy_link_state or "unknown",
        "source_policy_message": source_policy_message,
        "has_recent_related_execution": bool(recent_execution.get("job_id")),
        "recent_usage_state": "recent" if recent_execution.get("job_id") else "empty",
        "recent_usage_label": "최근 연관 실행 있음"
        if recent_execution.get("job_id")
        else "연관 실행 없음",
        "recent_usage_timestamp": recent_execution.get("created_at"),
    }
