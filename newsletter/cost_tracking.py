import os
from typing import List

try:
    from langchain.callbacks.base import BaseCallbackHandler
except Exception:  # Fallback when langchain is not installed

    class BaseCallbackHandler:
        pass


class LangSmithCallbackHandler(BaseCallbackHandler):
    """Simple callback handler to record token usage and estimated cost."""

    def __init__(self) -> None:
        # token and cost counters
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_cost = 0.0

    def on_llm_end(self, response, **kwargs) -> None:  # type: ignore[override]
        usage = getattr(response, "usage", None)
        if usage is None and isinstance(response, dict):
            usage = response.get("usage")
        if usage:
            self.prompt_tokens += int(usage.get("prompt_tokens", 0))
            self.completion_tokens += int(usage.get("completion_tokens", 0))
            # Fallback cost estimation if not provided
            self.total_cost += float(usage.get("cost", 0.0))


def get_tracking_callbacks() -> List[LangSmithCallbackHandler]:
    """Return LangSmith callbacks if cost tracking is enabled."""
    if os.environ.get("ENABLE_COST_TRACKING"):
        return [LangSmithCallbackHandler()]
    return []
