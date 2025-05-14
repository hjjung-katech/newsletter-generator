"""
Mock module for langchain_google_genai
"""

from unittest.mock import Mock
from langchain_core.messages import AIMessage


class MockChatGoogleGenerativeAI:
    """Mock for ChatGoogleGenerativeAI"""

    def __init__(self, model="", google_api_key="", temperature=0, **kwargs):
        self.model = model
        self.google_api_key = google_api_key
        self.temperature = temperature
        self.kwargs = kwargs

    def invoke(self, messages):
        return AIMessage(
            content="<!DOCTYPE html><html><body><h1>Mock Newsletter - 머신러닝</h1><p>This is a mock newsletter about 구글 AI.</p></body></html>"
        )

    def __call__(self, *args, **kwargs):
        return self.invoke(args[0] if args else [])


# Create module-level mock
chat_google_generative_ai = MockChatGoogleGenerativeAI
ChatGoogleGenerativeAI = MockChatGoogleGenerativeAI
