"""Runtime adapter helpers for the legacy llm_factory compatibility layer."""

from __future__ import annotations

import importlib
import logging
import os
from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderRuntimeSpec:
    settings_attr: str
    env_keys: tuple[str, ...]
    import_module: str
    class_name: str
    missing_package_message: str
    missing_api_key_message: str
    default_model: str
    default_temperature: float
    api_key_argument: str
    max_tokens_argument: str
    fast_mode_match: str | None = None
    fast_mode_replacement: str | None = None
    fast_mode_message: str | None = None


_PROVIDER_SPECS: dict[str, ProviderRuntimeSpec] = {
    "gemini": ProviderRuntimeSpec(
        settings_attr="gemini_api_key",
        env_keys=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        import_module="langchain_google_genai",
        class_name="ChatGoogleGenerativeAI",
        missing_package_message="langchain_google_genai 패키지가 설치되지 않았습니다",
        missing_api_key_message="GEMINI_API_KEY 환경변수가 설정되지 않았습니다",
        default_model="gemini-1.5-pro",
        default_temperature=0.3,
        api_key_argument="google_api_key",
        max_tokens_argument="max_output_tokens",
        fast_mode_match="gemini-1.5-pro",
        fast_mode_replacement="gemini-1.5-flash",
        fast_mode_message="빠른 모드: Gemini Pro를 Flash로 변경",
    ),
    "openai": ProviderRuntimeSpec(
        settings_attr="openai_api_key",
        env_keys=("OPENAI_API_KEY",),
        import_module="langchain_openai",
        class_name="ChatOpenAI",
        missing_package_message="langchain_openai 패키지가 설치되지 않았습니다",
        missing_api_key_message="OPENAI_API_KEY 환경변수가 설정되지 않았습니다",
        default_model="gpt-4o-mini",
        default_temperature=0.3,
        api_key_argument="api_key",
        max_tokens_argument="max_tokens",
        fast_mode_match="gpt-4",
        fast_mode_replacement="gpt-3.5-turbo",
        fast_mode_message="빠른 모드: GPT-4를 GPT-3.5-turbo로 변경",
    ),
    "anthropic": ProviderRuntimeSpec(
        settings_attr="anthropic_api_key",
        env_keys=("ANTHROPIC_API_KEY",),
        import_module="langchain_anthropic",
        class_name="ChatAnthropic",
        missing_package_message="langchain_anthropic 패키지가 설치되지 않았습니다",
        missing_api_key_message="ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다",
        default_model="claude-3-haiku-20240307",
        default_temperature=0.1,
        api_key_argument="anthropic_api_key",
        max_tokens_argument="max_tokens",
        fast_mode_match="claude-3-opus",
        fast_mode_replacement="claude-3-haiku-20240307",
        fast_mode_message="빠른 모드: Claude Opus를 Haiku로 변경",
    ),
}


def _get_provider_spec(provider_name: str) -> ProviderRuntimeSpec:
    try:
        return _PROVIDER_SPECS[provider_name]
    except KeyError as exc:
        raise ValueError(f"Unknown provider: {provider_name}") from exc


def resolve_runtime_settings(
    runtime_settings_loader: Callable[[], Any | None] | None,
    logger: Any,
) -> Any | None:
    if runtime_settings_loader is None:
        return None
    try:
        return runtime_settings_loader()
    except Exception as exc:
        logger.warning(f"중앙화된 설정 로드 실패, 환경변수 fallback 사용: {exc}")
        return None


def _get_secret_value(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "get_secret_value"):
        secret_value = value.get_secret_value()
        return str(secret_value) if secret_value is not None else None
    return str(value)


def resolve_provider_api_key(
    provider_name: str,
    *,
    settings: Any | None = None,
    getenv: Callable[[str], str | None] = os.getenv,
) -> str | None:
    spec = _get_provider_spec(provider_name)

    if settings is not None:
        secret_value = _get_secret_value(getattr(settings, spec.settings_attr, None))
        if secret_value:
            return secret_value

    for env_key in spec.env_keys:
        env_value = getenv(env_key)
        if env_value:
            return env_value
    return None


def prepare_google_runtime_environment(
    logger: Any,
    *,
    environ: MutableMapping[str, str] | None = None,
    path_exists: Callable[[str], bool] = os.path.exists,
) -> None:
    runtime_env = environ if environ is not None else os.environ
    google_creds_path = runtime_env.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if google_creds_path and not path_exists(google_creds_path):
        logger.warning(
            "GOOGLE_APPLICATION_CREDENTIALS이 존재하지 않는 파일을 가리킵니다: " f"{google_creds_path}"
        )
        logger.info("Google Cloud 인증을 비활성화하고 API 키만 사용합니다.")

    runtime_env["GOOGLE_APPLICATION_CREDENTIALS"] = ""
    runtime_env["GOOGLE_CLOUD_PROJECT"] = ""
    runtime_env.pop("CLOUDSDK_CONFIG", None)
    runtime_env.pop("GCLOUD_PROJECT", None)


def build_provider_model_params(
    provider_name: str,
    model_config: Mapping[str, Any],
    *,
    settings: Any | None = None,
    logger: Any,
) -> dict[str, Any]:
    spec = _get_provider_spec(provider_name)
    model_params = dict(model_config)

    if settings is not None:
        model_params.setdefault(
            "timeout",
            getattr(settings, "llm_request_timeout", 120),
        )
        if getattr(settings, "enable_fast_mode", False):
            fast_mode_match = spec.fast_mode_match
            model_name = str(model_params.get("model", ""))
            if (
                fast_mode_match
                and fast_mode_match in model_name
                and spec.fast_mode_replacement is not None
            ):
                model_params["model"] = spec.fast_mode_replacement
                if spec.fast_mode_message:
                    logger.info(spec.fast_mode_message)
    else:
        model_params.setdefault("timeout", 120)

    model_params.setdefault("temperature", spec.default_temperature)
    model_params.setdefault("max_tokens", 4000)
    model_params.setdefault("model", spec.default_model)
    return model_params


