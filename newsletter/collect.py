import json
from typing import Any, Dict, List, Union

import requests
from rich.console import Console

from . import article_filter, config
from .sources import configure_default_sources
from .utils.logger import get_structured_logger as get_logger

console = Console()
logger = get_logger("newsletter.collect")


def collect_articles(
    keywords: Union[str, List[str]],
    num_results: int = 10,
    max_per_source: int = 3,
    filter_duplicates: bool = True,
    group_by_keywords: bool = True,
    use_major_sources_filter: bool = True,
) -> Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """
    Collect news articles from multiple sources based on keywords.

    This function collects news from various configured sources including:
    - Serper.dev API (Google search results)
    - RSS feeds from major Korean news outlets
    - Naver News API (if configured)

    Args:
        keywords: String of comma-separated keywords OR list of keyword strings
        num_results: Number of results to return per keyword per source (default: 10)
        max_per_source: Maximum number of articles per source (default: 3)
        filter_duplicates: Whether to filter duplicate articles (default: True)
        group_by_keywords: Whether to group articles by keywords (default: True)
        use_major_sources_filter: Whether to prioritize major news sources (default: True)

    Returns:
        List of article dictionaries with standardized format, or a dictionary of articles grouped by keywords
    """
    # 다양한 뉴스 소스를 관리하는 매니저 생성
    source_manager = configure_default_sources()

    if not source_manager.sources:
        console.print(
            "[bold red]Error: No news sources configured. Please check your API keys.[/bold red]"
        )
        return []

    # 모든 소스에서 뉴스 수집
    all_articles = source_manager.fetch_all_sources(keywords, num_results)

    # 키워드 처리
    if isinstance(keywords, str):
        keywords_list = [k.strip() for k in keywords.split(",")]
    else:
        keywords_list = keywords

    # 중복 기사 제거
    if filter_duplicates:
        unique_articles = article_filter.remove_duplicate_articles(all_articles)
    else:
        unique_articles = all_articles

    console.print(
        f"[bold green]Article count after initial processing: {len(unique_articles)}[/bold green]"
    )

    # 언론사 필터링
    if use_major_sources_filter:
        console.print("[bold cyan]Applying major news sources filter...[/bold cyan]")
        # 키워드별 그룹 처리 시 각 키워드 그룹에서 필터링 적용
        if group_by_keywords:
            grouped_articles = article_filter.group_articles_by_keywords(
                unique_articles, keywords_list
            )

            # 각 키워드 그룹에 필터 적용
            filtered_grouped_articles = {}
            for keyword, articles in grouped_articles.items():
                # 도메인별 최대 기사 수 제한
                domain_filtered = article_filter.filter_articles_by_domains(
                    articles, max_per_domain=2
                )
                # 주요 언론사 필터 적용
                filtered_grouped_articles[
                    keyword
                ] = article_filter.filter_articles_by_major_sources(
                    domain_filtered, max_per_topic=max_per_source
                )

            return filtered_grouped_articles
        else:
            # 도메인별 최대 기사 수 제한
            domain_filtered = article_filter.filter_articles_by_domains(
                unique_articles, max_per_domain=2
            )
            # 주요 언론사 필터 적용
            return article_filter.filter_articles_by_major_sources(
                domain_filtered, max_per_topic=max_per_source
            )
    elif group_by_keywords:
        # 언론사 필터 없이 그룹화만 적용
        return article_filter.group_articles_by_keywords(unique_articles, keywords_list)
    else:
        # 아무 처리도 하지 않고 반환
        return unique_articles


