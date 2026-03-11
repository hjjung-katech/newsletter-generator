"""
LLM Factory Module

이 모듈은 다양한 LLM 제공자(Gemini, OpenAI, Anthropic)를 통합 관리하고,
기능별로 최적화된 LLM 모델을 제공하는 팩토리 클래스를 구현합니다.

F-14: 중앙화된 설정을 활용한 성능 최적화
"""

from typing import Any, Dict, Iterator, List, Optional, cast

from newsletter_core.application.llm_factory import (
    build_provider_info,
    get_default_model,
    resolve_provider_selection,
)
from newsletter_core.application.llm_factory_fallback import (
    create_fallback_model,
    invoke_with_fallback,
    is_fallback_trigger_error,
    resolve_fallback_runtime_config,
)
from newsletter_core.infrastructure.llm_factory_runtime import (
    build_provider_callbacks,
    build_runtime_provider_registry,
)
from newsletter_core.public.settings import get_llm_config

from .cost_tracking import get_cost_callback_for_provider
from .utils.error_handling import handle_exception
from .utils.logger import get_logger

# 중앙화된 설정 import 추가 (F-14)
try:
    from .centralized_settings import get_settings

    CENTRALIZED_SETTINGS_AVAILABLE = True
except ImportError:
    CENTRALIZED_SETTINGS_AVAILABLE = False
    get_settings = None

# 로거 초기화
logger = get_logger()

# LangChain Runnable 관련 imports 추가
try:
    from langchain_core.runnables import Runnable
    from langchain_core.runnables.config import RunnableConfig
except ImportError:
    # Fallback for older versions
    Runnable = object
    RunnableConfig = dict


def _load_runtime_settings() -> Any | None:
    if not CENTRALIZED_SETTINGS_AVAILABLE or get_settings is None:
        return None
    return get_settings()


class QuotaExceededError(Exception):
    """API 할당량 초과 에러"""

    pass


