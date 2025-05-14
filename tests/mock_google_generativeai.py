"""
Mock module for google.generativeai
"""

from unittest.mock import Mock


class CachedContent:
    """Mock for caching module"""

    def __init__(self, text=""):
        self.text = text


class GenerativeModel:
    """Mock for GenerativeModel"""

    def __init__(self, model_name="", **kwargs):
        self.model_name = model_name
        self.kwargs = kwargs

    def generate_content(self, content, **kwargs):
        response = Mock()
        response.text = "<html><body><h1>Mock Newsletter</h1><p>This is a mock newsletter.</p></body></html>"
        return response


# Module configuration function
def configure(api_key=None, **kwargs):
    """Mock configure function"""
    return None


# Create module-level variables and functions
types = Mock()
types.HarmCategory = Mock()
types.HarmBlockThreshold = Mock()

# Create caching module
caching = Mock()
caching.CachedContent = CachedContent