def collect_articles_from_serper(keywords, num_results: int = 10):
    """
    Legacy function for backward compatibility.
    Collect news articles from Serper.dev based on keywords using the news-specific endpoint.

    Args:
        keywords: String of comma-separated keywords OR list of keyword strings
        num_results: Number of results to return per keyword (default: 10)

    Returns:
        List of article dictionaries
    """
    console.print(
        "[yellow]Warning: Using legacy Serper-only collection method.[/yellow]"
    )

    # 키워드가 문자열로 제공된 경우 리스트로 변환
    if isinstance(keywords, str):
        keywords_list = [kw.strip() for kw in keywords.split(",")]
    else:
        # 이미 리스트로 제공된 경우
        keywords_list = keywords

    logger.info(f"Collecting articles for: {keywords_list} using Serper.dev")
    # 키워드별 기사 수를 저장할 딕셔너리
    keyword_article_counts = {}

    if not config.SERPER_API_KEY:
        logger.error("SERPER_API_KEY not found. Please set it in the .env file.")
        return []  # 뉴스 전용 엔드포인트로 변경
    url = "https://google.serper.dev/news"

    # 각 키워드에 대해 개별적으로 API 호출
    all_articles = []

    for keyword in keywords_list:
        logger.debug(f"Searching for keyword: {keyword}")
        payload = json.dumps(
            {
                "q": keyword,
                "gl": "kr",  # 한국 지역 결과
                "num": num_results,  # 지정된 수만큼 결과 반환
            }
        )
        headers = {
            "X-API-KEY": config.SERPER_API_KEY,
            "Content-Type": "application/json",
        }

        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            response.raise_for_status()  # Raise an exception for HTTP errors
            search_results = response.json()

            articles_for_keyword = []

            # 뉴스 API 응답 처리 - 여러 가능한 컨테이너 확인
            articles_container = []

            # 1. 주요 'news' 컨테이너 확인
            if "news" in search_results:
                logger.debug(f"Processing news results for keyword '{keyword}'")
                articles_container.extend(search_results["news"])

            # 2. 'topStories' 컨테이너도 확인 (일부 응답에서 사용)
            if "topStories" in search_results and not articles_container:
                logger.debug(f"Processing topStories results for keyword '{keyword}'")
                articles_container.extend(search_results["topStories"])

            # 3. 'organic' 컨테이너 확인 (fallback)
            if "organic" in search_results and not articles_container:
                logger.debug(f"Processing organic results for keyword '{keyword}'")
                articles_container.extend(search_results["organic"])

            # 결과 처리
            if articles_container:
                for item in articles_container:
                    articles_for_keyword.append(
                        {
                            "title": item.get("title", "No Title"),
                            "url": item.get("link", "#"),
                            "link": item.get("link", "#"),  # 호환성을 위해 link도 추가
                            "content": item.get(
                                "snippet", item.get("description", "No Content Snippet")
                            ),
                            "source": item.get("source", "Unknown Source"),
                            "date": item.get("date")
                            or item.get("publishedAt")
                            or "No Date",
                        }
                    )
            else:
                logger.info(
                    f"No results found for keyword '{keyword}'. Available keys: {list(search_results.keys())}"
                )

            # 키워드별 기사 수 저장 및 출력
            num_articles_found = len(articles_for_keyword)
            keyword_article_counts[keyword] = num_articles_found
            logger.info(f"Found {num_articles_found} articles for keyword: '{keyword}'")

            all_articles.extend(articles_for_keyword)

        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error fetching articles for keyword '{keyword}' from Serper.dev: {e}"
            )
        except json.JSONDecodeError:
            logger.error(
                f"Error decoding JSON response for keyword '{keyword}' from Serper.dev. Response: {response.text}"
            )

    # 전체 수집된 기사 수 출력
    logger.info(f"Total collected articles: {len(all_articles)}")
    # 키워드별 수집된 기사 수 요약 출력
    logger.info("Summary of articles collected per keyword:")
    for kw, count in keyword_article_counts.items():
        logger.info(f"- '{kw}': {count} articles")

    return all_articles


if __name__ == "__main__":
    # Example usage:
    # Make sure to have SERPER_API_KEY in your .env file
    # from config import SERPER_API_KEY # For direct execution test
    # if not SERPER_API_KEY:
    #     print("Please set SERPER_API_KEY in .env file for testing.")
    # else:
    #     test_keywords = "AI in healthcare"
    #     collected_articles = collect_articles(test_keywords)
    #     if collected_articles:
    #         print(f"\nCollected {len(collected_articles)} articles for '{test_keywords}':")
    #         for article in collected_articles:
    #             print(f"- Title: {article['title']}")
    #             print(f"  URL: {article['url']}")
    #             print(f"  Snippet: {article['content'][:100]}...") # Print first 100 chars of snippet
    #     else:
    #         print(f"No articles collected for '{test_keywords}'.")
    pass
