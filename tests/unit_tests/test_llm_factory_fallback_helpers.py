from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import newsletter.llm_factory as legacy_llm_factory
import newsletter_core.application.llm_factory_fallback as fallback_helpers


class _FakeLogger:
    def __init__(self) -> None:
        self.debugs: list[str] = []
        self.infos: list[str] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def debug(self, message: str) -> None:
        self.debugs.append(message)

    def info(self, message: str) -> None:
        self.infos.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def error(self, message: str) -> None:
        self.errors.append(message)


class _FakeLLM:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def invoke(
        self,
        input_data: Any,
        config: Any = None,
        **kwargs: Any,
    ) -> Any:
        self.calls.append(
            {
                "input_data": input_data,
                "config": config,
                "kwargs": dict(kwargs),
            }
        )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class _FakeProvider:
    def __init__(
        self,
        *,
        available: bool = True,
        create_result: Any | None = None,
        create_error: Exception | None = None,
    ) -> None:
        self.available = available
        self.create_result = create_result
        self.create_error = create_error
        self.created: list[tuple[dict[str, Any], list[Any]]] = []

    def is_available(self) -> bool:
        return self.available

    def create_model(
        self,
        model_config: dict[str, Any],
        callbacks: list[Any] | None = None,
    ) -> Any:
        snapshot = dict(model_config)
        callback_list = list(callbacks or [])
        self.created.append((snapshot, callback_list))
        if self.create_error is not None:
            raise self.create_error
        return self.create_result


class _LegacyFactoryStub:
    def __init__(self) -> None:
        self.providers = {
            "gemini": object(),
            "openai": object(),
            "anthropic": object(),
        }

    def get_available_providers(self) -> list[str]:
        return ["gemini", "openai", "anthropic"]

    def _get_default_model(self, provider_name: str) -> str:
        return f"default:{provider_name}"

    def _build_callbacks(
        self,
        provider_name: str,
        callbacks: list[Any] | None = None,
        *,
        fallback_path: bool = False,
    ) -> list[Any]:
        callback_list = list(callbacks or [])
        return callback_list + [f"cost:{provider_name}:{fallback_path}"]


def test_resolve_fallback_runtime_config_prefers_loaded_settings() -> None:
    logger = _FakeLogger()
    settings = SimpleNamespace(
        llm_max_retries=5,
        llm_retry_delay=2.5,
        llm_request_timeout=90,
        test_mode=True,
        mock_api_responses=False,
        skip_real_api_calls=True,
    )

    config = fallback_helpers.resolve_fallback_runtime_config(
        lambda: settings,
        logger=logger,
    )

    assert config == fallback_helpers.FallbackRuntimeConfig(
        max_retries=5,
        retry_delay=2.5,
        timeout=90,
        test_mode=True,
        mock_responses=False,
        skip_real_api=True,
    )
    warnings = logger.warnings
    assert warnings == []


def test_resolve_fallback_runtime_config_uses_test_env_defaults() -> None:
    config = fallback_helpers.resolve_fallback_runtime_config(
        lambda: None,
        getenv=lambda key: "1" if key == "TESTING" else None,
        modules={},
    )

    assert config == fallback_helpers.FallbackRuntimeConfig(
        max_retries=3,
        retry_delay=1.0,
        timeout=60,
        test_mode=True,
        mock_responses=True,
        skip_real_api=True,
    )


def test_build_fallback_candidates_preserve_gemini_order() -> None:
    def _default_model(provider_name: str) -> str:
        return f"default:{provider_name}"

    candidates = fallback_helpers.build_fallback_candidates(
        primary_provider_name="GeminiChatModel",
        primary_model="gemini-1.5-pro",
        temperature=0.4,
        available_providers=("gemini", "openai", "anthropic"),
        default_model_getter=_default_model,
    )

    assert [
        (candidate.provider_name, candidate.model_config["model"])
        for candidate in candidates
    ] == [
        ("gemini", "gemini-1.5-flash"),
        ("openai", "gpt-4o"),
        ("anthropic", "claude-3-5-sonnet-20241022"),
    ]
    candidate_temperatures = [
        candidate.model_config["temperature"] for candidate in candidates
    ]
    assert candidate_temperatures == [0.4, 0.4, 0.4]


