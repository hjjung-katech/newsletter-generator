#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# flake8: noqa

import json
import os
import sys
import traceback
from datetime import datetime
from typing import List, Optional

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
from .compose import compose_compact_newsletter_html, compose_newsletter_html

app = typer.Typer()
console = Console()


# The 'collect' command can remain if it's used for other purposes or direct testing.
@app.command()
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
):
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


@app.command()
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
):
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


@app.command()
def test(
    data_file: str = typer.Argument(
        ...,
        help="Path to the render_data_langgraph_...json file or collected_articles json file to use for testing",
    ),
    output: Optional[str] = typer.Option(
        None, "--output", help="Optional custom output path for the HTML file"
    ),
    mode: str = typer.Option(
        "template",
        "--mode",
        "-m",
        help="Mode: 'template' (just re-render) or 'content' (run full processing pipeline with saved articles)",
    ),
    template_style: str = typer.Option(
        "detailed",
        "--template-style",
        help="Newsletter template style: 'compact' (short, main news focused) or 'detailed' (full length with all sections).",
    ),
    email_compatible: bool = typer.Option(
        False,
        "--email-compatible",
        help="Apply email compatibility processing (inline CSS, table layout). Recommended for email sending.",
    ),
    track_cost: bool = typer.Option(
        False, "--track-cost", help="Enable LangSmith cost tracking during generation."
    ),
):
    """
    Process a newsletter from existing data file.

    In 'template' mode (default), it simply re-renders the existing data with the current template.
    In 'content' mode, it runs the full processing pipeline (excluding article collection) with previously collected articles.
    """
    try:
        # 데이터 파일 로드
        console.print(f"[cyan]Loading data from {data_file}...[/cyan]")
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if track_cost:
            os.environ["ENABLE_COST_TRACKING"] = "1"

        # 현재 날짜 및 시간 정보 설정
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M:%S")
        os.environ["GENERATION_DATE"] = current_date
        os.environ["GENERATION_TIMESTAMP"] = current_time

        # 모드에 따른 처리
        if mode.lower() == "template":
            # Template 모드: 기존 데이터를 HTML 템플릿으로 렌더링만 수행
            console.print(
                f"[cyan]Running in template mode - just re-rendering existing data with {template_style} style[/cyan]"
            )

            if email_compatible:
                console.print(f"[cyan]Email compatibility mode enabled[/cyan]")

            # 템플릿 스타일에 따른 compose_newsletter 함수 사용
            from .compose import compose_newsletter

            template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")

            # email_compatible인 경우 데이터에 template_style 정보 추가
            if email_compatible:
                if isinstance(data, dict):
                    data["template_style"] = template_style
                effective_style = "email_compatible"
                console.print(
                    f"[cyan]Rendering newsletter using email-compatible template with {template_style} content style...[/cyan]"
                )
            else:
                effective_style = template_style
                console.print(
                    f"[cyan]Rendering newsletter using {template_style} template...[/cyan]"
                )

            html_content = compose_newsletter(data, template_dir, style=effective_style)

            # 파일명 생성 및 저장
            if output is None:
                # 통일된 파일명 생성 함수 사용
                from .utils.file_naming import generate_unified_newsletter_filename

                # 입력 파일명에서 주제 추출 시도
                base_name = os.path.basename(data_file)
                if "render_data_langgraph" in base_name:
                    topic_part = "_".join(base_name.split("_")[3:]).replace(".json", "")
                elif "collected_articles" in base_name:
                    topic_part = base_name.replace("collected_articles_", "").replace(
                        ".json", ""
                    )
                else:
                    topic_part = "test"

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # 통일된 파일명 생성
                output = generate_unified_newsletter_filename(
                    topic=f"test_{topic_part}",
                    style=template_style,
                    timestamp=timestamp,
                    use_current_date=True,
                    generation_type="test",
                )

            # 출력 디렉토리 생성
            output_dir = os.path.dirname(output)
            if output_dir:  # 상대/절대 경로가 지정된 경우
                os.makedirs(output_dir, exist_ok=True)
            else:  # 파일명만 지정된 경우
                os.makedirs("output", exist_ok=True)
                output = os.path.join("output", os.path.basename(output))

            # HTML 저장
            with open(output, "w", encoding="utf-8") as f:
                f.write(html_content)

            console.print(f"[green]Newsletter rendered and saved to {output}[/green]")
            if os.path.exists(output):
                file_size = os.path.getsize(output)
                console.print(
                    f"[green]File created: {output} (Size: {file_size} bytes)[/green]"
                )
            else:
                console.print(
                    f"[bold red]Error: File was not created at {output}[/bold red]"
                )

        elif mode.lower() == "content":
            # Content 모드: 저장된 수집 데이터를 가지고 전체 프로세스 재실행
            console.print(
                "[cyan]Running in content mode - will run full processing pipeline with saved articles[/cyan]"
            )

            # 데이터 형식 확인 및 필요한 데이터 추출
            collected_articles = None
            keywords = None
            domain = None
            news_period_days = 14  # 기본값

            # 1. render_data_langgraph_*.json 파일인 경우
            if "sections" in data and "search_keywords" in data:
                console.print(
                    "[cyan]Found render data format. Extracting keywords...[/cyan]"
                )
                if isinstance(data["search_keywords"], list):
                    keywords = data["search_keywords"]
                else:
                    keywords = [
                        kw.strip()
                        for kw in data["search_keywords"].split(",")
                        if kw.strip()
                    ]

                # 도메인 정보는 일반적으로 없음 (있을 수도 있음)
                domain = data.get("domain", None)

                # 이 경우 collected_articles는 없으므로 다시 스크래핑 필요
                console.print(
                    "[yellow]No collected articles found in render data. Need to collect articles again.[/yellow]"
                )
                console.print(
                    "[cyan]Please use a collected_articles_*.json file for content mode to avoid recollection.[/cyan]"
                )

                # 사용자에게 계속할지 확인
                confirm = input("Continue with article collection? (y/n): ")
                if confirm.lower() != "y":
                    console.print("[yellow]Operation cancelled by user.[/yellow]")
                    return

                # 기사 수집
                console.print(
                    f"[cyan]Collecting articles for keywords: {', '.join(keywords)}...[/cyan]"
                )
                collected_articles = news_collect.collect_articles(
                    ",".join(keywords),
                    max_per_source=3,
                    filter_duplicates=True,
                    group_by_keywords=True,
                    use_major_sources_filter=True,
                )

            # 2. collected_articles_*.json 파일인 경우
            elif isinstance(data, dict) and any(
                key in data for key in ["keywords", "articles", "collected_articles"]
            ):
                console.print("[cyan]Found collected articles data format.[/cyan]")

                # keywords 추출
                if "keywords" in data:
                    if isinstance(data["keywords"], list):
                        keywords = data["keywords"]
                    else:
                        keywords = [
                            kw.strip()
                            for kw in data["keywords"].split(",")
                            if kw.strip()
                        ]

                # domain 추출
                domain = data.get("domain", None)

                # news_period_days 추출
                news_period_days = data.get("news_period_days", 14)

                # collected_articles 추출
                if "articles" in data:
                    collected_articles = data["articles"]
                    console.print(
                        f"[green]Found 'articles' field with {len(collected_articles)} articles.[/green]"
                    )
                elif "collected_articles" in data:
                    collected_articles = data["collected_articles"]
                    console.print(
                        f"[green]Found 'collected_articles' field with {len(collected_articles)} articles.[/green]"
                    )
                # Handle structured output from process_articles_node
                elif isinstance(data, list):
                    # Direct list of articles (old format)
                    collected_articles = data
                    console.print(
                        f"[yellow]Found old format (direct list of articles) without metadata. Count: {len(collected_articles)}[/yellow]"
                    )
                    # In this case, keywords should already be set or we'll error out later

            # 3. 직접 그룹화된 기사 데이터인 경우
            elif isinstance(data, dict) and len(data) > 0:
                # Check if this is a dictionary where most values are lists (keywords->articles grouping)
                list_values = [k for k, v in data.items() if isinstance(v, list)]
                if (
                    len(list_values) > 0
                    and "keywords" not in data
                    and "articles" not in data
                    and "collected_articles" not in data
                ):
                    console.print(
                        "[cyan]Found grouped articles data format (keywords->articles mapping).[/cyan]"
                    )
                    collected_articles = data
                    keywords = list(data.keys())

            # Print additional debug info
            console.print(
                f"[blue]Data keys: {list(data.keys() if isinstance(data, dict) else ['<list>'])}[/blue]"
            )
            console.print(f"[blue]Data type: {type(data)}[/blue]")

            # 필요한 데이터가 없으면 오류
            if not keywords:
                console.print(
                    "[yellow]Warning: No keywords found in the data file.[/yellow]"
                )
                # Try to check if we at least have articles
                if collected_articles:
                    console.print(
                        "[yellow]Setting fallback test keyword since articles are available.[/yellow]"
                    )
                    # Set a default test keyword
                    keywords = ["테스트"]
                    console.print(
                        f"[green]Using fallback keyword: {keywords[0]}[/green]"
                    )
                else:
                    console.print(
                        "[bold red]Error: No keywords found and no articles available. Cannot proceed.[/bold red]"
                    )
                    raise typer.Exit(code=1)

            if not collected_articles:
                console.print(
                    "[bold red]Error: No collected articles found in the data file.[/bold red]"
                )
                raise typer.Exit(code=1)

            console.print(f"[green]Using keywords: {', '.join(keywords)}[/green]")
            if domain:
                console.print(f"[green]Using domain: {domain}[/green]")
            console.print(f"[green]Using news period: {news_period_days} days[/green]")

            # LangGraph 워크플로우 실행 (스크래핑 단계 건너뛰기)
            console.print(
                "\n[cyan]Starting LangGraph workflow with existing articles...[/cyan]"
            )

            # NewsletterState 초기 상태 설정
            from .graph import (
                NewsletterState,
                create_newsletter_graph,
                process_articles_node,
            )

            # 뉴스레터 주제 결정
            if domain:
                newsletter_topic = domain
            elif len(keywords) == 1:
                newsletter_topic = keywords[0]
            else:
                from .tools import extract_common_theme_from_keywords

                newsletter_topic = extract_common_theme_from_keywords(keywords)

            # 초기 상태 생성 (collect 단계의 결과를 직접 입력)
            initial_state: NewsletterState = {
                "keywords": keywords,
                "news_period_days": news_period_days,
                "domain": domain,
                "newsletter_topic": newsletter_topic,
                "template_style": template_style,
                "email_compatible": email_compatible,
                "collected_articles": collected_articles,  # 이미 수집된 기사
                "processed_articles": None,
                "article_summaries": None,
                "category_summaries": None,
                "newsletter_html": None,
                "error": None,
                "status": "processing",  # 'collecting' 단계를 건너뛰고 'processing'부터 시작
            }

            # 그래프 생성
            graph = create_newsletter_graph()

            # 그래프의 collect 노드 연결 제거하고 process_articles 노드부터 시작
            # 대신 직접 process_articles_node 함수를 호출하여 처리
            console.print("\n[cyan]Processing collected articles...[/cyan]")
            processed_state = process_articles_node(initial_state)

            # process_articles 이후부터 나머지 워크플로우 실행
            console.print("\n[cyan]Running remaining workflow...[/cyan]")
            # 그래프 시작 상태를 processed_state로 설정하고 실행
            final_state = graph.invoke(processed_state)

            # 결과 처리
            if final_state["status"] == "error":
                console.print(
                    f"[yellow]Error in newsletter generation: {final_state.get('error', 'Unknown error')}[/yellow]"
                )
                return

            html_content = final_state["newsletter_html"]
            console.print(
                "[green]Newsletter generated successfully using LangGraph.[/green]"
            )

            # 뉴스레터 주제 및 파일명 설정
            newsletter_topic = final_state.get("newsletter_topic", "")
            current_date_str = datetime.now().strftime("%Y-%m-%d")
            current_time_str = datetime.now().strftime("%H%M%S")

            # 통일된 파일명 생성 함수 사용
            from .utils.file_naming import generate_unified_newsletter_filename

            # 파일 이름에 안전한 주제 문자열 생성
            safe_topic = tools.get_filename_safe_theme(keywords, domain)

            # 출력 파일명 설정
            if output is None:
                # 통일된 파일명 생성
                timestamp = f"{datetime.now().strftime('%Y%m%d')}_{current_time_str}"
                save_path = generate_unified_newsletter_filename(
                    topic=f"content_{safe_topic}",
                    style=template_style,
                    timestamp=timestamp,
                    use_current_date=True,
                    generation_type="regenerated",
                )
            else:
                save_path = output

            # 출력 디렉토리 생성
            output_dir = os.path.dirname(save_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            # HTML 저장
            console.print(f"\n[cyan]Saving newsletter...[/cyan]")
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            console.print(f"[green]Newsletter saved to {save_path}.[/green]")

            # 렌더 데이터 저장 (재사용 가능하도록)
            render_data_path = os.path.join(
                "output",
                "intermediate_processing",
                f"render_data_test_{current_date_str}_{current_time_str}.json",
            )
            os.makedirs(os.path.dirname(render_data_path), exist_ok=True)

            # 렌더 데이터 생성
            render_data = {
                "newsletter_topic": newsletter_topic,
                "generation_date": current_date,
                "generation_timestamp": current_time,
                "search_keywords": keywords,
                "sections": final_state.get("sections", []),
                # 추가 필드들...
                "recipient_greeting": final_state.get("recipient_greeting", "안녕하세요,"),
                "introduction_message": final_state.get(
                    "introduction_message",
                    "지난 한 주간의 주요 산업 동향을 정리해 드립니다.",
                ),
                "food_for_thought": final_state.get("food_for_thought"),
                "closing_message": final_state.get(
                    "closing_message",
                    "다음 주에 더 유익한 정보로 찾아뵙겠습니다. 감사합니다.",
                ),
                "editor_signature": final_state.get("editor_signature", "편집자 드림"),
                "company_name": final_state.get("company_name", "Your Newsletter Co."),
            }

            # 렌더 데이터 저장
            with open(render_data_path, "w", encoding="utf-8") as f:
                json.dump(render_data, f, ensure_ascii=False, indent=2)

            console.print(f"[green]Render data saved to {render_data_path}.[/green]")
            console.print("\n[bold green]Newsletter process completed.[/bold green]")

        else:
            console.print(f"[red]Unknown mode '{mode}'. Using 'template' mode.[/red]")
            mode = "template"
            # 이후 template 모드 실행 (중복 방지를 위해 생략)

    except Exception as e:
        console.print(f"[red]Error in test command: {e}[/red]")
        traceback.print_exc()


app.command()(check_config)
app.command()(check_llm)
app.command()(test_llm)
app.command()(list_providers)
app.command()(test_email)
app.command()(run)


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
    return tools.generate_keywords_with_gemini(domain, count=count)


if __name__ == "__main__":
    app()
