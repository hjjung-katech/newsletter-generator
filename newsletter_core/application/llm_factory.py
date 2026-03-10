"""Pure decision helpers for the legacy llm_factory compatibility layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, cast

_DEFAULT_TASK_CONFIG = {
    "temperature": 0.3,
    "max_retries": 2,
    "timeout": 60,
}

_DEFAULT_PROVIDER_MODELS = {
    "gemini": "gemini-1.5-pro",
    "openai": "gpt-4o",
    "anthropic": "claude-3-sonnet-20240229",
}


@dataclass(frozen=True)
class ProviderSelection:
    """Resolved provider/model plan for a single task request."""

    requested_provider: Any
    selected_provider: str
    model_config: dict[str, Any]
    used_fallback: bool


def _as_mapping(value: Any) -> Mapping[Any, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def get_default_model(llm_config: Mapping[str, Any], provider_name: Any) -> str:
    """Return the standard model for a provider, preserving legacy defaults."""

    provider_models = _as_mapping(llm_config.get("provider_models", {}))
    models = _as_mapping(provider_models.get(provider_name, {}))
    default_model = _DEFAULT_PROVIDER_MODELS.get(provider_name, "gemini-1.5-pro")
    return cast(str, models.get("standard", default_model))


def resolve_task_model_config(
    llm_config: Mapping[str, Any],
    task: str,
) -> dict[str, Any]:
    """Resolve the task model config or the legacy default fallback config."""

    model_config = _as_mapping(_as_mapping(llm_config.get("models", {})).get(task))
    if model_config:
        return dict(model_config)

    provider_name = llm_config.get("default_provider", "gemini")
    default_config = dict(_DEFAULT_TASK_CONFIG)
    default_config.update(
        {
            "provider": provider_name,
            "model": get_default_model(llm_config, provider_name),
        }
    )
    return default_config


def resolve_provider_selection(
    llm_config: Mapping[str, Any],
    task: str,
    provider_order: Iterable[str],
    available_providers: Iterable[str],
) -> ProviderSelection:
    """Resolve the provider/model plan using the legacy fallback order."""

    ordered_providers = tuple(provider_order)
    available = set(available_providers)
    model_config = resolve_task_model_config(llm_config, task)
    requested_provider = model_config.get("provider", "gemini")

    if requested_provider not in ordered_providers:
        raise ValueError(f"Unknown provider: {requested_provider}")

    if requested_provider in available:
        return ProviderSelection(
            requested_provider=requested_provider,
            selected_provider=requested_provider,
            model_config=model_config,
            used_fallback=False,
        )

    for fallback_name in ordered_providers:
        if fallback_name not in available:
            continue
        fallback_config = dict(model_config)
        fallback_config["provider"] = fallback_name
        fallback_config["model"] = get_default_model(llm_config, fallback_name)
        return ProviderSelection(
            requested_provider=requested_provider,
            selected_provider=fallback_name,
            model_config=fallback_config,
            used_fallback=True,
        )

    raise ValueError("No LLM providers are available. Please check your API keys.")


def build_provider_info(
    llm_config: Mapping[str, Any],
    provider_order: Iterable[str],
    availability: Mapping[str, bool],
) -> dict[str, dict[str, Any]]:
    """Shape provider availability info without touching provider runtimes."""

    provider_models = _as_mapping(llm_config.get("provider_models", {}))
    info: dict[str, dict[str, Any]] = {}
    for name in provider_order:
        info[name] = {
            "available": bool(availability.get(name, False)),
            "models": dict(_as_mapping(provider_models.get(name, {}))),
        }
    return info


__all__ = [
    "ProviderSelection",
    "build_provider_info",
    "get_default_model",
    "resolve_provider_selection",
    "resolve_task_model_config",
]