def test_build_fallback_candidates_keep_legacy_type_matching() -> None:
    def _default_model(provider_name: str) -> str:
        return f"default:{provider_name}"

    candidates = fallback_helpers.build_fallback_candidates(
        primary_provider_name="ChatGoogleGenerativeAI",
        primary_model="gemini-1.5-pro",
        temperature=0.4,
        available_providers=("gemini", "openai", "anthropic"),
        default_model_getter=_default_model,
    )

    assert [
        (candidate.provider_name, candidate.model_config["model"])
        for candidate in candidates
    ] == [
        ("openai", "gpt-4o"),
        ("anthropic", "claude-3-5-sonnet-20241022"),
    ]


def test_create_fallback_model_uses_runtime_candidates() -> None:
    logger = _FakeLogger()
    gemini_provider = _FakeProvider(available=False)
    openai_provider = _FakeProvider(create_result="openai-fallback")
    callback_calls: list[tuple[str, list[Any], bool]] = []

    def _default_model(provider_name: str) -> str:
        return f"default:{provider_name}"

    def _build_callbacks(
        provider_name: str,
        callbacks: list[Any] | None = None,
        *,
        fallback_path: bool = False,
    ) -> list[Any]:
        callback_snapshot = list(callbacks or [])
        callback_record = (provider_name, callback_snapshot, fallback_path)
        callback_calls.append(callback_record)
        return callback_snapshot + [f"cost:{provider_name}"]

    fallback = fallback_helpers.create_fallback_model(
        primary_provider_name="ChatGoogleGenerativeAI",
        primary_model="gemini-1.5-pro",
        temperature=0.2,
        available_providers=("gemini", "openai", "anthropic"),
        default_model_getter=_default_model,
        providers={
            "gemini": gemini_provider,
            "openai": openai_provider,
            "anthropic": _FakeProvider(),
        },
        callbacks=["base"],
        callback_builder=_build_callbacks,
        logger=logger,
    )

    assert fallback == "openai-fallback"
    assert callback_calls == [("openai", ["base"], True)]
    assert openai_provider.created == [
        (
            {
                "provider": "openai",
                "model": "gpt-4o",
                "temperature": 0.2,
                "max_retries": 2,
                "timeout": 60,
            },
            ["base", "cost:openai"],
        )
    ]
    assert any("대체 모델을 찾는 중입니다" in message for message in logger.infos)


def test_invoke_with_fallback_retries_before_primary_success() -> None:
    logger = _FakeLogger()
    primary_llm = _FakeLLM([RuntimeError("429 rate limit"), "ok"])
    sleeps: list[float] = []

    result, last_used = fallback_helpers.invoke_with_fallback(
        primary_llm=primary_llm,
        input_data="payload",
        config={"trace": 1},
        kwargs={"extra": "value"},
        runtime_config=fallback_helpers.FallbackRuntimeConfig(
            max_retries=2,
            retry_delay=0.5,
            timeout=60,
            test_mode=False,
            mock_responses=False,
            skip_real_api=False,
        ),
        fallback_loader=lambda: None,
        logger=logger,
        sleep=sleeps.append,
    )

    assert result == "ok"
    assert last_used == "primary"
    assert sleeps == [0.5]
    assert len(primary_llm.calls) == 2


def test_invoke_with_fallback_uses_fallback_after_retries_exhausted() -> None:
    logger = _FakeLogger()
    primary_llm = _FakeLLM(
        [RuntimeError("429 rate limit"), RuntimeError("429 rate limit")]
    )
    fallback_llm = _FakeLLM(["fallback-result"])
    sleeps: list[float] = []

    result, last_used = fallback_helpers.invoke_with_fallback(
        primary_llm=primary_llm,
        input_data="payload",
        config=None,
        kwargs={},
        runtime_config=fallback_helpers.FallbackRuntimeConfig(
            max_retries=1,
            retry_delay=0.25,
            timeout=60,
            test_mode=False,
            mock_responses=False,
            skip_real_api=False,
        ),
        fallback_loader=lambda: fallback_llm,
        logger=logger,
        sleep=sleeps.append,
    )

    assert result == "fallback-result"
    assert last_used == "fallback"
    assert sleeps == [0.25]
    assert len(fallback_llm.calls) == 1


