from __future__ import annotations

from typing import Any

import pytest

import newsletter.llm_factory as legacy_llm_factory
from newsletter_core.application.llm_factory import (
    ProviderSelection,
    build_provider_info,
    get_default_model,
    resolve_provider_selection,
    resolve_task_model_config,
)


def _sample_llm_config() -> dict[str, Any]:
    return {
        "default_provider": "gemini",
        "models": {
            "translation": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "temperature": 0.1,
                "max_retries": 1,
                "timeout": 30,
            },
            "html_generation": {
                "provider": "gemini",
                "model": "gemini-2.5-pro-preview-03-25",
                "temperature": 0.2,
                "max_retries": 3,
                "timeout": 180,
            },
        },
        "provider_models": {
            "gemini": {
                "fast": "gemini-1.5-flash-latest",
                "standard": "gemini-1.5-pro",
                "advanced": "gemini-2.5-pro-preview-03-25",
            },
            "openai": {
                "fast": "gpt-4o-mini",
                "standard": "gpt-4o",
                "advanced": "gpt-4o",
            },
            "anthropic": {
                "fast": "claude-3-haiku-20240307",
                "standard": "claude-3-sonnet-20240229",
                "advanced": "claude-3-5-sonnet-20241022",
            },
        },
    }


class _StubProvider:
    def __init__(self, available: bool = True) -> None:
        self.available = available
        self.created: list[tuple[dict[str, Any], list[Any]]] = []

    def is_available(self) -> bool:
        return self.available

    def create_model(
        self, model_config: dict[str, Any], callbacks: list[Any] | None = None
    ) -> dict[str, Any]:
        snapshot = dict(model_config)
        callback_list = list(callbacks or [])
        self.created.append((snapshot, callback_list))
        return {
            "provider": snapshot["provider"],
            "model": snapshot["model"],
            "callbacks": callback_list,
        }


class _PassthroughFallback:
    def __init__(
        self,
        primary_llm: Any,
        factory: legacy_llm_factory.LLMFactory,
        task: str,
        callbacks: list[Any] | None = None,
    ) -> None:
        self.primary_llm = primary_llm
        self.factory = factory
        self.task = task
        self.callbacks = list(callbacks or [])


def test_resolve_task_model_config_returns_explicit_config_copy() -> None:
    llm_config = _sample_llm_config()

    resolved = resolve_task_model_config(llm_config, "translation")

    assert resolved == llm_config["models"]["translation"]
    assert resolved is not llm_config["models"]["translation"]


def test_resolve_task_model_config_returns_default_task_fallback() -> None:
    resolved = resolve_task_model_config(_sample_llm_config(), "unknown-task")

    assert resolved == {
        "provider": "gemini",
        "model": "gemini-1.5-pro",
        "temperature": 0.3,
        "max_retries": 2,
        "timeout": 60,
    }


def test_resolve_provider_selection_keeps_requested_provider_when_available() -> None:
    selection = resolve_provider_selection(
        _sample_llm_config(),
        "translation",
        ("gemini", "openai", "anthropic"),
        ("openai", "anthropic"),
    )

    assert selection == ProviderSelection(
        requested_provider="openai",
        selected_provider="openai",
        model_config={
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.1,
            "max_retries": 1,
            "timeout": 30,
        },
        used_fallback=False,
    )


def test_resolve_provider_selection_falls_back_in_registered_order() -> None:
    selection = resolve_provider_selection(
        _sample_llm_config(),
        "translation",
        ("gemini", "openai", "anthropic"),
        ("anthropic",),
    )

    assert selection.requested_provider == "openai"
    assert selection.selected_provider == "anthropic"
    assert selection.used_fallback is True
    assert selection.model_config["provider"] == "anthropic"
    assert selection.model_config["model"] == "claude-3-sonnet-20240229"
    assert selection.model_config["temperature"] == 0.1


def test_resolve_provider_selection_raises_for_unknown_provider() -> None:
    llm_config = _sample_llm_config()
    llm_config["models"]["translation"]["provider"] = "unknown-provider"

    with pytest.raises(ValueError, match="Unknown provider: unknown-provider"):
        resolve_provider_selection(
            llm_config,
            "translation",
            ("gemini", "openai", "anthropic"),
            ("gemini",),
        )


def test_get_default_model_uses_legacy_defaults_for_missing_provider_entry() -> None:
    assert (
        get_default_model(_sample_llm_config(), "missing-provider") == "gemini-1.5-pro"
    )


def test_build_provider_info_shapes_availability_without_runtime_access() -> None:
    info = build_provider_info(
        _sample_llm_config(),
        ("gemini", "openai", "anthropic"),
        {"gemini": True, "openai": False, "anthropic": True},
    )

    assert info["gemini"]["available"] is True
    assert info["openai"]["available"] is False
    assert info["anthropic"]["models"]["advanced"] == "claude-3-5-sonnet-20241022"


def test_legacy_factory_delegates_selection_to_core_logic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection_calls: dict[str, Any] = {}
    openai_provider = _StubProvider(available=True)

    def _fake_selection(
        llm_config: dict[str, Any],
        task: str,
        provider_order: Any,
        available_providers: Any,
    ) -> ProviderSelection:
        selection_calls["llm_config"] = llm_config
        selection_calls["task"] = task
        selection_calls["provider_order"] = tuple(provider_order)
        selection_calls["available_providers"] = tuple(available_providers)
        return ProviderSelection(
            requested_provider="gemini",
            selected_provider="openai",
            model_config={
                "provider": "openai",
                "model": "gpt-4o",
                "temperature": 0.4,
            },
            used_fallback=True,
        )

    monkeypatch.setattr(
        legacy_llm_factory,
        "get_llm_config",
        lambda: _sample_llm_config(),
    )
    monkeypatch.setattr(
        legacy_llm_factory,
        "resolve_provider_selection",
        _fake_selection,
    )
    monkeypatch.setattr(
        legacy_llm_factory,
        "get_cost_callback_for_provider",
        lambda provider: f"cost:{provider}",
    )
    monkeypatch.setattr(
        legacy_llm_factory,
        "LLMWithFallback",
        _PassthroughFallback,
    )

    factory = legacy_llm_factory.LLMFactory()
    factory.providers = {
        "gemini": _StubProvider(available=False),
        "openai": openai_provider,
        "anthropic": _StubProvider(available=True),
    }

    result = factory.get_llm_for_task("translation", callbacks=["base"])

    assert selection_calls["task"] == "translation"
    assert selection_calls["provider_order"] == ("gemini", "openai", "anthropic")
    assert selection_calls["available_providers"] == ("openai", "anthropic")
    assert openai_provider.created == [
        (
            {"provider": "openai", "model": "gpt-4o", "temperature": 0.4},
            ["base", "cost:openai"],
        )
    ]
    assert result.task == "translation"
    assert result.primary_llm["provider"] == "openai"
    assert result.callbacks == ["base", "cost:openai"]
