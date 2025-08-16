import os
import sys

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
import unittest
from unittest.mock import MagicMock, Mock, patch

import feedparser

from newsletter.sources import (
    NaverNewsAPISource,
    NewsSource,
    NewsSourceManager,
    RSSFeedSource,
    SerperAPISource,
    configure_default_sources,
)


class TestNewsSource(unittest.TestCase):
    def test_base_news_source(self):
        """기본 NewsSource 클래스 테스트"""
        source = NewsSource("TestSource")
        self.assertEqual(source.get_source_name(), "TestSource")

        # 추상 메서드 호출 시 NotImplementedError 발생 확인
        with self.assertRaises(NotImplementedError):
            source.fetch_news(["test"])

    def test_standardize_article(self):
        """기사 표준화 기능 테스트"""
        source = NewsSource("TestSource")

        # 다양한 형태의 기사 데이터 테스트
        article1 = {
            "title": "Test Title",
            "url": "http://test.com",
            "snippet": "Test snippet",
        }

        article2 = {
            "title": "Test Title 2",
            "link": "http://test2.com",
            "description": "Test description",
        }

        std_article1 = source._standardize_article(article1)
        std_article2 = source._standardize_article(article2)

        # 표준화된 필드 확인
        self.assertEqual(std_article1["title"], "Test Title")
        self.assertEqual(std_article1["url"], "http://test.com")
        self.assertEqual(std_article1["link"], "http://test.com")
        self.assertEqual(std_article1["content"], "Test snippet")
        self.assertEqual(std_article1["source"], "TestSource")
        self.assertEqual(std_article1["source_type"], "TestSource")

        self.assertEqual(std_article2["title"], "Test Title 2")
        self.assertEqual(std_article2["url"], "http://test2.com")
        self.assertEqual(std_article2["link"], "http://test2.com")
        self.assertEqual(std_article2["content"], "Test description")


class TestSerperAPISource(unittest.TestCase):
    @patch("newsletter.sources.config.SERPER_API_KEY", "fake_api_key")
    @patch("newsletter.sources.fetch_url_content")
    def test_fetch_news(self, mock_fetch_url_content):
        """SerperAPISource의 fetch_news 메서드 테스트"""
        # API 응답 JSON 문자열 설정
        api_response_json = """{
            "news": [
                {
                    "title": "Test News Article",
                    "link": "http://test.com/news1",
                    "snippet": "This is a test snippet",
                    "source": "Test Source",
                    "date": "2023-05-20"
                },
                {
                    "title": "Another Test Article",
                    "link": "http://test.com/news2",
                    "snippet": "Another test snippet",
                    "source": "Another Source",
                    "publishedAt": "2023-05-19"
                }
            ]
        }"""
        mock_fetch_url_content.return_value = api_response_json

        # 소스 객체 생성 및 테스트
        source = SerperAPISource()
        articles = source.fetch_news(["test keyword"], 10)

        # API 호출 확인
        mock_fetch_url_content.assert_called_once()

        # 결과 확인
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0]["title"], "Test News Article")
        self.assertEqual(articles[0]["url"], "http://test.com/news1")
        self.assertEqual(articles[0]["source_type"], "SerperAPI")

        self.assertEqual(articles[1]["title"], "Another Test Article")
        self.assertEqual(articles[1]["date"], "2023-05-19")

    @patch("newsletter.sources.config.SERPER_API_KEY", None)
    def test_no_api_key(self):
        """API 키가 없는 경우 테스트"""
        source = SerperAPISource()
        articles = source.fetch_news(["test"])
        self.assertEqual(len(articles), 0)