def build_provider_callbacks(
    provider_name: str,
    callbacks: list[Any] | None,
    *,
    cost_callback_factory: Callable[[str], Any],
    exception_handler: Callable[..., Any],
    logger: Any,
    fallback_path: bool = False,
    error_message: str | None = None,
) -> list[Any]:
    final_callbacks = list(callbacks) if callbacks else []
    try:
        cost_callback = cost_callback_factory(provider_name)
        if cost_callback is not None:
            final_callbacks.append(cost_callback)
    except Exception as exc:
        message = error_message
        if message is None:
            message = (
                f"비용 추적 추가 ({provider_name})"
                if fallback_path
                else f"Warning: Failed to add cost tracking for {provider_name}"
            )
        exception_handler(exc, message, log_level=logging.INFO)
    return final_callbacks


def _load_chat_class(provider_name: str) -> Any:
    spec = _get_provider_spec(provider_name)
    try:
        module = importlib.import_module(spec.import_module)
    except ImportError as exc:
        raise ImportError(spec.missing_package_message) from exc

    try:
        return getattr(module, spec.class_name)
    except AttributeError as exc:
        raise ImportError(spec.missing_package_message) from exc


def _build_chat_kwargs(
    provider_name: str,
    api_key: str,
    model_params: Mapping[str, Any],
    callbacks: list[Any],
) -> dict[str, Any]:
    spec = _get_provider_spec(provider_name)
    kwargs = {
        spec.api_key_argument: api_key,
        "model": model_params["model"],
        "temperature": model_params["temperature"],
        spec.max_tokens_argument: model_params["max_tokens"],
        "timeout": model_params.get("timeout", 120),
        "callbacks": callbacks,
    }
    return kwargs


def create_provider_model_instance(
    provider_name: str,
    *,
    api_key: str,
    model_params: Mapping[str, Any],
    callbacks: list[Any],
) -> Any:
    chat_class = _load_chat_class(provider_name)
    return chat_class(
        **_build_chat_kwargs(provider_name, api_key, model_params, callbacks)
    )


class RuntimeLLMProvider:
    """Adapter-backed provider used by the legacy llm_factory wrapper."""

    def __init__(
        self,
        provider_name: str,
        *,
        runtime_settings_loader: Callable[[], Any | None] | None,
        cost_callback_factory: Callable[[str], Any],
        exception_handler: Callable[..., Any],
        logger: Any,
        environ: MutableMapping[str, str] | None = None,
        getenv: Callable[[str], str | None] = os.getenv,
        path_exists: Callable[[str], bool] = os.path.exists,
    ) -> None:
        self.provider_name = provider_name
        self.runtime_settings_loader = runtime_settings_loader
        self.cost_callback_factory = cost_callback_factory
        self.exception_handler = exception_handler
        self.logger = logger
        self.environ = environ if environ is not None else os.environ
        self.getenv = getenv
        self.path_exists = path_exists

    def create_model(
        self,
        model_config: dict[str, Any],
        callbacks: list[Any] | None = None,
    ) -> Any:
        spec = _get_provider_spec(self.provider_name)
        settings = resolve_runtime_settings(self.runtime_settings_loader, self.logger)

        if self.provider_name == "gemini":
            prepare_google_runtime_environment(
                self.logger,
                environ=self.environ,
                path_exists=self.path_exists,
            )

        api_key = resolve_provider_api_key(
            self.provider_name,
            settings=settings,
            getenv=self.getenv,
        )
        if not api_key:
            raise ValueError(spec.missing_api_key_message)

        model_params = build_provider_model_params(
            self.provider_name,
            model_config,
            settings=settings,
            logger=self.logger,
        )
        all_callbacks = build_provider_callbacks(
            self.provider_name,
            callbacks,
            cost_callback_factory=self.cost_callback_factory,
            exception_handler=self.exception_handler,
            logger=self.logger,
        )
        return create_provider_model_instance(
            self.provider_name,
            api_key=api_key,
            model_params=model_params,
            callbacks=all_callbacks,
        )

    def is_available(self) -> bool:
        try:
            _load_chat_class(self.provider_name)
        except ImportError:
            return False

        settings = resolve_runtime_settings(self.runtime_settings_loader, self.logger)
        return bool(
            resolve_provider_api_key(
                self.provider_name,
                settings=settings,
                getenv=self.getenv,
            )
        )


def build_runtime_provider_registry(
    *,
    runtime_settings_loader: Callable[[], Any | None] | None,
    cost_callback_factory: Callable[[str], Any],
    exception_handler: Callable[..., Any],
    logger: Any,
) -> dict[str, RuntimeLLMProvider]:
    return {
        name: RuntimeLLMProvider(
            name,
            runtime_settings_loader=runtime_settings_loader,
            cost_callback_factory=cost_callback_factory,
            exception_handler=exception_handler,
            logger=logger,
        )
        for name in _PROVIDER_SPECS
    }


__all__ = [
    "RuntimeLLMProvider",
    "build_provider_callbacks",
    "build_provider_model_params",
    "build_runtime_provider_registry",
    "create_provider_model_instance",
    "prepare_google_runtime_environment",
    "resolve_provider_api_key",
    "resolve_runtime_settings",
]
