"""
Helper module for managing test dependencies and imports
"""

import importlib
import os
import sys
from types import ModuleType
from unittest.mock import Mock, patch

# Use mocks from tests directory
from tests.mock_langchain_google_genai import MockChatGoogleGenerativeAI


def create_mock_module(name):
    """Create a new mock module"""
    module = ModuleType(name)
    module.__file__ = f"<mock {name}>"
    return module


def mock_imports():
    """Apply mock imports to avoid external dependencies"""
    # Create base modules if they don't exist
    if "google" not in sys.modules:
        sys.modules["google"] = create_mock_module("google")

    # google.generativeai는 더 이상 사용하지 않음 (langchain-google-genai로 대체됨)

    # Mock langchain modules
    if "langchain_google_genai" not in sys.modules:
        langchain_google_genai = create_mock_module("langchain_google_genai")
        langchain_google_genai.ChatGoogleGenerativeAI = MockChatGoogleGenerativeAI
        sys.modules["langchain_google_genai"] = langchain_google_genai

    if "langchain_google_genai.chat_models" not in sys.modules:
        chat_models = create_mock_module("langchain_google_genai.chat_models")
        chat_models.ChatGoogleGenerativeAI = MockChatGoogleGenerativeAI
        sys.modules["langchain_google_genai.chat_models"] = chat_models

    return {
        "chat_google_generative_ai": MockChatGoogleGenerativeAI,
    }
