"""Shared LLM and article formatting utilities for newsletter chains."""

import logging
import os
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

from newsletter_core.public.settings import get_setting_value

from .utils.error_handling import handle_exception
from .utils.logger import get_logger

logger = get_logger(__name__)


def get_llm(
    temperature: float = 0.3,
    callbacks: list[Any] | None = None,
    task: str = "html_generation",
) -> Any:
    """
    지정된 작업에 최적화된 LLM 모델 인스턴스를 생성합니다.

    Args:
        temperature: 모델 온도 설정
        callbacks: LangChain 콜백 리스트
        task: 작업 유형 (html_generation, news_summarization 등)
    """
    if callbacks is None:
        callbacks = []
    if os.environ.get("ENABLE_COST_TRACKING"):
        try:
            from .cost_tracking import get_tracking_callbacks

            callbacks += get_tracking_callbacks()
        except Exception as e:
            handle_exception(e, "비용 추적 콜백 추가", log_level=logging.INFO)
            # 비용 추적 실패는 치명적이지 않음

    # LLM 팩토리를 사용하여 작업별 최적화된 모델 생성
    try:
        from .llm_factory import get_llm_for_task

        llm = get_llm_for_task(task, callbacks, enable_fallback=False)

        # 온도 설정이 다른 경우 모델 재구성
        if hasattr(llm, "temperature") and llm.temperature != temperature:
            # 기존 설정을 복사하고 온도만 변경
            if hasattr(llm, "_get_client_config"):
                # Gemini의 경우
                return type(llm)(
                    model=llm.model,
                    google_api_key=getattr(llm, "google_api_key", None),
                    temperature=temperature,
                    transport=getattr(llm, "transport", "rest"),
                    callbacks=callbacks,
                    convert_system_message_to_human=getattr(
                        llm, "convert_system_message_to_human", False
                    ),
                    timeout=getattr(llm, "timeout", 60),
                    max_retries=getattr(llm, "max_retries", 2),
                    disable_streaming=getattr(llm, "disable_streaming", False),
                )
            else:
                # OpenAI, Anthropic의 경우 - F-14 중앙화된 설정 시스템 적용
                if "ChatOpenAI" in str(type(llm)):
                    return type(llm)(
                        model=getattr(
                            llm, "model_name", getattr(llm, "model", "gpt-4o-mini")
                        ),
                        api_key=getattr(llm, "api_key", None),
                        temperature=temperature,
                        callbacks=callbacks,
                        timeout=getattr(llm, "timeout", 60),
                        max_retries=getattr(llm, "max_retries", 2),
                    )
                elif "ChatAnthropic" in str(type(llm)):
                    return type(llm)(
                        model=getattr(
                            llm,
                            "model_name",
                            getattr(llm, "model", "claude-3-haiku-20240307"),
                        ),
                        api_key=getattr(llm, "api_key", None),
                        temperature=temperature,
                        callbacks=callbacks,
                        timeout=getattr(llm, "timeout", 60),
                        max_retries=getattr(llm, "max_retries", 2),
                    )
                else:
                    # 기타 제공자의 경우
                    return type(llm)(
                        model=getattr(
                            llm,
                            "model_name",
                            getattr(llm, "model", llm.__class__.__name__),
                        ),
                        api_key=getattr(llm, "api_key", None),
                        temperature=temperature,
                        callbacks=callbacks,
                        timeout=getattr(llm, "timeout", 60),
                        max_retries=getattr(llm, "max_retries", 2),
                    )

        return llm

    except Exception as e:
        # Google Cloud 인증 관련 오류는 조용히 처리
        error_msg = str(e).lower()
        if "credentials" in error_msg or "not found" in error_msg:
            # 조용한 fallback (디버그 모드에서만 출력)
            if os.environ.get("DEBUG_LLM_FACTORY"):
                logger.debug(f"Debug: LLM factory failed, using fallback: {e}")
        else:
            # 다른 오류는 출력 - F-14 로거 수정
            logger.warning(
                f"Warning: LLM factory failed, falling back to default Gemini: {e}"
            )

        # Fallback to original Gemini implementation
        if not get_setting_value("GEMINI_API_KEY"):
            raise ValueError("GEMINI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")

        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=get_setting_value("GEMINI_API_KEY"),
            temperature=temperature,
            transport="rest",
            callbacks=callbacks,
            convert_system_message_to_human=False,
            timeout=60,
            max_retries=3,  # 재시도 횟수 증가
            disable_streaming=False,
        )


# 기사 목록을 텍스트로 변환하는 함수
def format_articles(data: dict[str, Any]) -> str:
    """
    기사 목록을 텍스트 형식으로 변환합니다.

    Args:
        data: 기사 데이터를 포함하는 딕셔너리

    Returns:
        str: 포맷팅된 기사 텍스트
    """
    articles = data.get("articles", [])
    if not articles:
        return "기사 데이터를 찾을 수 없습니다."

    formatted_articles = []
    for i, article in enumerate(articles):
        title = article.get("title", "제목 없음")
        url = article.get("url", "#")
        content = article.get("content", "내용 없음")
        source = article.get("source", "출처 없음")
        date = article.get("date", "날짜 없음")

        formatted_articles.append(
            f"기사 #{i + 1}:\n제목: {title}\nURL: {url}\n출처: {source}\n"
            f"날짜: {date}\n내용:\n{content}\n"
        )

    return "\n---\n".join(formatted_articles)
