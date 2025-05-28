"""
LLM Factory Module

이 모듈은 다양한 LLM 제공자(Gemini, OpenAI, Anthropic)를 통합 관리하고,
기능별로 최적화된 LLM 모델을 제공하는 팩토리 클래스를 구현합니다.
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

# Google Cloud 인증 문제 해결
# 시스템에 잘못된 GOOGLE_APPLICATION_CREDENTIALS가 설정되어 있는 경우 처리
google_creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
if google_creds_path and not os.path.exists(google_creds_path):
    # 파일이 존재하지 않으면 환경변수 제거
    print(
        f"Warning: GOOGLE_APPLICATION_CREDENTIALS points to non-existent file: {google_creds_path}"
    )
    print("Disabling Google Cloud authentication to use API key only.")
    os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)

# Google Cloud 기본 인증 파일 검색 완전 비활성화
# 이렇게 하면 langchain_google_genai가 credentials.json을 찾지 않음
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = ""
os.environ["GOOGLE_CLOUD_PROJECT"] = ""

# Google Cloud SDK 기본 설정 파일도 비활성화
os.environ.pop("CLOUDSDK_CONFIG", None)
os.environ.pop("GCLOUD_PROJECT", None)

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

# LangChain Runnable 관련 imports 추가
try:
    from langchain_core.runnables import Runnable
    from langchain_core.runnables.config import RunnableConfig
    from langchain_core.runnables.utils import Input, Output
except ImportError:
    # Fallback for older versions
    Runnable = object
    RunnableConfig = dict
    Input = Any
    Output = Any

from . import config
from .cost_tracking import get_cost_callback_for_provider


class QuotaExceededError(Exception):
    """API 할당량 초과 에러"""

    pass


class LLMWithFallback(Runnable):
    """
    API 할당량 초과 시 자동으로 다른 제공자로 fallback하는 LLM 래퍼
    """

    def __init__(self, primary_llm, factory, task, callbacks=None):
        self.primary_llm = primary_llm
        self.factory = factory
        self.task = task
        self.callbacks = callbacks or []
        self.fallback_llm = None

    def invoke(self, input_data, config: Optional[RunnableConfig] = None, **kwargs):
        """LLM 호출 시 429 에러 처리"""
        try:
            return self.primary_llm.invoke(input_data, config=config, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            # 529, 429 에러 또는 할당량 초과 관련 에러 감지
            if (
                "529" in error_str
                or "429" in error_str
                or "quota" in error_str
                or "rate limit" in error_str
                or "too many requests" in error_str
                or "overloaded" in error_str
            ):

                print(
                    f"[WARNING] API error ({e}) for {type(self.primary_llm).__name__}. Attempting fallback..."
                )

                # Fallback LLM 생성 (한 번만)
                if self.fallback_llm is None:
                    self.fallback_llm = self._get_fallback_llm()

                if self.fallback_llm:
                    print(
                        f"[INFO] Using fallback LLM: {type(self.fallback_llm).__name__}"
                    )
                    return self.fallback_llm.invoke(input_data, config=config, **kwargs)
                else:
                    raise QuotaExceededError(
                        f"Primary LLM error and no fallback available. Original error: {e}"
                    )
            else:
                # 다른 종류의 에러는 그대로 전파
                raise e

    def stream(self, input_data, config: Optional[RunnableConfig] = None, **kwargs):
        """스트리밍 지원"""
        try:
            if hasattr(self.primary_llm, "stream"):
                return self.primary_llm.stream(input_data, config=config, **kwargs)
            else:
                # 스트리밍을 지원하지 않는 경우 일반 invoke 사용
                result = self.invoke(input_data, config=config, **kwargs)
                yield result
        except Exception as e:
            error_str = str(e).lower()
            if (
                "529" in error_str
                or "429" in error_str
                or "quota" in error_str
                or "rate limit" in error_str
                or "too many requests" in error_str
                or "overloaded" in error_str
            ):

                if self.fallback_llm is None:
                    self.fallback_llm = self._get_fallback_llm()

                if self.fallback_llm and hasattr(self.fallback_llm, "stream"):
                    return self.fallback_llm.stream(input_data, config=config, **kwargs)
                elif self.fallback_llm:
                    result = self.fallback_llm.invoke(
                        input_data, config=config, **kwargs
                    )
                    yield result
                else:
                    raise e
            else:
                raise e

    def batch(self, inputs, config: Optional[RunnableConfig] = None, **kwargs):
        """배치 처리 지원"""
        try:
            if hasattr(self.primary_llm, "batch"):
                return self.primary_llm.batch(inputs, config=config, **kwargs)
            else:
                # 배치를 지원하지 않는 경우 개별 처리
                return [
                    self.invoke(input_data, config=config, **kwargs)
                    for input_data in inputs
                ]
        except Exception as e:
            error_str = str(e).lower()
            if (
                "529" in error_str
                or "429" in error_str
                or "quota" in error_str
                or "rate limit" in error_str
                or "too many requests" in error_str
                or "overloaded" in error_str
            ):

                if self.fallback_llm is None:
                    self.fallback_llm = self._get_fallback_llm()

                if self.fallback_llm and hasattr(self.fallback_llm, "batch"):
                    return self.fallback_llm.batch(inputs, config=config, **kwargs)
                elif self.fallback_llm:
                    return [
                        self.fallback_llm.invoke(input_data, config=config, **kwargs)
                        for input_data in inputs
                    ]
                else:
                    raise e
            else:
                raise e

    def _get_fallback_llm(self):
        """Fallback LLM을 찾아서 반환"""
        primary_provider = type(self.primary_llm).__name__
        primary_model = getattr(self.primary_llm, "model", "unknown")

        print(f"[INFO] Looking for fallback for {primary_provider} ({primary_model})")

        # 1. 같은 제공자 내에서 안정적인 모델로 fallback 시도
        if "gemini" in primary_provider.lower():
            stable_models = ["gemini-1.5-pro", "gemini-1.5-flash"]

            for stable_model in stable_models:
                if stable_model != primary_model:  # 동일한 모델이 아닌 경우만
                    try:
                        print(f"[INFO] Trying stable Gemini model: {stable_model}")
                        fallback_config = {
                            "provider": "gemini",
                            "model": stable_model,
                            "temperature": getattr(
                                self.primary_llm, "temperature", 0.3
                            ),
                            "max_retries": 2,
                            "timeout": 60,
                        }

                        # 비용 추적 콜백 추가
                        fallback_callbacks = list(self.callbacks)
                        try:
                            cost_callback = get_cost_callback_for_provider("gemini")
                            fallback_callbacks.append(cost_callback)
                        except Exception:
                            pass

                        provider = self.factory.providers.get("gemini")
                        if provider and provider.is_available():
                            return provider.create_model(
                                fallback_config, fallback_callbacks
                            )
                    except Exception as e:
                        print(
                            f"[WARNING] Failed to create stable Gemini model {stable_model}: {e}"
                        )
                        continue

        # 2. 다른 제공자로 fallback 시도
        available_providers = self.factory.get_available_providers()

        for provider_name in available_providers:
            provider = self.factory.providers[provider_name]

            # 이미 시도한 제공자는 스킵 (단, Gemini는 다른 모델로 이미 시도했으므로 제외)
            if provider_name == "gemini":
                continue

            try:
                # 제공자별 안정적인 기본 모델 사용
                stable_model_map = {
                    "openai": "gpt-4o",
                    "anthropic": "claude-3-5-sonnet-20241022",
                }

                fallback_model = stable_model_map.get(
                    provider_name, self.factory._get_default_model(provider_name)
                )

                print(
                    f"[INFO] Trying different provider: {provider_name} with model {fallback_model}"
                )

                fallback_config = {
                    "provider": provider_name,
                    "model": fallback_model,
                    "temperature": getattr(self.primary_llm, "temperature", 0.3),
                    "max_retries": 2,
                    "timeout": 60,
                }

                # 비용 추적 콜백 추가
                fallback_callbacks = list(self.callbacks)
                try:
                    cost_callback = get_cost_callback_for_provider(provider_name)
                    fallback_callbacks.append(cost_callback)
                except Exception:
                    pass

                return provider.create_model(fallback_config, fallback_callbacks)

            except Exception as e:
                print(
                    f"[WARNING] Failed to create fallback LLM with {provider_name}: {e}"
                )
                continue

        print("[WARNING] No fallback LLM could be created")
        return None

    def __getattr__(self, name):
        """다른 속성들은 primary LLM에 위임"""
        return getattr(self.primary_llm, name)


class LLMProvider(ABC):
    """LLM 제공자 추상 클래스"""

    @abstractmethod
    def create_model(
        self, model_config: Dict[str, Any], callbacks: Optional[List] = None
    ):
        """LLM 모델 인스턴스를 생성합니다."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """제공자가 사용 가능한지 확인합니다."""
        pass


class GeminiProvider(LLMProvider):
    """Google Gemini 제공자"""

    def create_model(
        self, model_config: Dict[str, Any], callbacks: Optional[List] = None
    ):
        if not self.is_available():
            raise ValueError("Gemini provider is not available. Check GEMINI_API_KEY.")

        if ChatGoogleGenerativeAI is None:
            raise ImportError(
                "langchain_google_genai is not installed. Run: pip install langchain-google-genai"
            )

        # Google Cloud 서비스 계정 인증 비활성화 (API 키 사용)
        # 이렇게 하면 credentials.json 파일을 찾지 않음
        model_kwargs = {
            "model": model_config.get("model", "gemini-1.5-pro"),
            "google_api_key": config.GEMINI_API_KEY,
            "temperature": model_config.get("temperature", 0.3),
            "transport": "rest",
            "callbacks": callbacks or [],
            "convert_system_message_to_human": False,
            "timeout": model_config.get("timeout", 60),
            "max_retries": model_config.get("max_retries", 2),
            "disable_streaming": False,
        }

        # Google Cloud 인증 관련 환경변수가 설정되어 있지 않으면 명시적으로 비활성화
        if not config.GOOGLE_APPLICATION_CREDENTIALS:
            # API 키 기반 인증만 사용하도록 강제
            os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)

        return ChatGoogleGenerativeAI(**model_kwargs)

    def is_available(self) -> bool:
        return bool(config.GEMINI_API_KEY and ChatGoogleGenerativeAI)


class OpenAIProvider(LLMProvider):
    """OpenAI 제공자"""

    def create_model(
        self, model_config: Dict[str, Any], callbacks: Optional[List] = None
    ):
        if not self.is_available():
            raise ValueError("OpenAI provider is not available. Check OPENAI_API_KEY.")

        if ChatOpenAI is None:
            raise ImportError(
                "langchain_openai is not installed. Run: pip install langchain-openai"
            )

        return ChatOpenAI(
            model=model_config.get("model", "gpt-4o"),
            api_key=config.OPENAI_API_KEY,
            temperature=model_config.get("temperature", 0.3),
            callbacks=callbacks or [],
            timeout=model_config.get("timeout", 60),
            max_retries=model_config.get("max_retries", 2),
        )

    def is_available(self) -> bool:
        return bool(config.OPENAI_API_KEY and ChatOpenAI)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude 제공자"""

    def create_model(
        self, model_config: Dict[str, Any], callbacks: Optional[List] = None
    ):
        if not self.is_available():
            raise ValueError(
                "Anthropic provider is not available. Check ANTHROPIC_API_KEY."
            )

        if ChatAnthropic is None:
            raise ImportError(
                "langchain_anthropic is not installed. Run: pip install langchain-anthropic"
            )

        return ChatAnthropic(
            model=model_config.get("model", "claude-3-sonnet-20240229"),
            api_key=config.ANTHROPIC_API_KEY,
            temperature=model_config.get("temperature", 0.3),
            callbacks=callbacks or [],
            timeout=model_config.get("timeout", 60),
            max_retries=model_config.get("max_retries", 2),
        )

    def is_available(self) -> bool:
        return bool(config.ANTHROPIC_API_KEY and ChatAnthropic)


