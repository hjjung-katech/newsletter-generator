import unittest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage

from newsletter.scoring import score_articles, DEFAULT_WEIGHTS


class TestScoring(unittest.TestCase):
    def test_score_articles_ranking(self):
        articles = [
            {
                "title": "A",
                "content": "text",
                "source": "조선일보",
                "date": "2025-01-01",
            },
            {"title": "B", "content": "text", "source": "블로그", "date": "2025-01-01"},
        ]

        llm = MagicMock()
        llm.invoke.side_effect = [
            AIMessage(content='{"relevance":5,"impact":5,"novelty":4}'),
            AIMessage(content='{"relevance":1,"impact":1,"novelty":1}'),
        ]

        ranked = score_articles(
            articles, "AI", top_n=2, weights=DEFAULT_WEIGHTS, llm=llm
        )
        self.assertEqual(len(ranked), 2)
        self.assertGreaterEqual(
            ranked[0]["priority_score"], ranked[1]["priority_score"]
        )


if __name__ == "__main__":
    unittest.main()
