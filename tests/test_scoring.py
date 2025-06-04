import unittest
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

from newsletter.scoring import load_scoring_weights_from_config, score_articles


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

        # config에서 가중치 로드
        weights = load_scoring_weights_from_config()

        ranked = score_articles(articles, "AI", top_n=2, weights=weights, llm=llm)
        self.assertEqual(len(ranked), 2)
        self.assertGreaterEqual(
            ranked[0]["priority_score"], ranked[1]["priority_score"]
        )
        for art in ranked:
            self.assertIn("scoring", art)

    def test_returns_all_when_top_none(self):
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
            AIMessage(content='{"relevance":3,"impact":3,"novelty":3}'),
        ]

        # config에서 가중치 로드
        weights = load_scoring_weights_from_config()

        ranked = score_articles(articles, "AI", top_n=None, weights=weights, llm=llm)
        self.assertEqual(len(ranked), 2)
        self.assertTrue(all("priority_score" in a for a in ranked))


if __name__ == "__main__":
    unittest.main()
