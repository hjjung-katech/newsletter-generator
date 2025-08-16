"""
Newsletter Generator - News Sources
이 모듈은 다양한 뉴스 소스를 통합하여 뉴스 기사를 수집하는 기능을 제공합니다.
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, Final, List

import feedparser
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from rich.console import Console
from urllib3.util.retry import Retry

from . import config
from .date_utils import standardize_date
from .utils.error_handling import handle_exception
from .utils.logger import get_logger, show_collection_brief

# 로거 초기화
logger = get_logger()
console = Console()

# 상수 정의
TIMEOUT_SECONDS: Final[int] = 30
MAX_RETRIES: Final[int] = 3
BACKOFF_FACTOR: Final[float] = 0.3


def create_requests_session() -> requests.Session:
    """재시도 로직이 포함된 requests 세션 생성"""
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_url_content(
    url: str, headers: dict = None, method: str = "GET", data: dict = None
) -> str:
    """URL에서 컨텐츠를 안전하게 가져옴"""
    session = create_requests_session()
    try:
        if method.upper() == "POST":
            response = session.post(
                url, headers=headers, json=data, timeout=TIMEOUT_SECONDS
            )
        else:
            response = session.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"URL 요청 실패: {url}, 메소드: {method}, 에러: {str(e)}")
        raise


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

        # 기사 요약 내용 추출 (snippet 우선, 없으면 description, 없으면 content)
        snippet_content = article.get(
            "snippet",
            article.get("description", article.get("content", "내용 없음")),
        )

        # 반환할 기사 정보 (snippet과 content 모두 포함)
        return {
            "title": article.get("title", "제목 없음"),
            "url": article.get("url", article.get("link", "#")),
            "link": article.get("link", article.get("url", "#")),
            "snippet": snippet_content,  # 템플릿에서 사용하는 필드
            "content": snippet_content,  # 호환성을 위해 content도 유지
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
        """Serper API를 통해 뉴스 기사를 검색"""
        if not self.api_key:
            logger.warning("Serper API 키를 찾을 수 없습니다. Serper 소스를 건너뜁니다.")
            return []

        all_articles = []
        keyword_article_counts = {}

        for keyword in keywords:
            logger.info(f"Serper API를 사용하여 키워드 '{keyword}'에 대한 기사를 검색중입니다")

            url = "https://google.serper.dev/news"
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json",
            }
            payload = {
                "q": keyword,
                "num": num_results,
                "gl": "kr",  # 대한민국 검색 결과
                "hl": "ko",  # 한국어 인터페이스
            }

            try:
                content = fetch_url_content(
                    url, headers=headers, method="POST", data=payload
                )
                results = json.loads(content)
                articles_for_keyword = []

                if "news" in results:
                    for item in results["news"]:
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
                logger.info(
                    f"Serper API를 통해 키워드 '{keyword}'에 대해 {num_found}개의 기사를 찾았습니다"
                )
                all_articles.extend(articles_for_keyword)

            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Serper API를 통해 키워드 '{keyword}'에 대한 기사를 가져오는 중 오류가 발생했습니다: {e}"
                )
            except json.JSONDecodeError:
                logger.error(
                    f"Serper API를 통해 키워드 '{keyword}'에 대한 JSON 응답을 디코딩하는 중 오류가 발생했습니다."
                )

        # 키워드별 수집 결과 저장 (소스별 집계용)
        self._last_keyword_counts = keyword_article_counts
        return all_articles


class RSSFeedSource(NewsSource):
    """RSS 피드에서 뉴스 기사를 가져오는 소스"""

    def __init__(self, name: str, feed_urls: List[str]):
        super().__init__(name)
        self.feed_urls = feed_urls

    def fetch_news(
        self, keywords: List[str], num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """RSS 피드에서 뉴스 기사를 가져옴"""
        all_articles = []
        keyword_article_counts = {keyword: 0 for keyword in keywords}

        for feed_url in self.feed_urls:
            try:
                content = fetch_url_content(feed_url)
                feed = feedparser.parse(content)

                if not feed.entries:
                    logger.warning(f"피드 {feed_url}에서 기사를 찾을 수 없습니다")
                    continue

                logger.info(
                    f"RSS 피드를 성공적으로 가져왔습니다: {feed_url} - {len(feed.entries)} entries"
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

                logger.info(f"{feed_url}에서 {len(matched_entries)}개의 일치하는 기사를 찾았습니다")

            except Exception as e:
                logger.error(f"RSS 피드 {feed_url}를 가져오는 중 오류가 발생했습니다: {e}")

        # 키워드별 수집한 기사 수 출력
        for keyword, count in keyword_article_counts.items():
            logger.info(f"'{keyword}': RSS 피드에서 {count}개의 기사를 수집했습니다")

        # 키워드별 수집 결과 저장 (소스별 집계용)
        self._last_keyword_counts = keyword_article_counts
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
                except Exception as e:
                    handle_exception(e, "날짜 형식 변환", log_level=logging.DEBUG)
                    # 날짜 변환 실패시 다음 필드 시도
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
                except Exception as e:
                    handle_exception(e, "날짜 형식 변환", log_level=logging.DEBUG)
                    # 날짜 변환 실패시 다음 필드 시도
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
            logger.warning("Naver API 자격 증명을 찾을 수 없습니다. Naver 뉴스 소스를 건너뜁니다.")
            return []

        all_articles = []
        keyword_article_counts = {}

        for keyword in keywords:
            logger.info(f"Naver News API를 사용하여 키워드 '{keyword}'에 대한 기사를 검색중입니다")

            url = f"https://openapi.naver.com/v1/search/news.json?query={keyword}&display={num_results}&sort=date"
            headers = {
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret,
            }

            try:
                content = fetch_url_content(url, headers=headers)
                results = json.loads(content)
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
                logger.info(
                    f"Naver News API를 통해 키워드 '{keyword}'에 대해 {num_found}개의 기사를 찾았습니다"
                )
                all_articles.extend(articles_for_keyword)

            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Naver News API를 통해 키워드 '{keyword}'에 대한 기사를 가져오는 중 오류가 발생했습니다: {e}"
                )

        # 키워드별 수집 결과 저장 (소스별 집계용)
        self._last_keyword_counts = keyword_article_counts
        return all_articles


class NewsSourceManager:
    """여러 뉴스 소스를 관리하고 통합 결과를 제공하는 관리자 클래스"""

    def __init__(self):
        self.sources = []
        # 주요 언론사 설정은 config에서 중앙 관리

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

        logger.info(f"키워드: {keywords_list}에 대한 뉴스를 수집중입니다")

        all_articles = []
        for source in self.sources:
            logger.info(f"{source.get_source_name()}에서 뉴스를 수집중입니다...")
            articles = source.fetch_news(keywords_list, num_results_per_source)
            all_articles.extend(articles)

        logger.info(f"모든 소스에서 수집한 총 기사 수: {len(all_articles)}")

        # 키워드별 수집 결과 간략 표시
        # 키워드별 기사 수 집계
        keyword_counts = {}
        for source in self.sources:
            if hasattr(source, "_last_keyword_counts"):
                for keyword, count in source._last_keyword_counts.items():
                    keyword_counts[keyword] = keyword_counts.get(keyword, 0) + count

        if keyword_counts:
            show_collection_brief(keyword_counts)

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

        logger.info(f"{len(articles) - len(unique_articles)}개의 중복된 기사를 제거했습니다")
        return unique_articles

    def filter_by_major_sources(
        self, articles: List[Dict[str, Any]], max_per_topic: int = 5
    ) -> List[Dict[str, Any]]:
        """주요 언론사 기사 우선 필터링

        Args:
            articles: 필터링할 기사 목록
            max_per_topic: 주제별 최대 기사 수

        Returns:
            필터링된 기사 목록
        """
        if not articles:
            return []

        # 주요 언론사 목록 (한국 주요 언론사)
        major_sources = config.ALL_MAJOR_NEWS_SOURCES

        # 주요 언론사 기사와 기타 기사 분리
        major_articles = []
        other_articles = []

        for article in articles:
            source = article.get("source", "").strip()
            is_major = any(major_source in source for major_source in major_sources)

            if is_major:
                major_articles.append(article)
            else:
                other_articles.append(article)

        # 주요 언론사 기사 우선 선택 (최대 개수의 70%)
        major_count = min(len(major_articles), int(max_per_topic * 0.7))
        selected_major = major_articles[:major_count]

        # 나머지 자리는 기타 기사로 채움
        remaining_slots = max_per_topic - len(selected_major)
        selected_other = other_articles[:remaining_slots]

        filtered_articles = selected_major + selected_other

        logger.info(
            f"Filtered articles by major sources: {len(filtered_articles)} selected from {len(articles)} total"
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
            logger.info(
                f"Grouped {len(grouped_articles[keyword])} articles for keyword: '{keyword}'"
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
