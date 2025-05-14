"""
Test minimal version of clean_html_markers function
"""
import unittest
from tests.tools_minimal import clean_html_markers

class TestCleanHtmlMarkers(unittest.TestCase):
    """Test clean_html_markers function"""
    
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

    def test_clean_html_markers_with_filepath_comment_and_no_leading_newline_for_marker(
        self,
    ):
        html_with_comment = """<!-- filepath: c:\\path\\to\\file.html -->```html
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

    def test_clean_html_markers_without_filepath_comment(self):
        html_without_comment = """```html
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
        self.assertEqual(clean_html_markers(html_without_comment), expected_html)

if __name__ == "__main__":
    unittest.main() 