class LLMFactory:
    """LLM 팩토리 클래스"""

    def __init__(self):
        self.providers = {
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
        }
        self.llm_config = config.LLM_CONFIG

    def get_llm_for_task(
        self, task: str, callbacks: Optional[List] = None, enable_fallback: bool = True
    ):
        """
        특정 작업에 최적화된 LLM 모델을 반환합니다.

        Args:
            task: 작업 유형 (keyword_generation, theme_extraction, etc.)
            callbacks: LangChain 콜백 리스트
            enable_fallback: 할당량 초과 시 자동 fallback 활성화 여부

        Returns:
            LLM 모델 인스턴스 (fallback 기능 포함)
        """
        model_config = self.llm_config.get("models", {}).get(task)

        if not model_config:
            # 기본 설정 사용
            provider_name = self.llm_config.get("default_provider", "gemini")
            model_config = {
                "provider": provider_name,
                "model": self._get_default_model(provider_name),
                "temperature": 0.3,
                "max_retries": 2,
                "timeout": 60,
            }

        provider_name = model_config.get("provider", "gemini")
        provider = self.providers.get(provider_name)

        if not provider:
            raise ValueError(f"Unknown provider: {provider_name}")

        # 비용 추적 콜백 자동 추가
        final_callbacks = list(callbacks) if callbacks else []
        try:
            cost_callback = get_cost_callback_for_provider(provider_name)
            final_callbacks.append(cost_callback)
        except Exception as e:
            print(f"Warning: Failed to add cost tracking for {provider_name}: {e}")

        if not provider.is_available():
            # Fallback to available provider
            for fallback_name, fallback_provider in self.providers.items():
                if fallback_provider.is_available():
                    print(
                        f"Warning: {provider_name} not available, falling back to {fallback_name}"
                    )
                    model_config = model_config.copy()
                    model_config["provider"] = fallback_name
                    model_config["model"] = self._get_default_model(fallback_name)

                    # Fallback 제공자에 대한 비용 추적 콜백 업데이트
                    final_callbacks = list(callbacks) if callbacks else []
                    try:
                        cost_callback = get_cost_callback_for_provider(fallback_name)
                        final_callbacks.append(cost_callback)
                    except Exception as e:
                        print(
                            f"Warning: Failed to add cost tracking for {fallback_name}: {e}"
                        )

                    llm = fallback_provider.create_model(model_config, final_callbacks)

                    # Fallback 래퍼 적용
                    if enable_fallback:
                        return LLMWithFallback(llm, self, task, final_callbacks)
                    else:
                        return llm

            raise ValueError(
                f"No LLM providers are available. Please check your API keys."
            )

        llm = provider.create_model(model_config, final_callbacks)

        # Fallback 래퍼 적용
        if enable_fallback:
            return LLMWithFallback(llm, self, task, final_callbacks)
        else:
            return llm

    def _get_default_model(self, provider_name: str) -> str:
        """제공자별 기본 모델명을 반환합니다."""
        provider_models = self.llm_config.get("provider_models", {})
        models = provider_models.get(provider_name, {})
        return models.get(
            "standard",
            {
                "gemini": "gemini-1.5-pro",
                "openai": "gpt-4o",
                "anthropic": "claude-3-sonnet-20240229",
            }.get(provider_name, "gemini-1.5-pro"),
        )

    def get_available_providers(self) -> List[str]:
        """사용 가능한 제공자 목록을 반환합니다."""
        return [
            name for name, provider in self.providers.items() if provider.is_available()
        ]

    def get_provider_info(self) -> Dict[str, Dict[str, Any]]:
        """각 제공자의 사용 가능 여부와 모델 정보를 반환합니다."""
        info = {}
        for name, provider in self.providers.items():
            info[name] = {
                "available": provider.is_available(),
                "models": self.llm_config.get("provider_models", {}).get(name, {}),
            }
        return info


# 전역 팩토리 인스턴스
llm_factory = LLMFactory()


def get_llm_for_task(
    task: str, callbacks: Optional[List] = None, enable_fallback: bool = True
):
    """
    편의 함수: 특정 작업에 최적화된 LLM 모델을 반환합니다.

    Args:
        task: 작업 유형
        callbacks: LangChain 콜백 리스트
        enable_fallback: 할당량 초과 시 자동 fallback 활성화 여부

    Returns:
        LLM 모델 인스턴스
    """
    return llm_factory.get_llm_for_task(task, callbacks, enable_fallback)


def get_available_providers() -> List[str]:
    """편의 함수: 사용 가능한 LLM 제공자 목록을 반환합니다."""
    return llm_factory.get_available_providers()


def get_provider_info() -> Dict[str, Dict[str, Any]]:
    """편의 함수: 제공자 정보를 반환합니다."""
    return llm_factory.get_provider_info()
