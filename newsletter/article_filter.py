"""
Newsletter Generator - Article Filtering and Grouping
이 모듈은 뉴스 기사를 필터링하고 그룹화하는 기능을 제공합니다.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from rich.console import Console

from . import config
from .utils.logger import get_logger

# 로거 초기화
logger = get_logger()
console = Console()

# 동의어 설정 (키워드 매칭 개선용)
SYNONYMS: Dict[str, List[str]] = {
    "AI반도체": ["AI반도체", "AI 반도체", "인공지능 반도체", "ai semiconductor"],
    "HBM": ["HBM", "hbm", "high bandwidth memory", "고대역폭 메모리"],
    "CXL": ["CXL", "cxl", "compute express link"],
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
            for major_source in config.MAJOR_NEWS_SOURCES["tier1"]
        ):
            tier1_articles.append(article)
        elif any(
            major_source.lower() in source_norm
            for major_source in config.MAJOR_NEWS_SOURCES["tier2"]
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

    # 티어에 따라 기사 선택 (관대한 필터링으로 더 많은 기사 포함)
    filtered_articles = []

    # 각 티어에서 균형있게 선택 (더 많은 기사 포함)
    tier1_count = min(len(tier1_articles), max(1, max_per_topic // 2))
    tier2_count = min(len(tier2_articles), max(1, max_per_topic // 3))
    other_count = max_per_topic - tier1_count - tier2_count
    
    # 각 티어에서 기사 추가
    filtered_articles.extend(tier1_articles[:tier1_count])
    filtered_articles.extend(tier2_articles[:tier2_count])
    filtered_articles.extend(other_articles[:other_count])
    
    # 아직 공간이 남으면 추가 기사 포함
    remaining_slots = max_per_topic - len(filtered_articles)
    if remaining_slots > 0:
        # 남은 기사들도 추가
        remaining_articles = (tier1_articles[tier1_count:] + 
                            tier2_articles[tier2_count:] + 
                            other_articles[other_count:])
        filtered_articles.extend(remaining_articles[:remaining_slots])

    console.print(
        f"[cyan]Filtered articles by major sources: {len(filtered_articles)} selected from {len(articles)} total[/cyan]"
    )

    return filtered_articles


def group_articles_by_keywords(
    articles: List[Dict[str, Any]], keywords: List[str]
) -> Dict[str, List[Dict[str, Any]]]:
    """키워드별로 기사 그룹화 (동의어 및 문맥 기반 매칭 지원)"""
    logger.debug(
        f"Starting grouping of {len(articles)} articles by {len(keywords)} keywords"
    )
    logger.debug(f"Keywords: {keywords}")

    grouped_articles = {keyword: [] for keyword in keywords}

    def _tokenize(text: str) -> List[str]:
        return re.findall(r"[가-힣a-zA-Z0-9]+", text.lower())

    def _tokens_in_context(
        text_tokens: List[str], tokens: List[str], window: int = 5
    ) -> bool:
        if len(tokens) == 1:
            return tokens[0] in text_tokens
        positions = []
        for token in tokens:
            idxs = [i for i, t in enumerate(text_tokens) if t == token]
            if not idxs:
                return False
            positions.append(idxs)
        import itertools

        for combo in itertools.product(*positions):
            if max(combo) - min(combo) <= window:
                return True
        return False

    for i, article in enumerate(articles):
        full_text = f"{article.get('title', '')} {article.get('content', '')}".lower()
        tokens = _tokenize(full_text)
        logger.debug(f"Processing article {i+1}: {full_text[:50]}...")

        for keyword in keywords:
            variations = SYNONYMS.get(keyword, [keyword])
            matched = False
            for variant in variations:
                v_text = variant.lower()
                v_tokens = _tokenize(variant)
                if v_text in full_text or v_text.replace(" ", "") in full_text.replace(
                    " ", ""
                ):
                    matched = True
                elif _tokens_in_context(tokens, v_tokens):
                    matched = True
                if matched:
                    grouped_articles[keyword].append(article)
                    logger.debug(
                        f"Article {i+1} matched keyword '{keyword}' via variant '{variant}'"
                    )
                    break
            if not matched:
                logger.debug(f"Article {i+1} did not match keyword '{keyword}'")

    for keyword in grouped_articles:
        logger.info(
            f"Grouped {len(grouped_articles[keyword])} articles for keyword: '{keyword}'"
        )

    return grouped_articles


def remove_duplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """중복된 기사 제거 (URL 정규화 및 제목 유사성 검사 포함)

    Args:
        articles: 중복 제거할 기사 목록

    Returns:
        중복이 제거된 기사 목록
    """
    unique_articles = []
    seen_urls = set()
    seen_titles = set()

    def normalize_url(url: str) -> str:
        """URL을 정규화하여 중복 검사에 사용"""
        if not url or url == "#":
            return ""
        # 쿼리 파라미터 제거, 프로토콜 통일, www 제거 등
        import re
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
            # 도메인 정규화 (www 제거, 소문자 변환)
            domain = parsed.netloc.lower()
            domain = re.sub(r"^www\.", "", domain)
            # 경로 정규화 (끝의 / 제거)
            path = parsed.path.rstrip("/")
            # 정규화된 URL 생성 (쿼리 파라미터 제외)
            normalized = f"{domain}{path}"
            return normalized
        except:
            return url.lower()

    def normalize_title(title: str) -> str:
        """제목을 정규화하여 중복 검사에 사용"""
        if not title:
            return ""
        # 특수문자 제거, 공백 정규화, 소문자 변환
        import re

        normalized = re.sub(r"[^\w\s가-힣]", "", title)
        normalized = re.sub(r"\s+", " ", normalized).strip().lower()
        return normalized

    for article in articles:
        url = article.get("url", "")
        title = article.get("title", "")

        # URL과 제목이 모두 없는 경우는 스킵
        if not url and not title:
            continue

        # URL 정규화 및 중복 확인
        normalized_url = normalize_url(url)
        if normalized_url and normalized_url in seen_urls:
            console.print(f"[yellow]Skipping duplicate URL: {url}[/yellow]")
            continue

        # 제목 정규화 및 중복 확인
        normalized_title = normalize_title(title)
        if normalized_title and normalized_title in seen_titles:
            console.print(f"[yellow]Skipping duplicate title: {title}[/yellow]")
            continue

        # 제목 유사성 검사 (기존 기사들과 비교)
        is_similar = False
        if normalized_title:
            for existing_title in seen_titles:
                if existing_title:
                    overlap_ratio = _word_overlap_ratio(
                        normalized_title, existing_title
                    )

                    # 겹침 비율이 높더라도 중요한 차별화 단어가 있으면 다른 기사로 처리
                    differentiating_words = [
                        "계획",
                        "발표",
                        "예정",
                        "준비",
                        "검토",
                        "추진",
                        "시작",
                        "완료",
                        "종료",
                        "중단",
                    ]
                    title_words = set(normalized_title.split())
                    existing_words = set(existing_title.split())

                    has_differentiating_word = any(
                        word in title_words or word in existing_words
                        for word in differentiating_words
                    )

                    # 겹침 비율이 매우 높고 차별화 단어가 없는 경우에만 중복으로 처리
                    if overlap_ratio >= 0.99 and not has_differentiating_word:
                        console.print(
                            f"[yellow]Skipping similar title: {title}[/yellow]"
                        )
                        is_similar = True
                        break

        if is_similar:
            continue

        # 중복이 아닌 경우 추가
        if normalized_url:
            seen_urls.add(normalized_url)
        if normalized_title:
            seen_titles.add(normalized_title)

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


def _word_overlap_ratio(title1: str, title2: str) -> float:
    """Compute overlap ratio between two titles based on unique word sets."""
    tokens1 = set(re.split(r"[\W_]+", title1.lower())) - {""}
    tokens2 = set(re.split(r"[\W_]+", title2.lower())) - {""}
    if not tokens1 or not tokens2:
        return 0.0
    overlap = tokens1 & tokens2
    return len(overlap) / min(len(tokens1), len(tokens2))


def remove_similar_articles(
    articles: List[Dict[str, Any]], similarity_threshold: float = 0.8
) -> List[Dict[str, Any]]:
    """Remove nearly identical articles based on title similarity."""
    unique_articles: List[Dict[str, Any]] = []
    for article in articles:
        title = article.get("title", "")
        if not title:
            unique_articles.append(article)
            continue
        is_similar = False
        for kept in unique_articles:
            kept_title = kept.get("title", "")
            if (
                kept_title
                and _word_overlap_ratio(title, kept_title) >= similarity_threshold
            ):
                is_similar = True
                break
        if not is_similar:
            unique_articles.append(article)
    console.print(
        f"[cyan]Removed {len(articles) - len(unique_articles)} similar articles[/cyan]"
    )
    return unique_articles


from .date_utils import parse_date_string


def calculate_article_importance(article: Dict[str, Any]) -> float:
    """Calculate a simple importance score for an article."""
    score = 0.0
    source = article.get("source", "")
    if any(s.lower() in source.lower() for s in config.MAJOR_NEWS_SOURCES["tier1"]):
        score += 2.0
    elif any(s.lower() in source.lower() for s in config.MAJOR_NEWS_SOURCES["tier2"]):
        score += 1.0

    date_obj = parse_date_string(article.get("date"))
    if date_obj:
        if date_obj.tzinfo is None or date_obj.tzinfo.utcoffset(date_obj) is None:
            date_obj = date_obj.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - date_obj).total_seconds() / 86400
        recency = max(0.0, 30 - age_days) / 30
    else:
        recency = 0.0
    score += recency
    return score


def select_top_articles(
    articles: List[Dict[str, Any]], top_n: int = 3
) -> List[Dict[str, Any]]:
    """Select top N articles based on importance score."""
    scored = [(a, calculate_article_importance(a)) for a in articles]
    scored.sort(key=lambda x: x[1], reverse=True)
    for article, score in scored:
        article["importance_score"] = round(score, 3)
    return [a for a, _ in scored[:top_n]]
