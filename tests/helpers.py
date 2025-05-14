"""
Test helpers and mock objects for unit testing
"""

from unittest.mock import Mock


# Mock classes for LangChain
class MockAIMessage:
    """Mock AIMessage class to avoid pydantic issues"""

    def __init__(self, content=""):
        self.content = content
        self.type = "ai"


class MockChatModel:
    """Mock ChatModel class for LangChain"""

    def __init__(self, response_text="Test response"):
        self.response_text = response_text

    def invoke(self, messages):
        return MockAIMessage(content=self.response_text)

    def generate(self, messages):
        return [MockAIMessage(content=self.response_text)]


class MockChatGoogleGenerativeAI(MockChatModel):
    """Mock for ChatGoogleGenerativeAI"""

    def __init__(self, model="", google_api_key="", temperature=0, **kwargs):
        super().__init__()
        self.model = model
        self.google_api_key = google_api_key
        self.temperature = temperature
        self.kwargs = kwargs


# Mock for Google GenerativeAI
class MockGenerativeModel:
    """Mock for Google's GenerativeModel"""

    def __init__(self, model_name="", **kwargs):
        self.model_name = model_name
        self.kwargs = kwargs

    def generate_content(self, content, **kwargs):
        mock_response = Mock()
        mock_response.text = "<html><body><h1>Mock Newsletter</h1><p>This is a mock newsletter.</p></body></html>"
        return mock_response


# Mock genai module
mock_genai = Mock()
mock_genai.configure.return_value = None
mock_genai.GenerativeModel = MockGenerativeModel
