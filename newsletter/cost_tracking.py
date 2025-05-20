import os
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    from langchain.callbacks.base import BaseCallbackHandler
    from langsmith import Client
except Exception:  # Fallback when langchain is not installed

    class BaseCallbackHandler:
        pass

    Client = None


class GoogleGenAICostCB(BaseCallbackHandler):
    """Callback handler to track Google Generative AI token usage and costs."""

    # Gemini 2.5 Pro 모델 가격 (2025년 5월 기준)
    # https://ai.google.dev/pricing 참조
    USD_INPUT_1K = 0.0007  # Input token cost per 1K tokens (Gemini 2.5 Pro)
    USD_OUTPUT_1K = 0.0014  # Output token cost per 1K tokens (Gemini 2.5 Pro)

    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_cost = 0.0
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Run when LLM starts running."""
        # If you need to log prompt_tokens on start, you might need to estimate
        # or get it from `serialized` if available.
        # For now, we will rely on on_llm_end for token counts from the response.
        pass

    def on_llm_end(self, response, **kwargs):
        """Run when LLM ends running."""
        # For LangChain >= 0.1.0, response is an LLMResult
        if hasattr(response, "llm_output") and response.llm_output:
            token_usage = response.llm_output.get("token_usage")
            model_name = response.llm_output.get("model_name")  # Gemini specific

            if token_usage and model_name:  # Check if token_usage and model_name exist
                in_tok = token_usage.get("prompt_token_count", 0)  # Gemini specific
                out_tok = token_usage.get(
                    "candidates_token_count", 0
                )  # Gemini specific

                self.prompt_tokens += in_tok
                self.completion_tokens += out_tok

                input_cost = (in_tok * self.USD_INPUT_1K) / 1000
                output_cost = (out_tok * self.USD_OUTPUT_1K) / 1000
                this_cost = input_cost + output_cost
                self.total_cost += this_cost

                if os.environ.get("DEBUG_COST_TRACKING"):
                    print(
                        f"[Token Usage - {model_name}] Input: {in_tok}, Output: {out_tok}, Cost: ${this_cost:.6f}"
                    )
            elif os.environ.get("DEBUG_COST_TRACKING"):
                print(
                    f"[DEBUG_COST_TRACKING] Token usage or model name not found in llm_output: {response.llm_output}"
                )

        # Fallback for older or direct Google AI calls if necessary (though tools.py should now standardize)
        # This part might become less relevant if all calls are standardized via LLMResult
        elif hasattr(response, "usage_metadata"):  # Direct Google AI usage
            meta = response.usage_metadata
            in_tok = getattr(meta, "prompt_token_count", 0)
            out_tok = getattr(meta, "candidates_token_count", 0)

            self.prompt_tokens += in_tok
            self.completion_tokens += out_tok

            input_cost = (in_tok * self.USD_INPUT_1K) / 1000
            output_cost = (out_tok * self.USD_OUTPUT_1K) / 1000
            this_cost = input_cost + output_cost
            self.total_cost += this_cost

            if os.environ.get("DEBUG_COST_TRACKING"):
                print(
                    f"[Token Usage - Direct Google AI] Input: {in_tok}, Output: {out_tok}, Cost: ${this_cost:.6f}"
                )
        elif os.environ.get("DEBUG_COST_TRACKING"):
            print(
                f"[DEBUG_COST_TRACKING] No standard token usage information found in response: {type(response)}"
            )

    def get_summary(self) -> Dict[str, Any]:
        """Return a summary of token usage and costs."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.prompt_tokens + self.completion_tokens,
            "total_cost_usd": self.total_cost,
            "timestamp": self.timestamp,
        }


# Legacy callback handler for compatibility
class LangSmithCallbackHandler(BaseCallbackHandler):
    """Legacy callback handler for backwards compatibility."""

    def __init__(self) -> None:
        # token and cost counters
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_cost = 0.0

    def on_llm_end(self, response, **kwargs) -> None:
        usage = getattr(response, "usage", None)
        if usage is None and isinstance(response, dict):
            usage = response.get("usage")
        if usage:
            self.prompt_tokens += int(usage.get("prompt_tokens", 0))
            self.completion_tokens += int(usage.get("completion_tokens", 0))
            # Fallback cost estimation if not provided
            self.total_cost += float(usage.get("cost", 0.0))


