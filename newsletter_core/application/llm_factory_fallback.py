"""Fallback orchestration helpers for legacy llm_factory compatibility."""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FallbackRuntimeConfig:
    max_retries: int
    retry_delay: float
    timeout: int | float
    test_mode: bool
    mock_responses: bool
    skip_real_api: bool


@dataclass(frozen=True)
class FallbackCandidate:
    provider_name: str
    model_config: dict[str, Any]
    attempt_message: str
    failure_prefix: str


_RETRYABLE_ERROR_KEYWORDS = (
    "529",
    "429",
    "quota",
    "rate limit",
    "too many requests",
    "overloaded",
    "timeout",
    "connection",
)
_FALLBACK_TRIGGER_ERROR_KEYWORDS = (
    "529",
    "429",
    "quota",
    "rate limit",
    "too many requests",
    "overloaded",
)
_GEMINI_STABLE_MODELS = ("gemini-1.5-pro", "gemini-1.5-flash")
_STABLE_FALLBACK_MODELS = {
    "openai": "gpt-4o",
    "anthropic": "claude-3-5-sonnet-20241022",
}


def resolve_fallback_runtime_config(
    runtime_settings_loader: Callable[[], Any | None] | None,
    *,
    getenv: Callable[[str], str | None] = os.getenv,
    modules: Mapping[str, Any] | None = None,
    logger: Any | None = None,
) -> FallbackRuntimeConfig:
    if runtime_settings_loader is not None:
        try:
            settings = runtime_settings_loader()
        except Exception as exc:
            if logger is not None:
                logger.warning(f"F-14 설정 로드 실패, 기본값 사용: {exc}")
        else:
            if settings is not None:
                max_retries = int(getattr(settings, "llm_max_retries", 3))
                retry_delay = float(getattr(settings, "llm_retry_delay", 1.0))
                timeout = getattr(settings, "llm_request_timeout", 60)
                test_mode = bool(getattr(settings, "test_mode", False))
                mock_response_attr = getattr(
                    settings,
                    "mock_api_responses",
                    False,
                )
                skip_real_api_attr = getattr(
                    settings,
                    "skip_real_api_calls",
                    False,
                )
                mock_responses = bool(mock_response_attr)
                skip_real_api = bool(skip_real_api_attr)
                return FallbackRuntimeConfig(
                    max_retries=max_retries,
                    retry_delay=retry_delay,
                    timeout=timeout,
                    test_mode=test_mode,
                    mock_responses=mock_responses,
                    skip_real_api=skip_real_api,
                )

    loaded_modules = modules if modules is not None else sys.modules
    test_mode = "pytest" in loaded_modules or getenv("TESTING") == "1"
    return FallbackRuntimeConfig(
        max_retries=3,
        retry_delay=1.0,
        timeout=60,
        test_mode=test_mode,
        mock_responses=test_mode,
        skip_real_api=test_mode,
    )


def is_retryable_error(exc: Exception) -> bool:
    return _matches_error_keywords(exc, _RETRYABLE_ERROR_KEYWORDS)


def is_fallback_trigger_error(exc: Exception) -> bool:
    return _matches_error_keywords(exc, _FALLBACK_TRIGGER_ERROR_KEYWORDS)