class LLMWithFallback(Runnable):
    """
    API 할당량 초과 시 자동으로 다른 제공자로 fallback하는 LLM 래퍼
    F-14: 중앙화된 설정 활용
    """

    def __init__(
        self,
        primary_llm: Any,
        factory: "LLMFactory",
        task: str,
        callbacks: Optional[List[Any]] = None,
    ) -> None:
        """F-14 중앙화된 설정을 사용한 LLM with Fallback 초기화"""
        self.primary_llm = primary_llm
        self.fallback_llm: Any | None = None
        self.factory = factory
        self.task = task
        self.callbacks = callbacks or []
        self.last_used = "primary"

        self.runtime_config = resolve_fallback_runtime_config(
            _load_runtime_settings,
            logger=logger,
        )
        self.max_retries = self.runtime_config.max_retries
        self.retry_delay = self.runtime_config.retry_delay
        self.timeout = self.runtime_config.timeout
        self.test_mode = self.runtime_config.test_mode
        self.mock_responses = self.runtime_config.mock_responses
        self.skip_real_api = self.runtime_config.skip_real_api

        logger.info(
            f"F-14 LLM 설정 로드: 재시도={self.max_retries}, "
            f"지연={self.retry_delay}초, 타임아웃={self.timeout}초, "
            f"테스트모드={self.test_mode}"
        )

        logger.info(
            f"F-14 LLM ({task}) 초기화 완료: "
            f"타입={type(primary_llm).__name__}, "
            f"테스트모드={self.test_mode}, "
            f"모킹={self.mock_responses}"
        )

        if self.test_mode:
            logger.info("F-14 테스트 모드 활성화 - 모킹된 응답 사용")

    def invoke(
        self,
        input_data: Any,
        config: Optional[RunnableConfig] = None,
        **kwargs: Any,
    ) -> Any:
        """F-14 중앙화된 설정을 사용한 LLM 호출 with fallback"""

        # F-14: 테스트 모드에서는 모킹된 응답 반환
        if self.test_mode and self.mock_responses:
            return self._generate_mock_response(input_data)

        # F-14: 실제 API 호출 건너뛰기 옵션
        if self.skip_real_api:
            logger.info("F-14: 실제 API 호출 건너뛰기, 모킹된 응답 반환")
            return self._generate_mock_response(input_data)

        # 실제 LLM 호출 (프로덕션 모드)
        return self._invoke_real_llm(input_data, config, **kwargs)

    def _generate_mock_response(self, input_data: Any) -> Any:
        """F-14 테스트 모드용 모킹된 응답 생성"""
        logger.debug("F-14 테스트 모드: 모킹된 응답 생성 중...")

        # 입력 데이터 기반 모킹된 응답 생성
        if isinstance(input_data, str):
            # 작업별 맞춤형 응답
            if "키워드" in input_data or "keyword" in input_data.lower():
                mock_content = "AI, 머신러닝, 딥러닝, 자연어처리, 컴퓨터비전"
            elif "요약" in input_data or "summary" in input_data.lower():
                mock_content = "AI 기술이 빠르게 발전하고 있으며, 다양한 분야에서 활용되고 있습니다."
            elif "번역" in input_data or "translate" in input_data.lower():
                mock_content = "안녕하세요, 세계!"
            else:
                mock_content = f"F-14 테스트 응답: {input_data[:50]}에 대한 모킹된 결과입니다."
        else:
            mock_content = "F-14 테스트 응답: 중앙화된 설정을 사용한 모킹된 LLM 응답입니다."

        # LangChain AIMessage 형태로 반환
        try:
            from langchain_core.messages import AIMessage

            return AIMessage(content=mock_content)
        except ImportError:
            # Fallback: 간단한 객체 반환
            class MockAIMessage:
                def __init__(self, content: str) -> None:
                    self.content = content

                def __str__(self) -> str:
                    return self.content

            return MockAIMessage(mock_content)

    def _invoke_real_llm(
        self,
        input_data: Any,
        config: Optional[RunnableConfig] = None,
        **kwargs: Any,
    ) -> Any:
        """실제 LLM 호출 (프로덕션 모드)"""
        result, last_used = invoke_with_fallback(
            primary_llm=self.primary_llm,
            input_data=input_data,
            config=config,
            kwargs=kwargs,
            runtime_config=self.runtime_config,
            fallback_loader=self._load_fallback_llm,
            logger=logger,
        )
        self.last_used = last_used
        return result

    def stream(
        self,
        input_data: Any,
        config: Optional[RunnableConfig] = None,
        **kwargs: Any,
    ) -> Iterator[Any]:
        """스트리밍 지원 (F-14 개선)"""
        try:
            if hasattr(self.primary_llm, "stream"):
                yield from self.primary_llm.stream(
                    input_data,
                    config=config,
                    **kwargs,
                )
                return

            result = self.invoke(input_data, config=config, **kwargs)
            yield result
        except Exception as e:
            if is_fallback_trigger_error(e):
                fallback_llm = self._load_fallback_llm()

                if fallback_llm is None:
                    raise e

                if hasattr(fallback_llm, "stream"):
                    yield from fallback_llm.stream(
                        input_data,
                        config=config,
                        **kwargs,
                    )
                    return

                result = fallback_llm.invoke(
                    input_data,
                    config=config,
                    **kwargs,
                )
                yield result
                return

            raise e

    def batch(
        self,
        inputs: Any,
        config: Optional[RunnableConfig] = None,
        **kwargs: Any,
    ) -> Any:
        """배치 처리 지원 (F-14 개선)"""
        try:
            if hasattr(self.primary_llm, "batch"):
                return self.primary_llm.batch(inputs, config=config, **kwargs)

            return [
                self.invoke(input_data, config=config, **kwargs)
                for input_data in inputs
            ]
        except Exception as e:
            if is_fallback_trigger_error(e):
                fallback_llm = self._load_fallback_llm()

                if fallback_llm is None:
                    raise e

                if hasattr(fallback_llm, "batch"):
                    return fallback_llm.batch(inputs, config=config, **kwargs)

                return [
                    fallback_llm.invoke(input_data, config=config, **kwargs)
                    for input_data in inputs
                ]

            raise e

    def _load_fallback_llm(self) -> Any | None:
        """Fallback LLM을 생성해 캐시하거나 기존 인스턴스를 반환합니다."""
        if self.fallback_llm is not None:
            return self.fallback_llm

        primary_provider = type(self.primary_llm).__name__
        primary_model = getattr(self.primary_llm, "model", "unknown")
        self.fallback_llm = create_fallback_model(
            primary_provider_name=primary_provider,
            primary_model=primary_model,
            temperature=getattr(self.primary_llm, "temperature", 0.3),
            available_providers=self.factory.get_available_providers(),
            default_model_getter=self.factory._get_default_model,
            providers=self.factory.providers,
            callbacks=list(self.callbacks),
            callback_builder=self.factory._build_callbacks,
            logger=logger,
        )
        return self.fallback_llm

    def __getattr__(self, name: str) -> Any:
        """다른 속성들은 primary LLM에 위임"""
        return getattr(self.primary_llm, name)


