import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from newsletter.template_manager import TemplateManager


class TestTemplateIntegration(unittest.TestCase):
    def setUp(self):
        # Create temp test directory
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.test_dir, "config")
        os.makedirs(self.config_dir, exist_ok=True)

        # Reset singleton instance
        TemplateManager._instance = None
        TemplateManager._config = None

        # Test config path
        self.config_path = os.path.join(self.config_dir, "template_config.json")

        # Create custom config
        custom_config = {
            "company": {"name": "Test Company"},
            "editor": {"signature": "Test Editorial Team"},
            "footer": {"disclaimer": "Test Disclaimer Text"},
            "audience": {"description": "Test Experts"},
        }

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(custom_config, f, ensure_ascii=False)

    def tearDown(self):
        # Clean up test directory
        shutil.rmtree(self.test_dir)

    def test_template_manager_integration(self):
        """Test template manager basic integration"""

        # Get template manager
        with patch("os.getcwd", return_value=self.test_dir):
            manager = TemplateManager.get_instance()

        # Verify config is loaded properly
        self.assertEqual(manager.get("company.name"), "Test Company")
        self.assertEqual(manager.get("editor.signature"), "Test Editorial Team")
        self.assertEqual(manager.get("footer.disclaimer"), "Test Disclaimer Text")
        self.assertEqual(manager.get("audience.description"), "Test Experts")

        # Test rendering function with template manager
        def simple_render():
            data = {}
            # Add company info from manager
            data["company_name"] = manager.get("company.name")
            data["footer_disclaimer"] = manager.get("footer.disclaimer")
            data["editor_signature"] = manager.get("editor.signature")
            data["audience_description"] = manager.get("audience.description")

            # Create sample output
            return f"""<html><body>
            <p>Company: {data['company_name']}</p>
            <p>Disclaimer: {data['footer_disclaimer']}</p>
            <p>Signature: {data['editor_signature']}</p>
            <p>Audience: {data['audience_description']}</p>
            </body></html>"""

        # Execute rendering
        result = simple_render()

        # Verify template values are in the result
        self.assertIn("Company: Test Company", result)
        self.assertIn("Signature: Test Editorial Team", result)
        self.assertIn("Disclaimer: Test Disclaimer Text", result)
        self.assertIn("Audience: Test Experts", result)


if __name__ == "__main__":
    unittest.main()
