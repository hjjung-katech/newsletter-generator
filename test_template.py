#!/usr/bin/env python3
"""
Test script for improved newsletter templates
"""

import json
import os
from newsletter.compose import compose_newsletter


def test_templates():
    """Test both compact and detailed templates with improved settings"""

    # Load test data
    data_file = "output/intermediate_processing/render_data_langgraph_20250526_102426_스마트팩토리_최신_동향_외_9개_분야.json"

    if not os.path.exists(data_file):
        print(f"Data file not found: {data_file}")
        return

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    template_dir = "templates"

    # Test compact template
    print("Testing compact template...")
    try:
        compact_html = compose_newsletter(data, template_dir, "compact")

        output_file = "output/test_compact_improved.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(compact_html)
        print(f"Compact template test completed: {output_file}")
    except Exception as e:
        print(f"Error with compact template: {e}")

    # Test detailed template
    print("Testing detailed template...")
    try:
        detailed_html = compose_newsletter(data, template_dir, "detailed")

        output_file = "output/test_detailed_improved.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(detailed_html)
        print(f"Detailed template test completed: {output_file}")
    except Exception as e:
        print(f"Error with detailed template: {e}")


if __name__ == "__main__":
    test_templates()
