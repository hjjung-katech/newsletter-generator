"""
LLM Factory Module

이 모듈은 다양한 LLM 제공자(Gemini, OpenAI, Anthropic)를 통합 관리하고,
기능별로 최적화된 LLM 모델을 제공하는 팩토리 클래스를 구현합니다.
"""

import os
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

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

from . import config
from .cost_tracking import get_cost_callback_for_provider


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

        return ChatGoogleGenerativeAI(
            model=model_config.get("model", "gemini-1.5-pro"),
            google_api_key=config.GEMINI_API_KEY,
            temperature=model_config.get("temperature", 0.3),
            transport="rest",
            callbacks=callbacks or [],
            convert_system_message_to_human=False,
            timeout=model_config.get("timeout", 60),
            max_retries=model_config.get("max_retries", 2),
            disable_streaming=False,
        )

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

    def get_llm_for_task(self, task: str, callbacks: Optional[List] = None):
        """
        특정 작업에 최적화된 LLM 모델을 반환합니다.

        Args:
            task: 작업 유형 (keyword_generation, theme_extraction, etc.)
            callbacks: LangChain 콜백 리스트

        Returns:
            LLM 모델 인스턴스
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

                    return fallback_provider.create_model(model_config, final_callbacks)

            raise ValueError(
                f"No LLM providers are available. Please check your API keys."
            )

        return provider.create_model(model_config, final_callbacks)

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


def get_llm_for_task(task: str, callbacks: Optional[List] = None):
    """
    편의 함수: 특정 작업에 최적화된 LLM 모델을 반환합니다.

    Args:
        task: 작업 유형
        callbacks: LangChain 콜백 리스트

    Returns:
        LLM 모델 인스턴스
    """
    return llm_factory.get_llm_for_task(task, callbacks)


def get_available_providers() -> List[str]:
    """편의 함수: 사용 가능한 LLM 제공자 목록을 반환합니다."""
    return llm_factory.get_available_providers()


def get_provider_info() -> Dict[str, Dict[str, Any]]:
    """편의 함수: 제공자 정보를 반환합니다."""
    return llm_factory.get_provider_info()
