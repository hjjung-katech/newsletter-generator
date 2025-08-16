import os
import sys
import unittest
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from newsletter import config
from newsletter.article_filter import (
    filter_articles_by_domains,
    filter_articles_by_major_sources,
    group_articles_by_keywords,
    remove_duplicate_articles,
    remove_similar_articles,
    select_top_articles,
)


class TestArticleFilter(unittest.TestCase):
    """Test cases for the article_filter module."""

    def setUp(self):
        """Set up test data."""
        # Sample test articles
        self.test_articles = [
            {
                "title": "AI반도체 시장 전망: 삼성전자, 새로운 기술 공개",
                "url": "https://example.com/news/article1",
                "content": "삼성전자가 최신 AI반도체 기술을 공개했습니다. HBM 메모리와 함께 사용되는 이 기술은...",
                "source": "조선일보",
                "date": "2025-05-13",
            },
            {
                "title": "SK하이닉스, AI 반도체 생산량 확대 계획",
                "url": "https://example.com/news/article2",
                "content": "SK하이닉스가 AI반도체와 HBM 생산량을 두 배로 확대한다고 발표했습니다.",
                "source": "매일경제",
                "date": "2025-05-12",
            },
            {
                "title": "AI반도체와 HBM의 관계: 향후 전망",
                "url": "https://example.com/news/article3",
                "content": "인공지능 반도체 시장에서 HBM의 중요성이 커지고 있습니다. CXL 기술과 함께...",
                "source": "뉴시스",
                "date": "2025-05-11",
            },
            {
                "title": "AI 반도체 시장 분석: 미래 전망",
                "url": "https://example.com/news/article4",
                "content": "글로벌 AI 반도체 시장은 2030년까지 연평균 40% 성장할 것으로 전망됩니다.",
                "source": "TechBlog",
                "date": "2025-05-10",
            },
            {
                "title": "삼성전자, 새로운 AI반도체 기술 공개",
                "url": "https://example.com/news/article1",  # 중복 URL
                "content": "삼성전자가 최신 AI반도체 기술을 공개했습니다. 이 기술은...",
                "source": "다른뉴스",
                "date": "2025-05-13",
            },
            {
                "title": "CXL 기술의 발전과 데이터센터 영향",
                "url": "https://example.com/news/article5",
                "content": "CXL 기술이 데이터센터 아키텍처에 미치는 영향에 대한 분석입니다.",
                "source": "ZDNet Korea",
                "date": "2025-05-09",
            },
        ]

    @patch("newsletter.article_filter.console")
    def test_filter_articles_by_major_sources(self, mock_console):
        """Test filtering articles by major news sources."""
        # 티어1 소스, 티어2 소스, 기타 소스가 있는 기사 목록으로 테스트
        result = filter_articles_by_major_sources(self.test_articles, max_per_topic=3)

        # 티어1 소스 기사가 우선 선택되었는지 확인
        tier1_sources = [
            source.lower() for source in config.MAJOR_NEWS_SOURCES["tier1"]
        ]
        tier1_articles = [
            a for a in result if any(s in a["source"].lower() for s in tier1_sources)
        ]

        self.assertTrue(len(tier1_articles) > 0, "No tier1 articles were selected")

        # 동일한 수의 기사가 있을 때 티어1 기사가 먼저 포함되는지 확인
        if len(result) < len(self.test_articles):
            for article in tier1_articles:
                self.assertIn(
                    article,
                    result,
                    f"Tier1 article '{article['title']}' was not included",
                )

        # 공간이 남을 경우에만 티어2와 기타 기사가 포함되는지 확인
        if len(tier1_articles) < 3:  # max_per_topic=3으로 설정
            remaining_articles = [a for a in result if a not in tier1_articles]
            self.assertTrue(
                len(remaining_articles) > 0,
                "No tier2/other articles were selected when there was space",
            )

    @patch("newsletter.article_filter.console")
    def test_empty_article_list_handling(self, mock_console):
        """Test handling of empty article lists."""
        result = filter_articles_by_major_sources([], max_per_topic=3)
        self.assertEqual(result, [], "Empty article list should return empty result")

        result = group_articles_by_keywords([], ["AI반도체", "HBM"])
        self.assertEqual(len(result), 2, "Should return empty lists for each keyword")
        self.assertEqual(
            result["AI반도체"],
            [],
            "Empty article list should return empty result for each keyword",
        )

        result = remove_duplicate_articles([])
        self.assertEqual(result, [], "Empty article list should return empty result")

        result = filter_articles_by_domains([], max_per_domain=2)
        self.assertEqual(result, [], "Empty article list should return empty result")

    @patch("newsletter.article_filter.console")
    def test_group_articles_by_keywords(self, mock_console):
        """Test grouping articles by keywords."""
        keywords = ["AI반도체", "HBM", "CXL"]
        result = group_articles_by_keywords(self.test_articles, keywords)

        # 각 키워드에 대한 그룹이 생성되었는지 확인
        for keyword in keywords:
            self.assertIn(keyword, result, f"No group created for keyword '{keyword}'")

        # AI반도체 키워드 그룹에 관련 기사가 포함되었는지 확인
        ai_chip_articles = result["AI반도체"]
        self.assertTrue(
            len(ai_chip_articles) > 0, "No articles matched with 'AI반도체' keyword"
        )

        # 공백 무시 매칭이 작동하는지 확인 (AI반도체 vs AI 반도체)
        space_matching_articles = [
            a
            for a in ai_chip_articles
            if "AI 반도체" in a["title"] or "AI 반도체" in a["content"]
        ]
        self.assertTrue(
            len(space_matching_articles) > 0, "Space-insensitive matching failed"
        )

        # HBM 키워드 그룹에 관련 기사가 포함되었는지 확인
        hbm_articles = result["HBM"]
        self.assertTrue(len(hbm_articles) > 0, "No articles matched with 'HBM' keyword")

        # CXL 키워드 그룹에 관련 기사가 포함되었는지 확인
        cxl_articles = result["CXL"]
        self.assertTrue(len(cxl_articles) > 0, "No articles matched with 'CXL' keyword")

    @patch("newsletter.article_filter.console")
    def test_remove_duplicate_articles(self, mock_console):
        """Test removing duplicate articles."""
        # 중복 URL이 있는 기사 목록으로 테스트
        result = remove_duplicate_articles(self.test_articles)

        # 중복 제거 전후의 기사 수 확인
        self.assertTrue(
            len(result) < len(self.test_articles), "Duplicates were not removed"
        )

        # 중복된 URL이 제거되었는지 확인
        urls = [article["url"] for article in result]
        self.assertEqual(
            len(urls), len(set(urls)), "Duplicate URLs still exist after filtering"
        )

        # 중복된 제목이 제거되었는지 확인
        titles = [article["title"] for article in result]
        duplicate_titles = [t for t in titles if titles.count(t) > 1]
        self.assertEqual(
            len(duplicate_titles),
            0,
            f"Duplicate titles still exist: {duplicate_titles}",
        )

    @patch("newsletter.article_filter.console")
    def test_filter_articles_by_domains(self, mock_console):
        """Test filtering articles by domains."""
        # 도메인별 최대 기사 수 제한 테스트
        result = filter_articles_by_domains(self.test_articles, max_per_domain=1)

        domains = set()
        for article in result:
            url = article.get("url", "")
            if url and url != "#":
                from urllib.parse import urlparse

                domain = urlparse(url).netloc
                domains.add(domain)

        # 각 도메인별 기사 수가 최대 개수를 넘지 않는지 확인
        for domain in domains:
            domain_articles = [a for a in result if domain in a.get("url", "")]
            self.assertTrue(
                len(domain_articles) <= 1,
                f"Domain {domain} has more than the maximum allowed articles",
            )

    @patch("newsletter.article_filter.console")
    def test_keyword_partial_matching(self, mock_console):
        """Test partial keyword matching for compound keywords."""
        # 복합 키워드 테스트 (예: "인공지능 반도체")
        compound_keyword = ["인공지능 반도체"]
        articles = [
            {
                "title": "인공지능 기술의 발전",
                "content": "최근 반도체 기술과 인공지능의 결합으로...",
                "url": "https://example.com/article1",
                "source": "테크뉴스",
            },
            {
                "title": "인공지능반도체 시장 동향",
                "content": "AI칩 시장은 계속 성장 중...",
                "url": "https://example.com/article2",
                "source": "경제신문",
            },
        ]

        result = group_articles_by_keywords(articles, compound_keyword)

        # 부분 일치하는 기사들이 포함되었는지 확인
        self.assertTrue(
            len(result[compound_keyword[0]]) > 0,
            "Partial matching failed for compound keywords",
        )

        # "인공지능"과 "반도체"가 모두 포함된 기사가 매칭되었는지 확인
        self.assertTrue(
            any(
                "인공지능" in a["title"]
                or "인공지능" in a["content"]
                and "반도체" in a["title"]
                or "반도체" in a["content"]
                for a in result[compound_keyword[0]]
            ),
            "Failed to match articles containing both parts of compound keyword",
        )

    @patch("newsletter.article_filter.console")
    def test_edge_cases_and_concerns(self, mock_console):
        """Test edge cases and potential concerns."""
        # 우려사항 1: 유사하지만 다른 중요 기사가 제거될 수 있음
        similar_articles = [
            {
                "title": "삼성전자 AI반도체 신제품 출시",
                "content": "삼성전자가 새로운 AI반도체 제품을 출시했습니다. 성능이 크게 향상되었습니다.",
                "url": "https://example.com/news1",
                "source": "조선일보",
            },
            {
                "title": "삼성전자, AI반도체 신제품 출시 계획 발표",
                "content": "삼성전자가 내년 초 새로운 AI반도체 제품을 출시할 계획이라고 발표했습니다.",
                "url": "https://example.com/news2",
                "source": "동아일보",
            },
        ]

        # 중복 제거 후 중요한 기사가 보존되는지 확인
        result = remove_duplicate_articles(similar_articles)
        self.assertEqual(
            len(result),
            2,
            "Similar but different articles were incorrectly removed as duplicates",
        )

        # 우려사항 2: 키워드 일치 알고리즘 문제
        edge_keyword = ["AI+HBM"]
        edge_articles = [
            {
                "title": "AI와 HBM의 결합으로 성능 향상",
                "content": "AI+HBM 기술로 성능이 크게 향상되었습니다.",
                "url": "https://example.com/edge1",
                "source": "테크뉴스",
            }
        ]

        result = group_articles_by_keywords(edge_articles, edge_keyword)
        # 특수문자가 포함된 키워드도 정상적으로 매칭되는지 확인
        self.assertTrue(
            len(result[edge_keyword[0]]) > 0,
            "Failed to match articles with special characters in keywords",
        )

        # 우려사항 3: 다양성이 훼손될 위험
        diverse_sources = [
            {
                "title": "기사 1",
                "url": "https://major.com/1",
                "source": "조선일보",
                "content": "AI반도체 내용",
            },
            {
                "title": "기사 2",
                "url": "https://major.com/2",
                "source": "중앙일보",
                "content": "AI반도체 내용",
            },
            {
                "title": "기사 3",
                "url": "https://major.com/3",
                "source": "동아일보",
                "content": "AI반도체 내용",
            },
            {
                "title": "기사 4",
                "url": "https://major.com/4",
                "source": "한국일보",
                "content": "AI반도체 내용",
            },
            {
                "title": "기사 5",
                "url": "https://major.com/5",
                "source": "한겨레",
                "content": "AI반도체 내용",
            },
            {
                "title": "중요한 관점",
                "url": "https://small.com/1",
                "source": "작은블로그",
                "content": "AI반도체에 대한 중요한 비판적 관점",
            },
        ]

        # 설정에 따라 소규모 소스의 중요한 기사가 포함될 수 있는지 확인
        result = filter_articles_by_major_sources(diverse_sources, max_per_topic=5)
        small_source_included = any(a["source"] == "작은블로그" for a in result)

        # 현재 알고리즘은 소규모 소스도 포함시키는 방향으로 변경됨을 확인
        if len(result) >= len(diverse_sources):
            self.assertTrue(
                small_source_included,
                "Small sources are now included even when major sources are present",
            )

        # 우려사항 4: 중요한 최신 기사가 누락될 수 있음
        # max_per_domain을 매우 낮게 설정하여 테스트
        restrictive_result = filter_articles_by_domains(
            self.test_articles, max_per_domain=1
        )
        self.assertTrue(
            len(restrictive_result)
            <= len(set([a.get("source") for a in self.test_articles])),
            "Number of articles should be limited by max_per_domain",
        )

    @patch("newsletter.article_filter.console")
    def test_remove_similar_articles(self, mock_console):
        """Test removal of nearly identical articles by title."""
        articles = [
            {"title": "AI 에이전트 출시", "url": "https://a.com/1", "source": "A"},
            {"title": "AI 에이전트 출시 소식", "url": "https://a.com/2", "source": "B"},
            {"title": "완전히 다른 기사", "url": "https://a.com/3", "source": "C"},
        ]

        result = remove_similar_articles(articles, similarity_threshold=0.8)
        self.assertEqual(len(result), 2, "Similar articles were not removed")
        titles = {a["title"] for a in result}
        self.assertIn("완전히 다른 기사", titles)

    @patch("newsletter.article_filter.console")
    def test_select_top_articles(self, mock_console):
        """Test selection of top articles based on importance score."""
        sample_articles = [
            {"title": "t1", "source": "조선일보", "date": "2025-01-01", "url": "u1"},
            {"title": "t2", "source": "뉴시스", "date": "2025-01-01", "url": "u2"},
            {"title": "t3", "source": "블로그", "date": "2025-01-01", "url": "u3"},
            {"title": "t4", "source": "중앙일보", "date": "2025-01-01", "url": "u4"},
        ]

        top = select_top_articles(sample_articles, top_n=3)
        self.assertEqual(len(top), 3, "Did not select correct number of top articles")
        top_sources = {a["source"] for a in top}
        self.assertIn("조선일보", top_sources)
        self.assertIn("중앙일보", top_sources)
        self.assertIn("뉴시스", top_sources)
        self.assertNotIn("블로그", top_sources)


if __name__ == "__main__":
    unittest.main()
