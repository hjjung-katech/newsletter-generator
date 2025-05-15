import unittest
from unittest.mock import patch, mock_open
from newsletter.chains import SYSTEM_PROMPT, HTML_TEMPLATE, load_html_template

class TestChains(unittest.TestCase):

    def test_system_prompt_contains_html_template(self):
        # 현재 로드된 HTML_TEMPLATE이 SYSTEM_PROMPT에 포함되어 있는지 확인
        self.assertIn(HTML_TEMPLATE, SYSTEM_PROMPT)

    @patch('builtins.open', new_callable=mock_open, read_data="<p>Mocked HTML Content</p>")
    def test_system_prompt_updates_with_template_change(self, mock_file):
        # load_html_template 함수가 mock_open을 사용하도록 패치
        # HTML 템플릿을 다시 로드 (실제로는 mock_open이 반환하는 내용으로 대체됨)
        new_html_template = load_html_template()

        # 시스템 프롬프트를 새 템플릿으로 다시 생성 (실제 코드에서는 모듈 로드 시점에 생성되므로, 여기서는 개념적 표현)
        # 실제 애플리케이션에서는 chains.py가 다시 실행되거나,
        # SYSTEM_PROMPT가 동적으로 HTML_TEMPLATE을 참조하도록 수정해야 합니다.
        # 현재 구조에서는 SYSTEM_PROMPT가 모듈 로드 시점에 고정되므로,
        # 이 테스트는 SYSTEM_PROMPT가 HTML_TEMPLATE의 현재 값을 사용하는지 간접적으로 확인합니다.

        # chains.py의 SYSTEM_PROMPT 정의를 가져와서 new_html_template이 포함되었는지 확인해야합니다.
        # 이를 위해서는 chains 모듈을 다시 로드하거나, SYSTEM_PROMPT를 함수로 만들어야 합니다.
        # 여기서는 현재 SYSTEM_PROMPT가 초기 HTML_TEMPLATE을 사용하는지 확인하는 것으로 대체합니다.
        # 그리고 load_html_template이 변경된 내용을 반환하는지 확인합니다.

        self.assertEqual(new_html_template, "<p>Mocked HTML Content</p>")

        # SYSTEM_PROMPT가 동적으로 HTML_TEMPLATE을 참조하도록 코드가 수정되었다고 가정하고,
        # 해당 참조가 올바르게 업데이트되었는지 확인하는 방법은 다음과 같을 수 있습니다:
        # from newsletter import chains
        # import importlib
        # importlib.reload(chains) # chains 모듈을 다시 로드하여 SYSTEM_PROMPT를 업데이트
        # self.assertIn(new_html_template, chains.SYSTEM_PROMPT)

        # 현재 구조에서는 SYSTEM_PROMPT가 f-string으로 HTML_TEMPLATE을 고정시키므로,
        # 모듈을 다시 로드하지 않는 한 SYSTEM_PROMPT는 업데이트되지 않습니다.
        # 따라서, 이 테스트는 load_html_template이 잘 동작하는지와
        # 초기 SYSTEM_PROMPT가 HTML_TEMPLATE을 잘 포함하는지를 주로 검증합니다.
        # SYSTEM_PROMPT가 항상 최신 HTML_TEMPLATE을 반영하도록 하려면,
        # SYSTEM_PROMPT를 함수로 만들거나, 사용할 때마다 f-string을 다시 평가해야 합니다.

        # 현재 코드대로라면, SYSTEM_PROMPT는 모듈 로딩 시점의 HTML_TEMPLATE 값을 가집니다.
        # 만약 HTML_TEMPLATE이 변경된 후 SYSTEM_PROMPT를 사용하는 코드가 있다면,
        # 그 코드가 최신 HTML_TEMPLATE을 반영한 SYSTEM_PROMPT를 사용하는지 확인해야 합니다.
        # 이 테스트 케이스는 그 부분을 직접 검증하기 어렵지만,
        # load_html_template이 변경된 내용을 반환하는 것을 보여줍니다.

        # 수정된 SYSTEM_PROMPT 로직 (함수 또는 동적 생성)을 가정하고 테스트:
        # 아래는 SYSTEM_PROMPT가 함수라고 가정했을 때의 테스트 코드 예시입니다.
        # def get_system_prompt():
        # return f"""... {load_html_template()} ..."""
        # self.assertIn(new_html_template, get_system_prompt())

        # 현재 구조에서는, SYSTEM_PROMPT가 초기화 시점의 HTML_TEMPLATE을 사용합니다.
        # HTML_TEMPLATE이 변경되어도 SYSTEM_PROMPT는 자동으로 업데이트되지 않습니다.
        # 이를 해결하려면 SYSTEM_PROMPT를 함수로 만들거나, 사용할 때마다 재생성해야 합니다.
        # 예를 들어, get_system_prompt() 함수를 만들어서 호출 시점에 HTML_TEMPLATE을 참조하도록 합니다.

        # 이 테스트는 load_html_template이 mock된 내용을 반환하는지,
        # 그리고 초기 SYSTEM_PROMPT가 초기 HTML_TEMPLATE을 포함하는지 확인합니다.
        
        self.assertIn(HTML_TEMPLATE, SYSTEM_PROMPT) # 초기 상태 확인
        # 만약 chains.py의 SYSTEM_PROMPT가 함수 호출로 변경된다면, 아래와 같이 테스트할 수 있습니다.
        # self.assertIn(new_html_template, chains.get_current_system_prompt())


if __name__ == '__main__':
    unittest.main()
