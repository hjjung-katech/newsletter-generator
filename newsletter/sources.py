"""
Newsletter Generator - News Sources
이 모듈은 다양한 뉴스 소스를 통합하여 뉴스 기사를 수집하는 기능을 제공합니다.
"""

import json
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import feedparser
import requests
from bs4 import BeautifulSoup
from rich.console import Console

from . import config
from .date_utils import parse_date_string, standardize_date

console = Console()


class NewsSource:
    """기본 뉴스 소스 클래스 - 모든 소스의 기본 인터페이스를 정의"""

    def __init__(self, name: str):
        self.name = name

    def fetch_news(
        self, keywords: List[str], num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """키워드 기반으로 뉴스 기사를 검색하는 메서드"""
        raise NotImplementedError("Subclasses must implement fetch_news method")

    def get_source_name(self) -> str:
        """소스 이름을 반환"""
        return self.name

    def _standardize_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """각 소스별 기사 형식을 표준화"""
        # 날짜 정보 추출
        raw_date = article.get(
            "date",
            article.get("publishedAt", article.get("published", "날짜 없음")),
        )

        # 원래 날짜 형식 저장 (디버깅 및 데이터 보존 목적)
        original_date = raw_date

        # 날짜 형식 표준화 (YYYY-MM-DD)
        standardized_date = standardize_date(raw_date)

        # 반환할 기사 정보
        return {
            "title": article.get("title", "제목 없음"),
            "url": article.get("url", article.get("link", "#")),
            "link": article.get("link", article.get("url", "#")),
            "content": article.get(
                "snippet",
                article.get("description", article.get("content", "내용 없음")),
            ),
            "source": article.get("source", self.name),
            "date": standardized_date,  # 표준화된 날짜 사용
            "original_date": original_date,  # 원래 날짜 형식 보존
            "source_type": self.name,  # 어떤 소스에서 수집되었는지 추적
        }


class SerperAPISource(NewsSource):
    """Serper.dev API를 사용하여 뉴스 기사를 검색하는 소스"""

    def __init__(self):
        super().__init__("SerperAPI")
        self.api_key = config.SERPER_API_KEY

    def fetch_news(
        self, keywords: List[str], num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Serper.dev API를 통해 뉴스 기사를 검색"""
        if not self.api_key:
            console.print(
                "[bold red]Error: SERPER_API_KEY not found. Please set it in the .env file.[/bold red]"
            )
            return []

        all_articles = []
        keyword_article_counts = {}

        url = "https://google.serper.dev/news"

        for keyword in keywords:
            console.print(
                f"[cyan]Searching articles for keyword: '{keyword}' using Serper.dev[/cyan]"
            )
            payload = json.dumps(
                {"q": keyword, "gl": "kr", "num": num_results}  # 한국 지역 결과
            )

            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json",
            }

            try:
                response = requests.request("POST", url, headers=headers, data=payload)
                response.raise_for_status()

                results = response.json()
                articles_for_keyword = []

                # 여러 가능한 결과 컨테이너를 확인하여 데이터 추출
                containers = []

                # 1. 'news' 키 확인 (뉴스 엔드포인트의 주요 응답 형식)
                if "news" in results:
                    containers.extend(results["news"])

                # 2. 'topStories' 키도 확인 (일부 응답에 존재할 수 있음)
                if "topStories" in results:
                    containers.extend(results["topStories"])

                # 3. 'organic' 키 확인 (fallback - 일반 검색 결과)
                if "organic" in results and not containers:
                    containers.extend(results["organic"])

                # 각 아이템 처리
                for item in containers[: min(num_results, len(containers))]:
                    article = {
                        "title": item.get("title", "제목 없음"),
                        "url": item.get("link", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet")
                        or item.get("description", "내용 없음"),
                        "source": item.get("source", "출처 없음"),
                        "date": item.get("date")
                        or item.get("publishedAt")
                        or "날짜 없음",
                    }
                    articles_for_keyword.append(self._standardize_article(article))

                num_found = len(articles_for_keyword)
                keyword_article_counts[keyword] = num_found
                console.print(
                    f"[green]Found {num_found} articles for keyword: '{keyword}' from Serper.dev[/green]"
                )
                all_articles.extend(articles_for_keyword)

            except requests.exceptions.RequestException as e:
                console.print(
                    f"[bold red]Error fetching articles for keyword '{keyword}' from Serper.dev: {e}[/bold red]"
                )
            except json.JSONDecodeError:
                console.print(
                    f"[bold red]Error decoding JSON response for keyword '{keyword}' from Serper.dev.[/bold red]"
                )

        return all_articles


class RSSFeedSource(NewsSource):
    """RSS 피드를 사용하여 뉴스 기사를 수집하는 소스"""

    def __init__(self, name: str, feed_urls: List[str]):
        super().__init__(name)
        self.feed_urls = feed_urls

    def fetch_news(
        self, keywords: List[str], num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """RSS 피드에서 뉴스 기사를 수집하고 키워드로 필터링"""
        all_articles = []
        keyword_article_counts = {keyword: 0 for keyword in keywords}

        for feed_url in self.feed_urls:
            try:
                console.print(f"[cyan]Fetching RSS feed: {feed_url}[/cyan]")
                feed = feedparser.parse(feed_url)

                if getattr(feed, "status", 200) != 200:
                    console.print(
                        f"[yellow]Warning: Could not fetch RSS feed {feed_url}, status: {getattr(feed, 'status', 'unknown')}[/yellow]"
                    )
                    continue

                console.print(
                    f"[green]Successfully fetched RSS feed: {feed_url} - {len(feed.entries)} entries[/green]"
                )

                matched_entries = []

                for entry in feed.entries:
                    # entry가 dict 또는 객체일 수 있으므로 get과 getattr 모두 사용
                    title = (
                        entry.get("title", "").lower()
                        if isinstance(entry, dict)
                        else getattr(entry, "title", "").lower()
                    )
                    description = (
                        entry.get("description", "").lower()
                        if isinstance(entry, dict)
                        else getattr(entry, "description", "").lower()
                    )
                    content = (
                        entry.get("content", None)
                        if isinstance(entry, dict)
                        else getattr(entry, "content", None)
                    )
                    content_value = ""
                    if content:
                        if isinstance(content, list):
                            content_value = (
                                content[0].get("value", "")
                                if isinstance(content[0], dict)
                                else str(content[0])
                            )
                        else:
                            content_value = str(content)
                    content_value = content_value.lower()

                    # 키워드 매칭 여부 확인 (title, description, content_value 중 하나라도 포함되면 True)
                    matched_keyword = False
                    for keyword in keywords:
                        keyword_lower = keyword.lower()
                        # 영문/숫자 키워드는 단어 경계, 한글 등은 단순 포함
                        if re.fullmatch(r"[a-zA-Z0-9]+", keyword_lower):
                            keyword_pattern = r"\b" + re.escape(keyword_lower) + r"\b"
                            match = (
                                re.search(keyword_pattern, title)
                                or re.search(keyword_pattern, description)
                                or re.search(keyword_pattern, content_value)
                            )
                        else:
                            match = (
                                keyword_lower in title
                                or keyword_lower in description
                                or keyword_lower in content_value
                            )
                        if match:
                            matched_keyword = True
                            keyword_article_counts[keyword] += 1
                            break

                    if matched_keyword:
                        article = {
                            "title": entry.get(
                                "title", getattr(entry, "title", "제목 없음")
                            ),
                            "url": entry.get("link", getattr(entry, "link", "#")),
                            "link": entry.get("link", getattr(entry, "link", "#")),
                            "snippet": entry.get(
                                "description",
                                getattr(entry, "description", "내용 없음"),
                            ),
                            "source": (
                                getattr(feed.feed, "title", self.name)
                                if hasattr(feed, "feed")
                                else self.name
                            ),
                            "date": self._parse_rss_date(entry),
                        }
                        matched_entries.append(article)

                # 각 피드에서 최대 num_results개의 기사만 선택
                for article in matched_entries[:num_results]:
                    all_articles.append(self._standardize_article(article))

                console.print(
                    f"[green]Found {len(matched_entries)} matching articles from {feed_url}[/green]"
                )

            except Exception as e:
                console.print(
                    f"[bold red]Error fetching RSS feed {feed_url}: {e}[/bold red]"
                )

        # 키워드별 수집한 기사 수 출력
        for keyword, count in keyword_article_counts.items():
            console.print(
                f"[cyan]- '{keyword}': {count} articles from RSS feeds[/cyan]"
            )

        return all_articles

    def _parse_rss_date(self, entry) -> str:
        """RSS 피드 항목의 날짜 정보를 파싱"""
        # feedparser가 자동으로 파싱한 published_parsed 필드 사용
        date_field = None
        # dict 타입 지원
        if isinstance(entry, dict):
            for field in ["published_parsed", "updated_parsed", "created_parsed"]:
                if field in entry and entry[field]:
                    date_field = entry[field]
                    break
            if date_field:
                try:
                    dt = datetime(*date_field[:6])
                    return dt.strftime("%Y-%m-%d")
                except Exception:
                    pass
            for field in ["published", "updated", "created"]:
                if field in entry and entry[field]:
                    return entry[field]
        else:
            for field in ["published_parsed", "updated_parsed", "created_parsed"]:
                if hasattr(entry, field) and getattr(entry, field):
                    date_field = getattr(entry, field)
                    break
            if date_field:
                try:
                    dt = datetime(*date_field[:6])
                    return dt.strftime("%Y-%m-%d")
                except Exception:
                    pass
            for field in ["published", "updated", "created"]:
                if hasattr(entry, field) and getattr(entry, field):
                    return getattr(entry, field)
        return "날짜 없음"


class NaverNewsAPISource(NewsSource):
    """네이버 뉴스 검색 API를 사용하여 뉴스 기사를 검색하는 소스"""

    def __init__(self):
        super().__init__("NaverNewsAPI")
        self.client_id = config.NAVER_CLIENT_ID
        self.client_secret = config.NAVER_CLIENT_SECRET

    def fetch_news(
        self, keywords: List[str], num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """네이버 뉴스 API를 통해 뉴스 기사를 검색"""
        if not self.client_id or not self.client_secret:
            console.print(
                "[bold yellow]Warning: Naver API credentials not found. Skipping Naver news source.[/bold yellow]"
            )
            return []

        all_articles = []
        keyword_article_counts = {}

        for keyword in keywords:
            console.print(
                f"[cyan]Searching articles for keyword: '{keyword}' using Naver News API[/cyan]"
            )

            url = f"https://openapi.naver.com/v1/search/news.json?query={keyword}&display={num_results}&sort=date"
            headers = {
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret,
            }

            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()

                results = response.json()
                articles_for_keyword = []

                if "items" in results and results["items"]:
                    for item in results["items"]:
                        # HTML 태그 제거
                        title = BeautifulSoup(
                            item.get("title", "제목 없음"), "html.parser"
                        ).get_text()
                        description = BeautifulSoup(
                            item.get("description", "내용 없음"), "html.parser"
                        ).get_text()

                        article = {
                            "title": title,
                            "url": item.get("link", "#"),
                            "link": item.get("link", "#"),
                            "snippet": description,
                            "source": item.get("originallink", "네이버 뉴스"),
                            "date": item.get("pubDate", "날짜 없음"),
                        }
                        articles_for_keyword.append(self._standardize_article(article))

                num_found = len(articles_for_keyword)
                keyword_article_counts[keyword] = num_found
                console.print(
                    f"[green]Found {num_found} articles for keyword: '{keyword}' from Naver News API[/green]"
                )
                all_articles.extend(articles_for_keyword)

            except requests.exceptions.RequestException as e:
                console.print(
                    f"[bold red]Error fetching articles for keyword '{keyword}' from Naver News API: {e}[/bold red]"
                )

        return all_articles


class NewsSourceManager:
    """여러 뉴스 소스를 관리하고 통합 결과를 제공하는 관리자 클래스"""

    def __init__(self):
        self.sources = []
        # 주요 언론사 티어 설정
        self.major_news_sources = {
            # 티어 1: 최우선 포함 주요 언론사
            "tier1": [
                "조선일보",
                "중앙일보",
                "동아일보",
                "한국일보",
                "한겨레",
                "경향신문",
                "매일경제",
                "한국경제",
                "서울경제",
                "연합뉴스",
                "YTN",
                "KBS",
                "MBC",
                "SBS",
                "Bloomberg",
                "Reuters",
                "Wall Street Journal",
                "Financial Times",
                "The Economist",
                "TechCrunch",
                "Wired",
            ],
            # 티어 2: 보조 언론사
            "tier2": [
                "뉴시스",
                "뉴스1",
                "아시아경제",
                "아주경제",
                "이데일리",
                "머니투데이",
                "디지털타임스",
                "전자신문",
                "IT조선",
                "ZDNet Korea",
                "디지털데일리",
            ],
        }

    def add_source(self, source: NewsSource) -> None:
        """뉴스 소스 추가"""
        self.sources.append(source)

    def fetch_all_sources(
        self, keywords: List[str], num_results_per_source: int = 10
    ) -> List[Dict[str, Any]]:
        """모든 소스에서 뉴스 기사 수집"""
        if isinstance(keywords, str):
            keywords_list = [k.strip() for k in keywords.split(",")]
        else:
            keywords_list = keywords

        console.print(
            f"[bold green]Fetching news for keywords: {keywords_list}[/bold green]"
        )

        all_articles = []
        for source in self.sources:
            console.print(
                f"[bold]Fetching news from {source.get_source_name()}...[/bold]"
            )
            articles = source.fetch_news(keywords_list, num_results_per_source)
            all_articles.extend(articles)

        console.print(
            f"[bold green]Total articles collected from all sources: {len(all_articles)}[/bold green]"
        )
        return all_articles

    def remove_duplicates(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복된 기사 제거"""
        unique_articles = []
        seen_urls = set()
        seen_titles = set()

        for article in articles:
            url = article.get("url", "")
            title = article.get("title", "")

            # URL과 제목이 모두 없는 경우는 스킵
            if not url and not title:
                continue

            # URL 기반 중복 확인
            if url and url in seen_urls:
                continue

            # 제목 기반 중복 확인 (URL이 다르더라도)
            if title and title in seen_titles:
                continue

            if url:
                seen_urls.add(url)
            if title:
                seen_titles.add(title)

            unique_articles.append(article)

        console.print(
            f"[cyan]Removed {len(articles) - len(unique_articles)} duplicate articles[/cyan]"
        )
        return unique_articles

    def filter_by_major_sources(
        self, articles: List[Dict[str, Any]], max_per_topic: int = 5
    ) -> List[Dict[str, Any]]:
        """주요 언론사 기사 우선 필터링

        Args:
            articles: 필터링할 기사 목록
            max_per_topic: 각 주제별 최대 기사 수

        Returns:
            필터링된 기사 목록
        """
        # 언론사 소스별로 분류
        tier1_articles = []
        tier2_articles = []
        other_articles = []

        for article in articles:
            source = article.get("source", "")

            # 소스 이름 정규화 (대소문자 무시, 공백 제거)
            source_norm = source.lower().strip()

            # 티어에 따라 분류
            if any(
                major_source.lower() in source_norm
                for major_source in self.major_news_sources["tier1"]
            ):
                tier1_articles.append(article)
            elif any(
                major_source.lower() in source_norm
                for major_source in self.major_news_sources["tier2"]
            ):
                tier2_articles.append(article)
            else:
                other_articles.append(article)

        # 티어에 따라 기사 선택 (티어1 우선, 그 다음 티어2, 마지막에 기타)
        filtered_articles = []

        # 먼저 티어1 기사 추가
        filtered_articles.extend(tier1_articles[:max_per_topic])

        # 아직 공간이 남으면 티어2 기사 추가
        remaining_slots = max_per_topic - len(filtered_articles)
        if remaining_slots > 0:
            filtered_articles.extend(tier2_articles[:remaining_slots])

        # 그래도 남으면 기타 기사 추가
        remaining_slots = max_per_topic - len(filtered_articles)
        if remaining_slots > 0:
            filtered_articles.extend(other_articles[:remaining_slots])

        console.print(
            f"[cyan]Filtered articles by major sources: {len(filtered_articles)} selected from {len(articles)} total[/cyan]"
        )

        return filtered_articles

    def group_articles_by_keywords(
        self, articles: List[Dict[str, Any]], keywords: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """키워드별로 기사 그룹화

        Args:
            articles: 그룹화할 기사 목록
            keywords: 키워드 리스트

        Returns:
            키워드별 기사 그룹 (키워드: 기사 목록)
        """
        # 키워드별 빈 목록 초기화
        grouped_articles = {keyword: [] for keyword in keywords}

        # 각 기사에 대해 일치하는 모든 키워드 찾기
        for article in articles:
            title = article.get("title", "").lower()
            content = article.get("content", "").lower()

            for keyword in keywords:
                keyword_lower = keyword.lower()

                # 영문/숫자 키워드는 단어 경계, 한글 등은 단순 포함
                if re.fullmatch(r"[a-zA-Z0-9]+", keyword_lower):
                    keyword_pattern = r"\b" + re.escape(keyword_lower) + r"\b"
                    if re.search(keyword_pattern, title) or re.search(
                        keyword_pattern, content
                    ):
                        grouped_articles[keyword].append(article)
                else:
                    if keyword_lower in title or keyword_lower in content:
                        grouped_articles[keyword].append(article)

        # 각 키워드 그룹에서 중복 제거
        for keyword in grouped_articles:
            grouped_articles[keyword] = self.remove_duplicates(
                grouped_articles[keyword]
            )
            console.print(
                f"[green]Grouped {len(grouped_articles[keyword])} articles for keyword: '{keyword}'[/green]"
            )

        return grouped_articles


# 기본 뉴스 소스 설정 함수
def configure_default_sources() -> NewsSourceManager:
    """기본 뉴스 소스를 구성"""
    manager = NewsSourceManager()

    # Serper API 소스 추가 (항상 추가)
    if config.SERPER_API_KEY:
        manager.add_source(SerperAPISource())

    # 네이버 뉴스 API 소스 추가 (자격 증명이 있는 경우)
    if hasattr(config, "NAVER_CLIENT_ID") and hasattr(config, "NAVER_CLIENT_SECRET"):
        if config.NAVER_CLIENT_ID and config.NAVER_CLIENT_SECRET:
            manager.add_source(NaverNewsAPISource())

    # 기본 RSS 피드 추가
    default_feeds = [
        # 국내 주요 언론사 RSS 피드
        "https://www.yonhapnewstv.co.kr/feed/",  # 연합뉴스TV
        "https://www.hani.co.kr/rss/",  # 한겨레
        "https://rss.donga.com/total.xml",  # 동아일보
        "https://www.khan.co.kr/rss/rssdata/total_news.xml",  # 경향신문
    ]

    # 환경 변수에서 추가 RSS 피드 URL 가져오기
    additional_feeds = os.environ.get("ADDITIONAL_RSS_FEEDS", "").split(",")
    feeds = default_feeds + [feed for feed in additional_feeds if feed.strip()]

    if feeds:
        manager.add_source(RSSFeedSource("DefaultRSSFeeds", feeds))

    return manager
