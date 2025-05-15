import unittest
from unittest.mock import patch, mock_open
from newsletter.chains import (
    CATEGORIZATION_PROMPT,
    SUMMARIZATION_PROMPT,
    COMPOSITION_PROMPT,
    HTML_TEMPLATE,
    load_html_template,
)


class TestChains(unittest.TestCase):

    def test_prompts_contain_appropriate_content(self):
        # 각 프롬프트에 적절한 내용이 포함되어 있는지 확인
        self.assertIn(
            "당신은 뉴스들을 분석하고 분류하는 전문 편집자입니다", CATEGORIZATION_PROMPT
        )
        self.assertIn("당신은 뉴스들을 분석하고 요약하여", SUMMARIZATION_PROMPT)
        self.assertIn(
            "당신은 뉴스들을 분석하고 요약하여, HTML 형식으로", COMPOSITION_PROMPT
        )

        # 공통 내용 확인
        self.assertIn(
            "독자 배경: 독자들은 한국 첨단산업의 R&D 전략기획단 소속",
            CATEGORIZATION_PROMPT,
        )
        self.assertIn(
            "독자 배경: 독자들은 한국 첨단산업의 R&D 전략기획단 소속",
            SUMMARIZATION_PROMPT,
        )
        self.assertIn(
            "독자 배경: 독자들은 한국 첨단산업의 R&D 전략기획단 소속",
            COMPOSITION_PROMPT,
        )

    def test_composition_prompt_references_html_template(self):
        # COMPOSITION_PROMPT에서 HTML 템플릿 관련 내용 확인
        self.assertIn("HTML 형식으로", COMPOSITION_PROMPT)

    @patch(
        "builtins.open", new_callable=mock_open, read_data="<p>Mocked HTML Content</p>"
    )
    def test_html_template_loading(self, mock_file):
        # HTML 템플릿을 다시 로드 (실제로는 mock_open이 반환하는 내용으로 대체됨)
        new_html_template = load_html_template()
        self.assertEqual(new_html_template, "<p>Mocked HTML Content</p>")


if __name__ == "__main__":
    unittest.main()
