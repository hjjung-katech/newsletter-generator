from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import newsletter.llm_factory as legacy_llm_factory
import newsletter_core.infrastructure.llm_factory_runtime as runtime_adapters


class _SecretValue:
    def __init__(self, value: str) -> None:
        self.value = value

    def get_secret_value(self) -> str:
        return self.value


class _FakeLogger:
    def __init__(self) -> None:
        self.warnings: list[str] = []
        self.infos: list[str] = []

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def info(self, message: str) -> None:
        self.infos.append(message)


def test_resolve_runtime_settings_logs_and_falls_back_on_loader_error() -> None:
    logger = _FakeLogger()

    def _broken_loader() -> Any:
        raise RuntimeError("boom")

    assert runtime_adapters.resolve_runtime_settings(_broken_loader, logger) is None
    assert any("중앙화된 설정 로드 실패" in message for message in logger.warnings)


def test_resolve_provider_api_key_prefers_settings_then_env_fallback() -> None:
    settings = SimpleNamespace(
        gemini_api_key=_SecretValue("settings-gemini-key"),
        openai_api_key=None,
        anthropic_api_key=None,
    )
    env = {
        "OPENAI_API_KEY": "env-openai-key",
    }

    assert (
        runtime_adapters.resolve_provider_api_key(
            "gemini",
            settings=settings,
            getenv=env.get,
        )
        == "settings-gemini-key"
    )
    assert (
        runtime_adapters.resolve_provider_api_key(
            "openai",
            settings=settings,
            getenv=env.get,
        )
        == "env-openai-key"
    )


def test_build_provider_model_params_applies_fast_mode_defaults() -> None:
    logger = _FakeLogger()
    settings = SimpleNamespace(
        llm_request_timeout=45,
        enable_fast_mode=True,
    )

    model_params = runtime_adapters.build_provider_model_params(
        "gemini",
        {
            "model": "gemini-1.5-pro",
            "temperature": 0.2,
        },
        settings=settings,
        logger=logger,
    )

    assert model_params["model"] == "gemini-1.5-flash"
    assert model_params["temperature"] == 0.2
    assert model_params["max_tokens"] == 4000
    assert model_params["timeout"] == 45
    assert "빠른 모드: Gemini Pro를 Flash로 변경" in logger.infos


def test_prepare_google_runtime_environment_mutates_only_when_called() -> None:
    logger = _FakeLogger()
    runtime_env = {
        "GOOGLE_APPLICATION_CREDENTIALS": "/tmp/missing-credentials.json",
        "GOOGLE_CLOUD_PROJECT": "sample-project",
        "CLOUDSDK_CONFIG": "/tmp/gcloud",
        "GCLOUD_PROJECT": "sample-gcloud-project",
    }

    runtime_adapters.prepare_google_runtime_environment(
        logger,
        environ=runtime_env,
        path_exists=lambda _path: False,
    )

    assert runtime_env["GOOGLE_APPLICATION_CREDENTIALS"] == ""
    assert runtime_env["GOOGLE_CLOUD_PROJECT"] == ""
    assert "CLOUDSDK_CONFIG" not in runtime_env
    assert "GCLOUD_PROJECT" not in runtime_env
    assert any(
        "GOOGLE_APPLICATION_CREDENTIALS이 존재하지 않는 파일" in msg for msg in logger.warnings
    )


def test_build_provider_callbacks_appends_cost_callback() -> None:
    logger = _FakeLogger()

    callbacks = runtime_adapters.build_provider_callbacks(
        "openai",
        ["base"],
        cost_callback_factory=lambda provider_name: f"cost:{provider_name}",
        exception_handler=lambda *_args, **_kwargs: None,
        logger=logger,
    )

    assert callbacks == ["base", "cost:openai"]