def get_tracking_callbacks():
    """LangSmith 트레이싱 및 비용 추적을 위한 콜백 목록을 반환합니다.

    LangChain 0.3+ 버전에 맞게 구현됨
    """
    callbacks = []

    # LangChain 트레이싱 설정 (LANGCHAIN_TRACING_V2 환경 변수 사용)
    langchain_tracing_v2_env = os.environ.get("LANGCHAIN_TRACING_V2", "false").lower()
    is_tracing_enabled = (
        langchain_tracing_v2_env == "true" or langchain_tracing_v2_env == "1"
    )
    api_key_env = os.environ.get("LANGCHAIN_API_KEY")

    cleaned_api_key = None
    if api_key_env:
        # Remove potential surrounding quotes and comments
        cleaned_api_key = api_key_env.strip().strip("'\"")
        if "#" in cleaned_api_key:
            cleaned_api_key = cleaned_api_key.split("#", 1)[0].strip()

        # Set the cleaned key back into the environment for LangSmith client
        # This is a bit of a workaround; ideally, the client would handle this.
        os.environ["LANGCHAIN_API_KEY_CLEANED_FOR_TRACER"] = cleaned_api_key
        # LangChainTracer will pick up LANGCHAIN_API_KEY by default,
        # but we ensure it uses the cleaned one if we pass it explicitly.

    api_key_set = bool(cleaned_api_key)

    # More detailed debug print for the API key itself
    print(
        f"[DEBUG_COST_TRACKING] LANGCHAIN_API_KEY raw value: '{api_key_env}' (Type: {type(api_key_env)}, Length: {len(api_key_env) if api_key_env else 0})"
    )
    if cleaned_api_key != api_key_env:
        print(
            f"[DEBUG_COST_TRACKING] LANGCHAIN_API_KEY cleaned value: '{cleaned_api_key}' (Used for LangSmith)"
        )

    if is_tracing_enabled and api_key_set:
        try:
            from langsmith import (
                traceable,
            )  # 이 부분은 LangChainTracer와 직접 관련 없음
            from langchain.callbacks.tracers.langchain import LangChainTracer

            project_name = os.environ.get("LANGCHAIN_PROJECT", "default-project")
            print(
                f"[DEBUG] Initializing LangChainTracer for project: {project_name} with cleaned API key."
            )  # 디버그 로그 추가

            # Pass the cleaned API key explicitly if the tracer doesn't automatically pick up the modified env var
            # However, LangChainTracer typically uses os.environ.get("LANGCHAIN_API_KEY")
            # So the os.environ["LANGCHAIN_API_KEY_CLEANED_FOR_TRACER"] might not be directly used by it unless we pass api_key=cleaned_api_key
            # For now, let's assume it re-reads from os.environ or we modify the original LANGCHAIN_API_KEY.
            # A safer approach is to temporarily set os.environ["LANGCHAIN_API_KEY"] to the cleaned key for the tracer's initialization.

            original_api_key = os.environ.get("LANGCHAIN_API_KEY")
            os.environ["LANGCHAIN_API_KEY"] = (
                cleaned_api_key  # Temporarily override for tracer
            )

            tracer = LangChainTracer(
                project_name=project_name
            )  # api_key can be passed here if needed

            if original_api_key is not None:  # Restore original key if it existed
                os.environ["LANGCHAIN_API_KEY"] = original_api_key
            else:  # If it was not set, remove our temporary one
                del os.environ["LANGCHAIN_API_KEY"]

            # Remove the temporary cleaned key variable as well
            if "LANGCHAIN_API_KEY_CLEANED_FOR_TRACER" in os.environ:
                del os.environ["LANGCHAIN_API_KEY_CLEANED_FOR_TRACER"]

            callbacks.append(tracer)
            print(f"LangSmith tracing enabled for project: {project_name}")
        except Exception as e:
            print(f"Warning: Failed to initialize LangSmith tracing: {e}")
    else:
        print("[DEBUG] LangSmith tracing not enabled or API key not set.")
        print(f"  LANGCHAIN_TRACING_V2 value: {os.environ.get('LANGCHAIN_TRACING_V2')}")
        print(f"  Evaluated as enabled: {is_tracing_enabled}")
        print(f"  LANGCHAIN_API_KEY is set: {api_key_set}")
        print(f"  LANGCHAIN_API_KEY actual value for check: '{api_key_env}'")

    # Google GenAI 비용 추적
    try:
        callbacks.append(GoogleGenAICostCB())
    except Exception as e:
        print(f"Warning: Failed to initialize Google GenAI cost tracking: {e}")

    return callbacks