def test_is_fallback_trigger_error_matches_legacy_subset() -> None:
    retryable_error = RuntimeError("quota exceeded")
    assert fallback_helpers.is_fallback_trigger_error(retryable_error)
    assert not fallback_helpers.is_fallback_trigger_error(
        RuntimeError("connection reset by peer")
    )


def test_legacy_wrapper_delegates_runtime_config_to_core_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = fallback_helpers.FallbackRuntimeConfig(
        max_retries=4,
        retry_delay=1.5,
        timeout=75,
        test_mode=False,
        mock_responses=False,
        skip_real_api=False,
    )

    monkeypatch.setattr(
        legacy_llm_factory,
        "resolve_fallback_runtime_config",
        lambda *_args, **_kwargs: config,
    )

    wrapper = legacy_llm_factory.LLMWithFallback(
        _FakeLLM(["ok"]),
        _LegacyFactoryStub(),
        "translation",
        ["base"],
    )

    assert wrapper.runtime_config == config
    assert wrapper.max_retries == 4
    assert wrapper.retry_delay == 1.5
    assert wrapper.timeout == 75


def test_legacy_wrapper_delegates_fallback_creation_to_core_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    fallback_model = object()

    monkeypatch.setattr(
        legacy_llm_factory,
        "resolve_fallback_runtime_config",
        lambda *_args, **_kwargs: fallback_helpers.FallbackRuntimeConfig(
            max_retries=1,
            retry_delay=0.1,
            timeout=60,
            test_mode=False,
            mock_responses=False,
            skip_real_api=False,
        ),
    )

    def _fake_create_fallback_model(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return fallback_model

    monkeypatch.setattr(
        legacy_llm_factory,
        "create_fallback_model",
        _fake_create_fallback_model,
    )

    primary_llm = SimpleNamespace(model="gemini-1.5-pro", temperature=0.6)
    factory = _LegacyFactoryStub()
    wrapper = legacy_llm_factory.LLMWithFallback(
        primary_llm,
        factory,
        "translation",
        ["base"],
    )

    assert wrapper._load_fallback_llm() is fallback_model
    assert captured["primary_provider_name"] == "SimpleNamespace"
    assert captured["primary_model"] == "gemini-1.5-pro"
    assert captured["temperature"] == 0.6
    assert captured["available_providers"] == [
        "gemini",
        "openai",
        "anthropic",
    ]
    assert captured["providers"] == factory.providers
    assert captured["callbacks"] == ["base"]
    assert callable(captured["default_model_getter"])
    assert callable(captured["callback_builder"])


def test_legacy_wrapper_delegates_real_invoke_to_core_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    monkeypatch.setattr(
        legacy_llm_factory,
        "resolve_fallback_runtime_config",
        lambda *_args, **_kwargs: fallback_helpers.FallbackRuntimeConfig(
            max_retries=2,
            retry_delay=0.5,
            timeout=60,
            test_mode=False,
            mock_responses=False,
            skip_real_api=False,
        ),
    )

    def _fake_invoke_with_fallback(**kwargs: Any) -> tuple[str, str]:
        captured.update(kwargs)
        return "core-result", "fallback"

    monkeypatch.setattr(
        legacy_llm_factory,
        "invoke_with_fallback",
        _fake_invoke_with_fallback,
    )

    primary_llm = _FakeLLM(["unused"])
    wrapper = legacy_llm_factory.LLMWithFallback(
        primary_llm,
        _LegacyFactoryStub(),
        "translation",
        ["base"],
    )

    assert (
        wrapper._invoke_real_llm(
            "payload",
            {"trace": 1},
            test=True,
        )
        == "core-result"
    )
    assert wrapper.last_used == "fallback"
    assert captured["primary_llm"] is primary_llm
    assert captured["input_data"] == "payload"
    assert captured["config"] == {"trace": 1}
    assert captured["kwargs"] == {"test": True}
    assert captured["fallback_loader"] == wrapper._load_fallback_llm
