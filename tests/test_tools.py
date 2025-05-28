import unittest

from newsletter.tools import clean_html_markers


class TestTools(unittest.TestCase):

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

    def test_clean_html_markers_no_markers(self):
        html_no_markers = """<!DOCTYPE html>
<html>
<head>
    <title>Test</title>
</head>
<body>
    <h1>Hello</h1>
</body>
</html>"""
        expected_html = """<!DOCTYPE html>
<html>
<head>
    <title>Test</title>
</head>
<body>
    <h1>Hello</h1>
</body>
</html>"""
        self.assertEqual(clean_html_markers(html_no_markers), expected_html)

    def test_clean_html_markers_only_filepath_comment(self):
        html_only_comment = """<!-- filepath: c:\\path\\to\\file.html -->"""
        expected_html = """"""
        self.assertEqual(clean_html_markers(html_only_comment), expected_html)

    def test_clean_html_markers_empty_string(self):
        self.assertEqual(clean_html_markers(""), "")


if __name__ == "__main__":
    unittest.main()