def test_build_provider_callbacks_handles_callback_factory_errors() -> None:
    logger = _FakeLogger()
    handled: dict[str, Any] = {}

    def _broken_factory(_provider_name: str) -> Any:
        raise RuntimeError("cost-failed")

    def _handle_exception(exc: Exception, message: str, *, log_level: int) -> None:
        handled["type"] = type(exc).__name__
        handled["message"] = message
        handled["log_level"] = log_level

    callbacks = runtime_adapters.build_provider_callbacks(
        "anthropic",
        ["base"],
        cost_callback_factory=_broken_factory,
        exception_handler=_handle_exception,
        logger=logger,
        fallback_path=True,
    )

    assert callbacks == ["base"]
    assert handled == {
        "type": "RuntimeError",
        "message": "비용 추적 추가 (anthropic)",
        "log_level": runtime_adapters.logging.INFO,
    }


def test_runtime_provider_creates_model_with_adapter_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = _FakeLogger()
    runtime_env = {
        "GOOGLE_APPLICATION_CREDENTIALS": "/tmp/real-credentials.json",
        "GOOGLE_CLOUD_PROJECT": "sample-project",
        "CLOUDSDK_CONFIG": "/tmp/gcloud",
        "GCLOUD_PROJECT": "sample-gcloud-project",
    }
    captured: dict[str, Any] = {}

    class _FakeChatModel:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(
        runtime_adapters,
        "_load_chat_class",
        lambda _provider_name: _FakeChatModel,
    )

    provider = runtime_adapters.RuntimeLLMProvider(
        "gemini",
        runtime_settings_loader=lambda: SimpleNamespace(
            gemini_api_key=_SecretValue("settings-gemini-key"),
            llm_request_timeout=90,
            enable_fast_mode=False,
        ),
        cost_callback_factory=lambda provider_name: f"cost:{provider_name}",
        exception_handler=lambda *_args, **_kwargs: None,
        logger=logger,
        environ=runtime_env,
        getenv=runtime_env.get,
        path_exists=lambda _path: True,
    )

    model = provider.create_model(
        {
            "provider": "gemini",
            "model": "gemini-1.5-pro",
            "temperature": 0.4,
        },
        ["base"],
    )

    assert isinstance(model, _FakeChatModel)
    assert captured == {
        "google_api_key": "settings-gemini-key",
        "model": "gemini-1.5-pro",
        "temperature": 0.4,
        "max_output_tokens": 4000,
        "timeout": 90,
        "callbacks": ["base", "cost:gemini"],
    }
    assert runtime_env["GOOGLE_APPLICATION_CREDENTIALS"] == ""
    assert runtime_env["GOOGLE_CLOUD_PROJECT"] == ""
    assert "CLOUDSDK_CONFIG" not in runtime_env
    assert "GCLOUD_PROJECT" not in runtime_env


def test_build_runtime_provider_registry_returns_supported_providers() -> None:
    registry = runtime_adapters.build_runtime_provider_registry(
        runtime_settings_loader=lambda: None,
        cost_callback_factory=lambda _provider_name: None,
        exception_handler=lambda *_args, **_kwargs: None,
        logger=_FakeLogger(),
    )

    assert set(registry) == {"gemini", "openai", "anthropic"}


def test_legacy_factory_build_callbacks_delegates_to_runtime_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _fake_build_provider_callbacks(
        provider_name: str,
        callbacks: list[Any] | None,
        **kwargs: Any,
    ) -> list[Any]:
        captured["provider_name"] = provider_name
        captured["callbacks"] = list(callbacks or [])
        captured["fallback_path"] = kwargs["fallback_path"]
        return ["from-runtime-helper"]

    monkeypatch.setattr(
        legacy_llm_factory,
        "build_provider_callbacks",
        _fake_build_provider_callbacks,
    )

    callbacks = legacy_llm_factory.LLMFactory()._build_callbacks(
        "openai",
        ["base"],
        fallback_path=True,
    )

    assert callbacks == ["from-runtime-helper"]
    assert captured == {
        "provider_name": "openai",
        "callbacks": ["base"],
        "fallback_path": True,
    }