class TestRSSFeedSource(unittest.TestCase):
    @patch("newsletter.sources.fetch_url_content")
    def test_fetch_news(self, mock_fetch_url_content):
        """RSSFeedSource의 fetch_news 메서드 테스트"""
        # RSS 피드 XML 문자열 설정
        rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test RSS Feed</title>
                <item>
                    <title>Keyword Test Article</title>
                    <link>http://rss.test/article1</link>
                    <description>This is an article containing the keyword</description>
                    <pubDate>Tue, 20 May 2023 12:00:00 +0000</pubDate>
                </item>
                <item>
                    <title>Unrelated Article</title>
                    <link>http://rss.test/article2</link>
                    <description>This article doesn\'t contain any keywords</description>
                    <pubDate>Mon, 19 May 2023 10:00:00 +0000</pubDate>
                </item>
            </channel>
        </rss>"""

        mock_fetch_url_content.return_value = rss_xml

        # 소스 객체 생성 및 테스트
        source = RSSFeedSource("TestRSS", ["http://test.com/rss"])
        articles = source.fetch_news(["keyword"], 10)

        # 피드 가져오기 호출 확인
        mock_fetch_url_content.assert_called_once()

        # 결과 확인 - 키워드가 포함된 첫 번째 항목만 반환되어야 함
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["title"], "Keyword Test Article")
        self.assertEqual(articles[0]["url"], "http://rss.test/article1")
        self.assertEqual(articles[0]["source"], "Test RSS Feed")
        self.assertEqual(articles[0]["date"], "2023-05-20")

    @patch("newsletter.sources.feedparser.parse")
    def test_feed_error(self, mock_parse):
        """RSS 피드 오류 처리 테스트"""
        # 오류 상태 설정
        mock_feed = MagicMock()
        mock_feed.status = 404
        mock_parse.return_value = mock_feed

        source = RSSFeedSource("TestRSS", ["http://test.com/rss"])
        articles = source.fetch_news(["keyword"], 10)

        # 오류가 있더라도 빈 목록 반환
        self.assertEqual(len(articles), 0)


class TestNaverNewsAPISource(unittest.TestCase):
    @patch("newsletter.sources.config.NAVER_CLIENT_ID", "fake_client_id")
    @patch("newsletter.sources.config.NAVER_CLIENT_SECRET", "fake_client_secret")
    @patch("newsletter.sources.fetch_url_content")
    def test_fetch_news(self, mock_fetch_url_content):
        """NaverNewsAPISource의 fetch_news 메서드 테스트"""
        # API 응답 JSON 문자열 설정
        api_response_json = """{
            "items": [
                {
                    "title": "Test <b>Naver</b> Article",
                    "link": "http://naver.com/news1",
                    "description": "This is a <b>test</b> description",
                    "originallink": "http://original.com/news1",
                    "pubDate": "Tue, 20 May 2023 12:00:00 +0900"
                },
                {
                    "title": "Another <b>Naver</b> Article",
                    "link": "http://naver.com/news2",
                    "description": "Another <b>test</b> description",
                    "originallink": "http://original.com/news2",
                    "pubDate": "Mon, 19 May 2023 10:00:00 +0900"
                }
            ]
        }"""
        mock_fetch_url_content.return_value = api_response_json

        # 소스 객체 생성 및 테스트
        source = NaverNewsAPISource()
        articles = source.fetch_news(["네이버"], 10)

        # API 호출 확인
        mock_fetch_url_content.assert_called_once()

        # 결과 확인 - HTML 태그가 제거되어야 함
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0]["title"], "Test Naver Article")
        self.assertEqual(articles[0]["url"], "http://naver.com/news1")
        self.assertEqual(articles[0]["content"], "This is a test description")
        self.assertEqual(articles[0]["source"], "http://original.com/news1")
        self.assertEqual(articles[0]["source_type"], "NaverNewsAPI")

    @patch("newsletter.sources.config.NAVER_CLIENT_ID", None)
    @patch("newsletter.sources.config.NAVER_CLIENT_SECRET", None)
    def test_no_credentials(self):
        """API 자격 증명이 없는 경우 테스트"""
        source = NaverNewsAPISource()
        articles = source.fetch_news(["test"])
        self.assertEqual(len(articles), 0)


class TestNewsSourceManager(unittest.TestCase):
    def test_add_source(self):
        """소스 추가 테스트"""
        manager = NewsSourceManager()
        source1 = NewsSource("Source1")
        source2 = NewsSource("Source2")

        manager.add_source(source1)
        manager.add_source(source2)

        self.assertEqual(len(manager.sources), 2)
        self.assertEqual(manager.sources[0].get_source_name(), "Source1")
        self.assertEqual(manager.sources[1].get_source_name(), "Source2")

    def test_fetch_all_sources(self):
        """모든 소스에서 뉴스 수집 테스트"""
        manager = NewsSourceManager()

        # 모의 소스 생성
        source1 = MagicMock()
        source1.get_source_name.return_value = "MockSource1"
        source1.fetch_news.return_value = [
            {"title": "Article 1", "url": "http://test.com/1"}
        ]

        source2 = MagicMock()
        source2.get_source_name.return_value = "MockSource2"
        source2.fetch_news.return_value = [
            {"title": "Article 2", "url": "http://test.com/2"}
        ]

        manager.add_source(source1)
        manager.add_source(source2)

        # 문자열 키워드로 테스트
        articles = manager.fetch_all_sources("test,keyword", 5)

        # 각 소스의 fetch_news 호출 확인
        source1.fetch_news.assert_called_once()
        source2.fetch_news.assert_called_once()

        # 결과 확인
        self.assertEqual(len(articles), 2)

    def test_remove_duplicates(self):
        """중복 기사 제거 테스트"""
        manager = NewsSourceManager()

        # 중복된 URL과 제목을 가진 기사 목록
        articles = [
            {"title": "Title 1", "url": "http://test.com/1"},
            {"title": "Title 1", "url": "http://test.com/2"},  # 제목 중복
            {"title": "Title 2", "url": "http://test.com/1"},  # URL 중복
            {"title": "Title 3", "url": "http://test.com/3"},  # 중복 없음
            {"title": "", "url": ""},  # 빈 항목
        ]

        unique_articles = manager.remove_duplicates(articles)

        # URL 또는 제목이 중복되지 않은 기사만 남아야 함
        self.assertEqual(len(unique_articles), 2)
        self.assertEqual(unique_articles[0]["url"], "http://test.com/1")
        self.assertEqual(unique_articles[1]["url"], "http://test.com/3")


class TestConfigureDefaultSources(unittest.TestCase):
    @patch("newsletter.sources.config.SERPER_API_KEY", "fake_api_key")
    @patch("newsletter.sources.config.NAVER_CLIENT_ID", "fake_client_id")
    @patch("newsletter.sources.config.NAVER_CLIENT_SECRET", "fake_client_secret")
    def test_configure_all_sources(self):
        """모든 소스가 구성된 경우 테스트"""
        # 환경 변수 설정 (테스트용)
        with patch.dict(
            os.environ,
            {"ADDITIONAL_RSS_FEEDS": "http://test.com/custom1,http://test.com/custom2"},
        ):
            manager = configure_default_sources()

            # 기본 소스 3개가 모두 구성되어야 함
            self.assertEqual(len(manager.sources), 3)

            # 소스 유형 확인
            # self.assertIsInstance(manager.sources[0], SerperAPISource)
            # self.assertIsInstance(manager.sources[1], NaverNewsAPISource)
            # self.assertIsInstance(manager.sources[2], RSSFeedSource)

    @patch("newsletter.sources.config.SERPER_API_KEY", "fake_api_key")
    @patch("newsletter.sources.config.NAVER_CLIENT_ID", None)
    @patch("newsletter.sources.config.NAVER_CLIENT_SECRET", None)
    def test_configure_partial_sources(self):
        """일부 소스만 구성된 경우 테스트"""
        manager = configure_default_sources()

        # SerperAPI 소스와 RSS 소스만 구성되어야 함
        self.assertEqual(len(manager.sources), 2)
        # self.assertIsInstance(manager.sources[0], SerperAPISource)
        # self.assertIsInstance(manager.sources[1], RSSFeedSource)


if __name__ == "__main__":
    unittest.main()
