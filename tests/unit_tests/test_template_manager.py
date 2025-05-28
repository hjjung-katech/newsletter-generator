import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from jinja2 import Environment, FileSystemLoader

from newsletter.template_manager import TemplateManager


class TestTemplateManager(unittest.TestCase):
    def setUp(self):
        # 테스트용 임시 디렉토리 생성
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.test_dir, "config")
        os.makedirs(self.config_dir, exist_ok=True)

        # 템플릿 매니저 클래스의 싱글톤 인스턴스 초기화
        TemplateManager._instance = None
        TemplateManager._config = None

        # 테스트용 설정 파일 경로
        self.config_path = os.path.join(self.config_dir, "template_config.json")

    def tearDown(self):
        # 테스트 디렉토리 정리
        shutil.rmtree(self.test_dir)

    def test_default_config_creation(self):
        """기본 설정 생성 테스트"""
        # 설정 파일이 없을 때 기본 설정이 생성되는지 테스트
        with patch("os.getcwd", return_value=self.test_dir):
            manager = TemplateManager.get_instance()
            self.assertTrue(os.path.exists(self.config_path))

            # 기본 설정값 확인
            self.assertEqual(manager.get("company.name"), "산업통상자원 R&D 전략기획단")
            self.assertEqual(
                manager.get("editor.signature"), "OSP 뉴스레터 편집팀 드림"
            )

    def test_custom_config_loading(self):
        """사용자 정의 설정 로드 테스트"""
        # 사용자 정의 설정 파일 생성
        custom_config = {
            "company": {"name": "테스트 회사"},
            "editor": {"signature": "테스트 편집팀"},
        }

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(custom_config, f, ensure_ascii=False)

        # 설정 로드
        manager = TemplateManager()
        manager.load_config(self.config_path)

        # 사용자 정의 설정값 확인
        self.assertEqual(manager.get("company.name"), "테스트 회사")
        self.assertEqual(manager.get("editor.signature"), "테스트 편집팀")

    def test_template_rendering_with_config(self):
        """Test if template settings are correctly applied to rendering"""
        # Create test template
        templates_dir = os.path.join(self.test_dir, "templates")
        os.makedirs(templates_dir, exist_ok=True)

        test_template = os.path.join(templates_dir, "test_template.html")
        with open(test_template, "w", encoding="utf-8") as f:
            f.write(
                """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Test Template</title>
            </head>
            <body>
                <h1>{{ newsletter_topic }}</h1>
                <p>Company: {{ company_name }}</p>
                <div class="footer">
                    <p>&copy; {{ generation_date.split('-')[0] }} {{ company_name }}. All rights reserved.</p>
                    <p>{{ footer_disclaimer }}</p>
                    <p>{{ editor_signature }}</p>
                </div>
            </body>
            </html>
            """
            )

        # User defined settings
        custom_config = {
            "company": {"name": "Test Company"},
            "editor": {"signature": "Test Editorial Team"},
            "footer": {"disclaimer": "Test Disclaimer Text"},
        }

        try:
            # Configure template manager
            manager = TemplateManager()
            manager.set_config(custom_config)
            print(f"Manager configured: {manager._config}")

            # Test template rendering function
            def render_with_template(data):
                # Add template configs to existing data
                template_data = data.copy()

                # Add company info
                template_data["company_name"] = manager.get("company.name")
                template_data["footer_disclaimer"] = manager.get("footer.disclaimer")
                template_data["editor_signature"] = manager.get("editor.signature")

                print(f"Rendering data: {template_data}")

                # Template rendering
                env = Environment(loader=FileSystemLoader(templates_dir))
                template = env.get_template("test_template.html")
                return template.render(**template_data)

            # Test data
            test_data = {
                "newsletter_topic": "Test Topic",
                "generation_date": "2025-05-16",
            }

            # Execute rendering
            rendered_html = render_with_template(test_data)
            print(f"Rendering result (first 100 chars): {rendered_html[:100]}...")

            # Verify results
            print(f"\nFull rendered HTML:\n{rendered_html}\n")
            self.assertIn("Company: Test Company", rendered_html)
            self.assertIn("Test Disclaimer Text", rendered_html)
            self.assertIn("Test Editorial Team", rendered_html)
            self.assertIn("&copy; 2025 Test Company", rendered_html)
        except Exception as e:
            import traceback

            traceback.print_exc()
            self.fail(f"Test failed: {e}")


if __name__ == "__main__":
    unittest.main()