class LLMFactory:
    """LLM 팩토리 클래스"""

    def __init__(self) -> None:
        self.providers = build_runtime_provider_registry(
            runtime_settings_loader=_load_runtime_settings,
            cost_callback_factory=get_cost_callback_for_provider,
            exception_handler=handle_exception,
            logger=logger,
        )

    @property
    def llm_config(self) -> Dict[str, Any]:
        return cast(Dict[str, Any], get_llm_config())

    def _build_callbacks(
        self,
        provider_name: str,
        callbacks: Optional[List[Any]] = None,
        *,
        fallback_path: bool = False,
    ) -> List[Any]:
        final_callbacks: List[Any] = build_provider_callbacks(
            provider_name,
            callbacks,
            cost_callback_factory=get_cost_callback_for_provider,
            exception_handler=handle_exception,
            logger=logger,
            fallback_path=fallback_path,
        )
        return final_callbacks

    def get_llm_for_task(
        self,
        task: str,
        callbacks: Optional[List[Any]] = None,
        enable_fallback: bool = True,
    ) -> Any:
        """
        특정 작업에 최적화된 LLM 모델을 반환합니다.

        Args:
            task: 작업 유형 (keyword_generation, theme_extraction, etc.)
            callbacks: LangChain 콜백 리스트
            enable_fallback: 할당량 초과 시 자동 fallback 활성화 여부

        Returns:
            LLM 모델 인스턴스 (fallback 기능 포함)
        """
        selection = resolve_provider_selection(
            self.llm_config,
            task,
            self.providers.keys(),
            self.get_available_providers(),
        )
        provider_name = selection.selected_provider
        provider = self.providers[provider_name]

        if selection.used_fallback:
            logger.warning(
                (
                    f"{selection.requested_provider}을 사용할 수 없어 "
                    f"{provider_name}으로 대체합니다"
                )
            )

        final_callbacks = self._build_callbacks(
            provider_name,
            callbacks,
            fallback_path=selection.used_fallback,
        )
        llm = provider.create_model(selection.model_config, final_callbacks)

        # Fallback 래퍼 적용
        if enable_fallback:
            return LLMWithFallback(llm, self, task, final_callbacks)
        else:
            return llm

    def _get_default_model(self, provider_name: str) -> str:
        """제공자별 기본 모델명을 반환합니다."""
        default_model: str = get_default_model(self.llm_config, provider_name)
        return default_model

    def get_available_providers(self) -> List[str]:
        """사용 가능한 제공자 목록을 반환합니다."""
        available_providers: List[str] = []
        for name, provider in self.providers.items():
            if provider.is_available():
                available_providers.append(name)
        return available_providers

    def get_provider_info(self) -> Dict[str, Dict[str, Any]]:
        """각 제공자의 사용 가능 여부와 모델 정보를 반환합니다."""
        availability: Dict[str, bool] = {}
        for name, provider in self.providers.items():
            availability[name] = provider.is_available()
        provider_info: Dict[str, Dict[str, Any]] = build_provider_info(
            self.llm_config,
            self.providers.keys(),
            availability,
        )
        return provider_info


_llm_factory_instance: LLMFactory | None = None


def get_llm_factory() -> LLMFactory:
    global _llm_factory_instance
    if _llm_factory_instance is None:
        _llm_factory_instance = LLMFactory()
    return _llm_factory_instance


class _LazyLLMFactory:
    def __getattr__(self, item: str) -> Any:
        return getattr(get_llm_factory(), item)

    def __repr__(self) -> str:  # pragma: no cover
        return "<LazyLLMFactory proxy>"


llm_factory = _LazyLLMFactory()


def get_llm_for_task(
    task: str,
    callbacks: Optional[List[Any]] = None,
    enable_fallback: bool = True,
) -> Any:
    """
    편의 함수: 특정 작업에 최적화된 LLM 모델을 반환합니다.

    Args:
        task: 작업 유형
        callbacks: LangChain 콜백 리스트
        enable_fallback: 할당량 초과 시 자동 fallback 활성화 여부

    Returns:
        LLM 모델 인스턴스
    """
    return get_llm_factory().get_llm_for_task(task, callbacks, enable_fallback)


def get_available_providers() -> List[str]:
    """편의 함수: 사용 가능한 LLM 제공자 목록을 반환합니다."""
    return get_llm_factory().get_available_providers()


def get_provider_info() -> Dict[str, Dict[str, Any]]:
    """편의 함수: 제공자 정보를 반환합니다."""
    return get_llm_factory().get_provider_info()