def build_fallback_candidates(
    *,
    primary_provider_name: str,
    primary_model: str,
    temperature: float,
    available_providers: Iterable[str],
    default_model_getter: Callable[[str], str],
) -> list[FallbackCandidate]:
    candidates: list[FallbackCandidate] = []

    if "gemini" in primary_provider_name.lower():
        for stable_model in _GEMINI_STABLE_MODELS:
            if stable_model == primary_model:
                continue
            attempt_message = f"안정적인 Gemini 모델을 시도합니다: {stable_model}"
            failure_prefix = f"안정적인 Gemini 모델 {stable_model} 생성에 실패했습니다"
            candidates.append(
                FallbackCandidate(
                    provider_name="gemini",
                    model_config={
                        "provider": "gemini",
                        "model": stable_model,
                        "temperature": temperature,
                        "max_retries": 2,
                        "timeout": 60,
                    },
                    attempt_message=attempt_message,
                    failure_prefix=failure_prefix,
                )
            )

    for provider_name in available_providers:
        if provider_name == "gemini":
            continue
        fallback_model = _STABLE_FALLBACK_MODELS.get(
            provider_name,
            default_model_getter(provider_name),
        )
        candidates.append(
            FallbackCandidate(
                provider_name=provider_name,
                model_config={
                    "provider": provider_name,
                    "model": fallback_model,
                    "temperature": temperature,
                    "max_retries": 2,
                    "timeout": 60,
                },
                attempt_message=(
                    f"다른 제공자를 시도합니다: {provider_name} (모델: {fallback_model})"
                ),
                failure_prefix=f"{provider_name}으로 대체 LLM 생성에 실패했습니다",
            )
        )

    return candidates


def create_fallback_model(
    *,
    primary_provider_name: str,
    primary_model: str,
    temperature: float,
    available_providers: Iterable[str],
    default_model_getter: Callable[[str], str],
    providers: Mapping[str, Any],
    callbacks: list[Any],
    callback_builder: Callable[..., list[Any]],
    logger: Any,
) -> Any | None:
    provider_label = f"{primary_provider_name} ({primary_model})"
    search_message = f"{provider_label}에 대한 대체 모델을 찾는 중입니다"
    logger.info(search_message)

    candidates = build_fallback_candidates(
        primary_provider_name=primary_provider_name,
        primary_model=primary_model,
        temperature=temperature,
        available_providers=available_providers,
        default_model_getter=default_model_getter,
    )

    for candidate in candidates:
        provider = providers.get(candidate.provider_name)
        if provider is None or not provider.is_available():
            continue

        try:
            logger.info(candidate.attempt_message)
            fallback_callbacks = callback_builder(
                candidate.provider_name,
                callbacks,
                fallback_path=True,
            )
            return provider.create_model(
                dict(candidate.model_config),
                fallback_callbacks,
            )
        except Exception as exc:
            logger.warning(f"{candidate.failure_prefix}: {exc}")

    logger.warning("대체 LLM을 생성할 수 없습니다")
    return None


def invoke_with_fallback(
    *,
    primary_llm: Any,
    input_data: Any,
    config: Any | None,
    kwargs: Mapping[str, Any],
    runtime_config: FallbackRuntimeConfig,
    fallback_loader: Callable[[], Any | None],
    logger: Any,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[Any, str]:
    max_retries = runtime_config.max_retries

    for attempt in range(max_retries + 1):
        try:
            logger.debug(f"LLM 호출 시도 {attempt + 1}/{max_retries + 1}")
            result = primary_llm.invoke(input_data, config=config, **kwargs)
            return result, "primary"
        except Exception as exc:
            if is_retryable_error(exc) and attempt < max_retries:
                wait_time = runtime_config.retry_delay * (2**attempt)
                logger.warning(f"LLM 호출 실패, {wait_time}초 후 재시도: {exc}")
                sleep(wait_time)
                continue

            fallback_llm = fallback_loader()
            if fallback_llm is not None:
                logger.warning(f"Primary LLM 실패, fallback 사용: {exc}")
                try:
                    result = fallback_llm.invoke(
                        input_data,
                        config=config,
                        **kwargs,
                    )
                    return result, "fallback"
                except Exception as fallback_error:
                    logger.error(f"Fallback LLM도 실패: {fallback_error}")

            logger.error(f"모든 LLM 호출 실패: {exc}")
            raise


def _matches_error_keywords(exc: Exception, keywords: tuple[str, ...]) -> bool:
    error_str = str(exc).lower()
    return any(keyword in error_str for keyword in keywords)


__all__ = [
    "FallbackCandidate",
    "FallbackRuntimeConfig",
    "build_fallback_candidates",
    "create_fallback_model",
    "invoke_with_fallback",
    "is_fallback_trigger_error",
    "is_retryable_error",
    "resolve_fallback_runtime_config",
]
