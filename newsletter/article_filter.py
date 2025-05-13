"""
Newsletter Generator - Article Filtering and Grouping
이 모듈은 뉴스 기사를 필터링하고 그룹화하는 기능을 제공합니다.
"""

from typing import Dict, List, Any
import re
from rich.console import Console

console = Console()

# 주요 언론사 티어 설정
MAJOR_NEWS_SOURCES = {
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


def filter_articles_by_major_sources(
    articles: List[Dict[str, Any]], max_per_topic: int = 5
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
            for major_source in MAJOR_NEWS_SOURCES["tier1"]
        ):
            tier1_articles.append(article)
        elif any(
            major_source.lower() in source_norm
            for major_source in MAJOR_NEWS_SOURCES["tier2"]
        ):
            tier2_articles.append(article)
        else:
            other_articles.append(article)

    console.print(f"[cyan]News source distribution:[/cyan]")
    console.print(
        f"[green]- Tier 1 (major sources): {len(tier1_articles)} articles[/green]"
    )
    console.print(
        f"[yellow]- Tier 2 (secondary sources): {len(tier2_articles)} articles[/yellow]"
    )
    console.print(f"[grey]- Other sources: {len(other_articles)} articles[/grey]")

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
    articles: List[Dict[str, Any]], keywords: List[str]
) -> Dict[str, List[Dict[str, Any]]]:
    """키워드별로 기사 그룹화

    Args:
        articles: 그룹화할 기사 목록
        keywords: 키워드 리스트

    Returns:
        키워드별 기사 그룹 (키워드: 기사 목록)
    """
    # 디버깅 정보 출력
    console.print(
        f"[bold cyan]DEBUG: Starting grouping of {len(articles)} articles by {len(keywords)} keywords[/bold cyan]"
    )
    console.print(f"[bold cyan]DEBUG: Keywords: {keywords}[/bold cyan]")

    # 키워드별 빈 목록 초기화
    grouped_articles = {keyword: [] for keyword in keywords}

    # 각 기사에 대해 일치하는 모든 키워드 찾기
    for i, article in enumerate(articles):
        title = article.get("title", "").lower()
        content = article.get("content", "").lower()

        console.print(f"[grey]DEBUG: Processing article {i+1}: {title[:50]}...[/grey]")

        for keyword in keywords:
            keyword_lower = keyword.lower()
            keyword_no_space = keyword_lower.replace(" ", "")  # 공백 제거

            # 영문/숫자 키워드는 단어 경계, 한글 등은 단순 포함
            if re.fullmatch(r"[a-zA-Z0-9]+", keyword_lower):
                keyword_pattern = r"\b" + re.escape(keyword_lower) + r"\b"
                title_match = re.search(keyword_pattern, title)
                content_match = re.search(keyword_pattern, content)
                if title_match or content_match:
                    grouped_articles[keyword].append(article)
                    console.print(
                        f"[cyan]DEBUG: Article {i+1} matched keyword '{keyword}' (word boundary)[/cyan]"
                    )
            else:
                # 한글 키워드를 위한 다양한 일치 시도
                # 1. 정확한 키워드 일치
                if keyword_lower in title or keyword_lower in content:
                    grouped_articles[keyword].append(article)
                    console.print(
                        f"[cyan]DEBUG: Article {i+1} matched keyword '{keyword}' (exact substring)[/cyan]"
                    )
                # 2. 공백 무시하고 일치
                elif keyword_no_space and (
                    keyword_no_space in title.replace(" ", "")
                    or keyword_no_space in content.replace(" ", "")
                ):
                    grouped_articles[keyword].append(article)
                    console.print(
                        f"[cyan]DEBUG: Article {i+1} matched keyword '{keyword}' (no spaces)[/cyan]"
                    )
                # 3. 부분 키워드 일치 (예: 'AI반도체'는 'ai 반도체'와 일치)
                else:
                    # 부분 일치 허용(공백이나 다른 구분자로 분리되어 있을 수 있음)
                    parts = re.split(r"[\s_\-]+", keyword_lower)
                    if len(parts) > 1:
                        parts_matched = all(
                            part in title or part in content
                            for part in parts
                            if len(part) > 1
                        )
                        if parts_matched:
                            grouped_articles[keyword].append(article)
                            console.print(
                                f"[cyan]DEBUG: Article {i+1} matched keyword '{keyword}' (parts matching)[/cyan]"
                            )
                            continue

                    # 디버깅 출력
                    console.print(
                        f"[grey]DEBUG: Article {i+1} did not match keyword '{keyword}'[/grey]"
                    )

                    # 내용 일부만 출력해서 확인
                    if len(title) > 100:
                        console.print(f"[grey]DEBUG: Title: {title[:100]}...[/grey]")
                    else:
                        console.print(f"[grey]DEBUG: Title: {title}[/grey]")

                    if len(content) > 100:
                        console.print(
                            f"[grey]DEBUG: Content excerpt: {content[:100]}...[/grey]"
                        )
                    else:
                        console.print(f"[grey]DEBUG: Content excerpt: {content}[/grey]")

    # 각 키워드 그룹 결과 출력
    for keyword in grouped_articles:
        console.print(
            f"[green]Grouped {len(grouped_articles[keyword])} articles for keyword: '{keyword}'[/green]"
        )

    return grouped_articles


def remove_duplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """중복된 기사 제거

    Args:
        articles: 중복 제거할 기사 목록

    Returns:
        중복이 제거된 기사 목록
    """
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


def filter_articles_by_domains(
    articles: List[Dict[str, Any]],
    preferred_domains: List[str] = None,
    max_per_domain: int = 2,
) -> List[Dict[str, Any]]:
    """동일 도메인의 기사 수를 제한

    Args:
        articles: 필터링할 기사 목록
        preferred_domains: 우선적으로 포함할 도메인 목록
        max_per_domain: 각 도메인별 최대 기사 수

    Returns:
        필터링된 기사 목록
    """
    if not preferred_domains:
        preferred_domains = []

    # 도메인별 기사 그룹화
    domain_groups = {}

    import re
    from urllib.parse import urlparse

    for article in articles:
        url = article.get("url", "")
        if not url or url == "#":
            continue

        # URL에서 도메인 추출
        try:
            domain = urlparse(url).netloc
            # www. 제거
            domain = re.sub(r"^www\.", "", domain)
        except:
            # URL 파싱 실패시 전체 URL 사용
            domain = url

        if domain not in domain_groups:
            domain_groups[domain] = []

        domain_groups[domain].append(article)

    # 선별된 기사 목록
    filtered_articles = []

    # 1. 우선 도메인 처리
    for domain in preferred_domains:
        if domain in domain_groups:
            # 우선 도메인은 최대 개수까지 추가
            filtered_articles.extend(domain_groups[domain][:max_per_domain])
            # 처리한 기사는 제거
            domain_groups[domain] = domain_groups[domain][max_per_domain:]

    # 2. 나머지 도메인 처리
    for domain, domain_articles in domain_groups.items():
        # 각 도메인별 최대 개수만 추가
        filtered_articles.extend(domain_articles[:max_per_domain])

    console.print(
        f"[cyan]Filtered by domains: {len(filtered_articles)} selected from {len(articles)} total[/cyan]"
    )

    return filtered_articles
