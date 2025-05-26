import sys
from types import SimpleNamespace

sys.modules.setdefault(
    "rich", SimpleNamespace(console=SimpleNamespace(Console=lambda *a, **k: None))
)
sys.modules.setdefault("rich.console", SimpleNamespace(Console=lambda *a, **k: None))

import unittest
from unittest.mock import patch
from newsletter.article_filter import group_articles_by_keywords


class TestArticleFilterSynonyms(unittest.TestCase):
    @patch("newsletter.article_filter.console")
    def test_synonym_matching(self, mock_console):
        articles = [
            {
                "title": "인공지능 반도체 시장 급성장",
                "content": "새로운 ai semiconductor 기술이 부상하고 있습니다",
                "url": "https://ex.com/1",
                "source": "테스트",
            }
        ]
        result = group_articles_by_keywords(articles, ["AI반도체"])
        self.assertEqual(len(result["AI반도체"]), 1)

    @patch("newsletter.article_filter.console")
    def test_context_based_matching(self, mock_console):
        articles = [
            {
                "title": "반도체 분야에서 인공지능 기술이 중요해지고 있다",
                "content": "기존 기술보다 5배 향상",
                "url": "https://ex.com/2",
                "source": "테스트",
            }
        ]
        result = group_articles_by_keywords(articles, ["AI반도체"])
        self.assertEqual(len(result["AI반도체"]), 1)


if __name__ == "__main__":
    unittest.main()
