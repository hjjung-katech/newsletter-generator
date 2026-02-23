#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# flake8: noqa

import json
import os
import sys
import traceback
from datetime import datetime
from typing import List, Optional, cast

# F-14: Windows 한글 인코딩 문제 해결 (강화된 버전)
if sys.platform.startswith("win"):
    import io
    import locale

    # UTF-8 인코딩 강제 설정
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"

    # 시스템 기본 인코딩을 UTF-8로 설정
    try:
        locale.setlocale(locale.LC_ALL, "ko_KR.UTF-8")
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, ".65001")  # Windows UTF-8 codepage
        except locale.Error:
            pass  # 설정할 수 없으면 무시

    # 표준 입출력 스트림을 UTF-8로 재구성
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    else:
        # 이전 Python 버전을 위한 fallback
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace"
        )

    # 디폴트 인코딩 설정
    if hasattr(sys, "_setdefaultencoding"):
        sys._setdefaultencoding("utf-8")

import typer
from dotenv import load_dotenv
from rich.console import Console

# Explicitly load .env from the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
dotenv_path = os.path.join(project_root, ".env")

# 새로운 로깅 시스템 import
from .utils.logger import get_logger, set_log_level

# 로거 초기화
logger = get_logger()

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    logger.debug(f"Loaded .env file from: {dotenv_path}")
else:
    logger.warning(f".env file not found at: {dotenv_path}")

from . import collect as news_collect
from . import compose as news_compose
from . import graph  # 새로운 LangGraph 모듈 임포트
from . import tools  # Import the tools module
from . import config
from . import deliver as news_deliver
from . import summarize as news_summarize
from .cli_diagnostics import (
    check_config,
    check_llm,
    list_providers,
    test_email,
    test_llm,
)
from .cli_run import run
from .cli_test import test
from .compose import compose_compact_newsletter_html, compose_newsletter_html

app = typer.Typer()
console = Console()


# The 'collect' command can remain if it's used for other purposes or direct testing.
@app.command()  # type: ignore[untyped-decorator]
def collect(
    keywords: str,
    max_per_source: int = typer.Option(
        3, "--max-per-source", help="Maximum number of articles per source."
    ),
    no_filter_duplicates: bool = typer.Option(
        False, "--no-filter-duplicates", help="Don't filter duplicate articles."
    ),
    no_group_by_keywords: bool = typer.Option(
        False, "--no-group-by-keywords", help="Don't group articles by keywords."
    ),
    no_major_sources_filter: bool = typer.Option(
        False, "--no-major-sources-filter", help="Don't prioritize major news sources."
    ),
    log_level: str = typer.Option(
        "WARNING",
        "--log-level",
        help="Logging level: DEBUG, INFO, WARNING, ERROR",
    ),
) -> None:
    """
    Collect articles based on keywords with improved filtering and grouping.
    """
    # 로그 레벨 설정
    set_log_level(log_level)
    logger = get_logger()

    logger.info(f"Collecting articles for keywords: {keywords}")

    # 기사 수집 및 처리
    with logger.step_context("article_collection", "기사 수집 및 처리"):
        articles = news_collect.collect_articles(
            keywords,
            max_per_source=max_per_source,
            filter_duplicates=not no_filter_duplicates,
            group_by_keywords=not no_group_by_keywords,
            use_major_sources_filter=not no_major_sources_filter,
        )

    # 결과 출력
    if isinstance(articles, dict):  # 그룹화된 결과인 경우
        keyword_counts = {
            keyword: len(keyword_articles)
            for keyword, keyword_articles in articles.items()
        }
        logger.show_article_collection_summary(keyword_counts)

        for keyword, keyword_articles in articles.items():
            logger.info(f"Keyword: {keyword} - {len(keyword_articles)} articles")
            for i, article in enumerate(keyword_articles, 1):
                logger.debug(
                    f"  {i}. {article.get('title', 'No title')} ({article.get('source', 'Unknown')})"
                )
    else:  # 그룹화되지 않은 결과인 경우
        logger.success(f"Collected {len(articles)} articles")
        for i, article in enumerate(articles, 1):
            logger.debug(
                f"{i}. {article.get('title', 'No title')} ({article.get('source', 'Unknown')})"
            )

    # 생성 날짜 설정
    current_date_str = datetime.now().strftime("%Y-%m-%d")
    # 파일 이름 생성
    filename_base = f"{current_date_str}_collected_articles_{keywords.replace(',', '_').replace(' ', '')}"

    # 결과 저장
    output_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"{filename_base}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    logger.success(f"Results saved to {output_path}")


@app.command()  # type: ignore[untyped-decorator]
def suggest(
    domain: str = typer.Option(..., "--domain", help="Domain to suggest keywords for."),
    count: int = typer.Option(
        10, "--count", min=1, help="Number of keywords to generate."
    ),
    log_level: str = typer.Option(
        "WARNING",
        "--log-level",
        help="Logging level: DEBUG, INFO, WARNING, ERROR",
    ),
) -> None:
    """
    Suggests trend keywords for a given domain using Google Gemini.
    """
    # 로그 레벨 설정
    set_log_level(log_level)
    logger = get_logger()

    logger.info(f"Suggesting {count} keywords for domain: '{domain}'")

    if not config.GEMINI_API_KEY:  # GOOGLE_API_KEY 대신 GEMINI_API_KEY 사용
        logger.error(
            "GEMINI_API_KEY is not set in the environment variables or .env file."
        )
        logger.info("Please set it to use the keyword suggestion feature.")
        raise typer.Exit(code=1)

    with logger.step_context("keyword_suggestion", f"도메인 '{domain}'에 대한 키워드 제안"):
        suggested_keywords = tools.generate_keywords_with_gemini(domain, count=count)

    if suggested_keywords:
        logger.show_keyword_info(suggested_keywords, domain)

        # Construct the command for the user
        keywords_str = ",".join(suggested_keywords)
        run_command = f'newsletter run --keywords "{keywords_str}"'
        logger.info(
            "To generate a newsletter with these keywords, you can use the following command:"
        )
        logger.info(f"{run_command}")
    else:
        logger.error(
            f"Failed to generate keywords for domain '{domain}'. Please check your API configuration."
        )


app.command()(check_config)
app.command()(check_llm)
app.command()(test_llm)
app.command()(list_providers)
app.command()(test_email)
app.command()(run)
app.command()(test)


# API wrapper functions for web interface
def suggest_keywords(domain: str, count: int = 10) -> list[str]:
    """
    Wrapper function for web API to suggest keywords for a given domain.
    Uses the existing tools.generate_keywords_with_gemini function.

    Args:
        domain: Domain to suggest keywords for
        count: Number of keywords to generate (default: 10)

    Returns:
        List of suggested keywords

    Raises:
        Exception: If keyword generation fails
    """
    from . import tools

    # 기존 검증된 키워드 생성 함수 사용
    return cast(list[str], tools.generate_keywords_with_gemini(domain, count=count))


if __name__ == "__main__":
    app()
