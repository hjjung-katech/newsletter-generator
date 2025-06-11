"""
Isolated test for tools module without external dependencies
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Create mock modules
mock_langchain_google_genai = Mock()
mock_langchain_google_genai.ChatGoogleGenerativeAI = Mock()

# Patch imports before importing from newsletter
with patch.dict(sys.modules, {"langchain_google_genai": mock_langchain_google_genai}):
    from newsletter.html_utils import clean_html_markers


class TestCleanHtmlMarkers(unittest.TestCase):
    """Test clean_html_markers function in isolation"""

    def test_clean_html_markers_with_filepath_comment(self):
        html_with_comment = """<!-- filepath: c:\\path\\to\\file.html -->
```html
<!DOCTYPE html>
<html>
<head>
    <title>Test</title>
</head>
<body>
    <h1>Hello</h1>
</body>
</html>
```
"""
        expected_html = """<!DOCTYPE html>
<html>
<head>
    <title>Test</title>
</head>
<body>
    <h1>Hello</h1>
</body>
</html>"""
        self.assertEqual(clean_html_markers(html_with_comment), expected_html)

    def test_clean_html_markers_without_html_markers(self):
        """Test the function with HTML but without markdown markers"""
        html_content = """<!DOCTYPE html>
<html>
<head>
    <title>No Markers</title>
</head>
<body>
    <h1>No Markdown Markers</h1>
</body>
</html>"""
        self.assertEqual(clean_html_markers(html_content), html_content)


if __name__ == "__main__":
    unittest.main()
