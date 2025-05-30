import json
import os
import traceback
from datetime import datetime
from typing import List, Optional

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
from .compose import compose_compact_newsletter_html, compose_newsletter_html

app = typer.Typer()
console = Console()


@app.command()
def run(
    config_file: Optional[str] = typer.Option(
        None,
        "--config",
        help="Path to the YAML configuration file. If provided, other options might be overridden.",
    ),
    keywords: Optional[str] = typer.Option(
        None,
        help="Keywords to search for, comma-separated. Used if --domain is not provided.",
    ),
    domain: Optional[str] = typer.Option(
        None,
        "--domain",
        help="Domain to generate keywords from. If provided, --keywords will be ignored unless keyword generation fails.",
    ),
    suggest_count: int = typer.Option(
        10,
        "--suggest-count",
        min=1,
        help="Number of keywords to generate if --domain is used.",
    ),
    news_period_days: int = typer.Option(
        14,
        "--period",
        "-p",
        min=1,
        help="Period in days for collecting recent news (default: 14 days).",
    ),
    to: Optional[str] = typer.Option(
        None,
        "--to",
        help="Email address to send the newsletter to. If not provided, email sending will be skipped.",
    ),
    output_format: Optional[str] = typer.Option(
        None,
        "--output-format",
        help="Format to save the newsletter locally (html or md). If not provided, saves to Drive if --drive is used, otherwise defaults to html.",
    ),
    template_style: str = typer.Option(
        "compact",
        "--template-style",
        help="Newsletter template style: 'compact' (short, main news focused) or 'detailed' (full length with all sections).",
    ),
    email_compatible: bool = typer.Option(
        False,
        "--email-compatible",
        help="Apply email compatibility processing (inline CSS, table layout). Recommended for email sending.",
    ),
    drive: bool = typer.Option(
        False,
        "--drive",
        help="Save the newsletter to Google Drive (HTML and Markdown).",
    ),
    filter_duplicates: bool = typer.Option(
        True,
        "--filter-duplicates/--no-filter-duplicates",
        help="Filter duplicate articles based on URL and title.",
    ),
    group_by_keywords: bool = typer.Option(
        True,
        "--group-by-keywords/--no-group-by-keywords",
        help="Group articles by keywords for better organization.",
    ),
    use_major_sources: bool = typer.Option(
        True,
        "--use-major-sources/--no-major-sources",
        help="Prioritize articles from major news sources.",
    ),
    track_cost: bool = typer.Option(
        False,
        "--track-cost",
        help="Enable LangSmith cost tracking during generation.",
    ),
    max_per_source: int = typer.Option(
        3, "--max-per-source", min=1, help="Maximum number of articles per source."
    ),
    log_level: str = typer.Option(
        "WARNING",
        "--log-level",
        help="Logging level: DEBUG, INFO, WARNING, ERROR",
    ),
):
    """
    Generate and optionally send a newsletter based on keywords or domain.

    This command creates a newsletter by searching for recent news articles,
    processing them using AI, and optionally sending via email or saving to various formats.
    """
    import time

    from . import deliver as news_deliver
    from . import graph, tools

    # 로깅 레벨 설정
    set_log_level(log_level)

    # 설정 정보 표시
    console.print(f"\n[bold blue]🚀 Newsletter Generator 시작[/bold blue]")
    console.print(f"[cyan]템플릿 스타일:[/cyan] {template_style}")
    console.print(
        f"[cyan]이메일 호환 모드:[/cyan] {'✅ 활성화' if email_compatible else '❌ 비활성화'}"
    )
    console.print(f"[cyan]뉴스 수집 기간:[/cyan] {news_period_days}일")

    # 이메일 발송 설정 확인 및 표시
    if to:
        console.print(f"\n[bold yellow]📧 이메일 발송 설정 확인[/bold yellow]")
        console.print(f"[cyan]수신자:[/cyan] {to}")

        # EMAIL_SENDER 설정 상태 확인 및 표시
        if config.EMAIL_SENDER:
            console.print(f"[cyan]발송자:[/cyan] {config.EMAIL_SENDER}")
            console.print("[green]✅ 이메일 발송자 설정 완료[/green]")
        else:
            console.print("[red]❌ EMAIL_SENDER가 설정되지 않았습니다![/red]")
            console.print("[yellow]이메일 발송을 위해 다음 설정이 필요합니다:[/yellow]")
            console.print("[cyan].env 파일에 다음을 추가하세요:[/cyan]")
            console.print("[cyan]EMAIL_SENDER=your_verified_sender@example.com[/cyan]")
            console.print("[cyan]POSTMARK_SERVER_TOKEN=your_postmark_token[/cyan]")
            console.print(
                "\n[yellow]참고: Postmark에서 발송자 이메일 주소가 인증되어야 합니다.[/yellow]"
            )
            raise typer.Exit(code=1)

        # POSTMARK_SERVER_TOKEN 설정 상태 확인
        if config.POSTMARK_SERVER_TOKEN:
            console.print("[green]✅ Postmark 토큰 설정 완료[/green]")
        else:
            console.print("[red]❌ POSTMARK_SERVER_TOKEN이 설정되지 않았습니다![/red]")
            console.print(
                "[yellow]이메일 발송을 위해 Postmark 토큰 설정이 필요합니다.[/yellow]"
            )
            console.print(
                "[cyan].env 파일에 POSTMARK_SERVER_TOKEN을 추가하세요.[/cyan]"
            )
            raise typer.Exit(code=1)

        # 이메일 호환 모드 권장
        if not email_compatible:
            console.print(
                "[yellow]💡 이메일 발송 시 --email-compatible 옵션 사용을 권장합니다.[/yellow]"
            )
            console.print(
                "[yellow]   이 옵션은 이메일 클라이언트 호환성을 개선합니다.[/yellow]"
            )

    elif email_compatible:
        console.print(
            "[yellow]💡 --email-compatible 옵션이 활성화되었지만 이메일 수신자가 지정되지 않았습니다.[/yellow]"
        )
        console.print(
            "[yellow]   이메일 발송을 원하시면 --to 옵션을 추가하세요.[/yellow]"
        )

    # 출력 형식 표시
    if output_format:
        console.print(f"[cyan]출력 형식:[/cyan] {output_format}")
    elif drive:
        console.print(f"[cyan]출력:[/cyan] Google Drive 저장")
    else:
        console.print(f"[cyan]출력:[/cyan] 로컬 HTML 파일")

    console.print("")  # 빈 줄 추가

    # 나머지 기존 로직 계속...

    # 로거 초기화
    logger = get_logger()

    # 나머지 코드는 그대로 유지
    if not output_format and not drive:
        logger.warning("No output option selected. Defaulting to local HTML save.")
        output_format = "html"  # Default to local html if no other option

    if track_cost:
        os.environ["ENABLE_COST_TRACKING"] = "1"

    # 기본 output_directory 설정
    output_directory = "./output"  # 기본값

    # config_file 처리
    if config_file:
        import yaml

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            # Extract settings from config_data
            newsletter_settings = config_data.get("newsletter_settings", {})

            # Override CLI options with config file values
            config_keywords = newsletter_settings.get("keywords")
            if config_keywords and not keywords:
                if isinstance(config_keywords, list):
                    keywords = ",".join(config_keywords)
                    logger.success(f"Using keywords from config file: {keywords}")
                else:
                    keywords = str(config_keywords)
                    logger.warning(
                        f"Keywords in config file is not a list. Converted to string: {keywords}"
                    )

            config_domain = newsletter_settings.get("domain")
            if config_domain and not domain:
                domain = config_domain
                logger.success(f"Using domain from config file: {domain}")

            config_suggest_count = newsletter_settings.get("suggest_count")
            if config_suggest_count:
                suggest_count = config_suggest_count
                logger.success(f"Using suggest_count from config file: {suggest_count}")

            config_output_format = newsletter_settings.get("output_format")
            if config_output_format and not output_format:
                output_format = config_output_format
                logger.success(f"Using output_format from config file: {output_format}")

            # Template style from config
            config_template_style = newsletter_settings.get("template_style")
            if config_template_style:
                # Only override if it's a valid option
                if config_template_style in ["compact", "detailed"]:
                    template_style = config_template_style
                    logger.success(
                        f"Using template_style from config file: {template_style}"
                    )
                else:
                    logger.warning(
                        f"Invalid template_style in config file: {config_template_style}. Using default: {template_style}"
                    )

            # Email compatibility from config
            config_email_compatible = newsletter_settings.get("email_compatible")
            if config_email_compatible is not None:
                email_compatible = bool(config_email_compatible)
                logger.success(
                    f"Using email_compatible from config file: {email_compatible}"
                )

            # Extract and log output directory from config
            output_directory = newsletter_settings.get(
                "output_directory", output_directory
            )
            logger.success(f"Output directory from config file: {output_directory}")

            # If email distribution is enabled in config, set it up
            distribution_settings = config_data.get("distribution", {})
            if distribution_settings.get("send_email") and not to:
                email_recipients = distribution_settings.get("email_recipients", [])
                if email_recipients and isinstance(email_recipients, list):
                    to = ",".join(email_recipients)
                    logger.success("Using email recipients from config file")

            logger.info(f"Loaded configuration from {config_file}")
        except Exception as e:
            logger.error(f"Failed to load or parse config file {config_file}: {e}")
            # Continue with CLI options

    # 디렉토리가 존재하는지 확인하고 생성
    os.makedirs(output_directory, exist_ok=True)

    # 뉴스레터 생성 정보 표시
    logger.show_newsletter_info(
        domain=domain or "키워드 기반",
        template_style=template_style,
        output_format=output_format or "html",
        recipient=to,
    )

    final_keywords_str = ""
    keyword_list = []

    if domain:
        with logger.step_context(
            "keyword_generation", f"도메인 '{domain}'에서 {suggest_count}개 키워드 생성"
        ):
            if not config.GEMINI_API_KEY:
                logger.error(
                    "GEMINI_API_KEY is not set. Cannot generate keywords from domain."
                )
                if not keywords:
                    logger.error("No fallback keywords provided. Exiting.")
                    raise typer.Exit(code=1)
                else:
                    logger.warning(f"Falling back to provided keywords: '{keywords}'")
                    final_keywords_str = keywords
            else:
                generated_keywords = tools.generate_keywords_with_gemini(
                    domain, count=suggest_count
                )
                if generated_keywords:
                    keyword_list = generated_keywords
                    final_keywords_str = ",".join(keyword_list)
                    logger.success(f"Generated keywords: {final_keywords_str}")
                else:
                    logger.warning(
                        f"Failed to generate keywords for domain '{domain}'."
                    )
                    if not keywords:
                        logger.error("No fallback keywords provided. Exiting.")
                        raise typer.Exit(code=1)
                    else:
                        logger.warning(
                            f"Falling back to provided keywords: '{keywords}'"
                        )
                        final_keywords_str = keywords
    elif keywords:
        final_keywords_str = keywords
    else:
        logger.error(
            "No keywords provided and no domain specified for keyword generation. Exiting."
        )
        raise typer.Exit(code=1)

    if not final_keywords_str:  # Should be caught by above, but as a safeguard
        logger.error("Keyword list is empty. Exiting.")
        raise typer.Exit(code=1)

    if (
        not keyword_list
    ):  # If domain was not used or failed and fell back to keywords string
        keyword_list = [
            kw.strip() for kw in final_keywords_str.split(",") if kw.strip()
        ]

    # 키워드 정보 표시
    logger.show_keyword_info(keyword_list, domain or "키워드 기반")

    # 날짜 및 시간 정보 설정
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")
    os.environ["GENERATION_DATE"] = current_date
    os.environ["GENERATION_TIMESTAMP"] = current_time

    logger.info(f"Generation date: {current_date}, time: {current_time}")

    html_content = ""

    # LangGraph를 사용하는 것이 이제 기본이자 유일한 방식입니다.
    logger.info("🔄 LangGraph 워크플로우 시작")

    # graph.generate_newsletter는 내부적으로 chains.get_newsletter_chain()을 호출하고,
    # chains.py의 변경으로 인해 render_data_langgraph...json 파일이 저장됩니다.
    # generate_newsletter는 (html_content, status)를 반환합니다.
    html_content, status = graph.generate_newsletter(
        keyword_list,
        news_period_days,
        domain=domain,
        template_style=template_style,  # 템플릿 스타일 추가
        email_compatible=email_compatible,  # 이메일 호환성 옵션 추가
    )

    if status == "error":
        logger.error(f"Error in newsletter generation: {html_content}")
        return

    info = graph.get_last_generation_info()
    step_times = info.get("step_times", {})
    total_time = info.get("total_time")
    cost_summary = info.get("cost_summary")

    # LangGraph의 세부 단계들을 logger에 추가하여 세분화된 시간 표시
    if step_times:
        # 단계 순서 정의 (표시 순서 보장)
        step_order = [
            "extract_theme",
            "collect_articles",
            "process_articles",
            "score_articles",
            "summarize_articles",
            "compose_newsletter",
        ]

        # 단계명을 한국어로 변환하여 표시
        korean_step_names = {
            "extract_theme": "Theme Extraction",
            "collect_articles": "Article Collection",
            "process_articles": "Article Processing",
            "score_articles": "Article Scoring",
            "summarize_articles": "Article Summarization",
            "compose_newsletter": "Newsletter Composition",
        }

        # 순서대로 step_times에 추가
        for step_name in step_order:
            if step_name in step_times:
                elapsed_time = step_times[step_name]
                korean_name = korean_step_names.get(
                    step_name, step_name.replace("_", " ").title()
                )
                logger.step_times[korean_name] = elapsed_time
                logger.update_statistics(f"step_time_{step_name}", elapsed_time)

    if total_time is not None:
        logger.update_statistics("total_generation_time", total_time)
        logger.info(f"Total generation time: {total_time:.2f} seconds")

    if cost_summary:
        logger.update_statistics("cost_summary", cost_summary)
        logger.debug(f"Cost summary: {cost_summary}")

    # 뉴스레터 주제 및 파일명 설정
    newsletter_topic = ""
    if domain:
        newsletter_topic = domain  # 도메인이 있으면 도메인 사용
    elif len(keyword_list) == 1:
        newsletter_topic = keyword_list[0]  # 단일 키워드면 해당 키워드 사용
    else:
        # 여러 키워드의 공통 주제 추출
        newsletter_topic = tools.extract_common_theme_from_keywords(keyword_list)

    # 통일된 파일명 생성 함수 사용
    from .utils.file_naming import generate_unified_newsletter_filename

    current_time_str = datetime.now().strftime("%H%M%S")  # Add time for filename
    # 날짜 문자열은 항상 정의 (이메일 제목에서 사용)
    current_date_str = datetime.now().strftime("%Y-%m-%d")

    # 파일 이름에 안전한 주제 문자열 생성
    safe_topic = tools.get_filename_safe_theme(keyword_list, domain)

    # 실제 파라미터를 반영한 스타일 설정
    effective_style = template_style
    if email_compatible:
        # email_compatible인 경우 "email_compatible"를 사용하되 파일명에는 original style 반영
        file_style = f"{template_style}_email_compatible"
    else:
        file_style = template_style

    # output_format이 지정된 경우 통일된 함수 사용
    if output_format:
        # 통일된 파일명 생성 (확장자 제외)
        full_file_path = generate_unified_newsletter_filename(
            topic=safe_topic,
            style=file_style,
            timestamp=f"{datetime.now().strftime('%Y%m%d')}_{current_time_str}",
            use_current_date=True,
            generation_type="original",
        )
        # .html 확장자를 제거하고 output_format으로 교체
        filename_base = os.path.splitext(os.path.basename(full_file_path))[0]
    else:
        # output_format이 없으면 기존 방식 호환성 유지 (새로운 날짜 형식 적용)
        style_suffix = f"_{file_style}" if file_style != "detailed" else ""
        filename_base = f"{current_date_str}_{current_time_str}_newsletter_{safe_topic}{style_suffix}"

    # 뉴스레터 파일 저장
    if output_format:
        with logger.step_context(
            "local_save", f"뉴스레터를 {output_format.upper()}로 로컬 저장"
        ):
            save_path = os.path.join(
                output_directory, f"{filename_base}.{output_format}"
            )
            logger.info(f"Saving to: {save_path}")

            if news_deliver.save_locally(
                html_content, filename_base, output_format, output_directory
            ):
                logger.success(f"Newsletter saved locally as {save_path}")
                # 파일 존재 확인
                if os.path.exists(save_path):
                    file_size = os.path.getsize(save_path)
                    logger.info(f"File created successfully - Size: {file_size} bytes")
                else:
                    logger.error(f"File was not created at {save_path}")
            else:
                logger.error(
                    f"Failed to save newsletter locally as {output_format.upper()}"
                )

    # Google Drive에 저장(드라이브 옵션이 활성화된 경우)
    if drive:
        with logger.step_context("drive_upload", "Google Drive에 업로드"):
            if news_deliver.save_to_drive(
                html_content, filename_base, output_directory
            ):
                logger.success("Successfully uploaded newsletter to Google Drive")
            else:
                logger.warning(
                    "Failed to upload newsletter to Google Drive. Check your credentials."
                )

    # 이메일 전송 로직 (LangGraph 경로에도 추가)
    if to:
        with logger.step_context("email_send", f"이메일 전송 to {to}"):
            email_subject = (
                f"주간 산업 동향 뉴스 클리핑: {newsletter_topic} ({current_date_str})"
            )

            # 이메일 발송 시 발송자 정보 다시 확인 및 표시
            console.print(f"\n[cyan]📤 이메일 발송 중...[/cyan]")
            console.print(f"[info]발송자: {config.EMAIL_SENDER}[/info]")
            console.print(f"[info]수신자: {to}[/info]")
            console.print(f"[info]제목: {email_subject}[/info]")

            if news_deliver.send_email(
                to_email=to, subject=email_subject, html_content=html_content
            ):
                logger.success(f"Email sent successfully to {to}")
                console.print(f"[green]✅ 이메일이 성공적으로 발송되었습니다![/green]")
            else:
                logger.warning(f"Failed to send email to {to}")
                console.print(f"[red]❌ 이메일 발송에 실패했습니다.[/red]")
    else:
        logger.info("Email sending skipped as no recipient was provided")

    # 시간 요약 및 최종 요약 표시
    logger.show_time_summary()
    logger.show_final_summary()

    logger.success("Newsletter process completed")


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

    with logger.step_context(
        "keyword_suggestion", f"도메인 '{domain}'에 대한 키워드 제안"
    ):
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
                "recipient_greeting": final_state.get(
                    "recipient_greeting", "안녕하세요,"
                ),
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


@app.command()
def check_config():
    """현재 설정 상태를 확인합니다 (이메일, LLM, 기타 설정)."""
    console.print("\n[bold blue]🔧 Newsletter Generator 설정 상태 확인[/bold blue]")
    console.print("=" * 60)

    # 1. 이메일 설정 확인
    console.print(f"\n[bold yellow]📧 이메일 발송 설정[/bold yellow]")

    # EMAIL_SENDER 확인
    if config.EMAIL_SENDER:
        console.print(f"[green]✅ EMAIL_SENDER:[/green] {config.EMAIL_SENDER}")
        console.print("   - Postmark에서 인증된 이메일 주소인지 확인하세요")
    else:
        console.print("[red]❌ EMAIL_SENDER:[/red] 설정되지 않음")
        console.print("   - .env 파일에 EMAIL_SENDER=your_email@domain.com 추가 필요")

    # POSTMARK_SERVER_TOKEN 확인
    if config.POSTMARK_SERVER_TOKEN:
        # 토큰의 일부만 표시 (보안상 전체 표시 안함)
        masked_token = (
            config.POSTMARK_SERVER_TOKEN[:8] + "..." + config.POSTMARK_SERVER_TOKEN[-4:]
            if len(config.POSTMARK_SERVER_TOKEN) > 12
            else "***"
        )
        console.print(f"[green]✅ POSTMARK_SERVER_TOKEN:[/green] {masked_token}")
    else:
        console.print("[red]❌ POSTMARK_SERVER_TOKEN:[/red] 설정되지 않음")
        console.print("   - .env 파일에 POSTMARK_SERVER_TOKEN=your_token 추가 필요")

    # 이메일 발송 가능 여부 종합 판단
    email_ready = config.EMAIL_SENDER and config.POSTMARK_SERVER_TOKEN
    if email_ready:
        console.print("\n[green]🎉 이메일 발송 설정 완료![/green]")
        console.print("   newsletter run --to your@email.com 명령어로 이메일 발송 가능")
    else:
        console.print("\n[red]⚠️  이메일 발송 설정 미완료[/red]")
        console.print("   위의 누락된 설정을 .env 파일에 추가해주세요")

    # 2. LLM 설정 확인
    console.print(f"\n[bold yellow]🤖 LLM 설정[/bold yellow]")

    # Gemini API Key 확인
    if config.GEMINI_API_KEY:
        masked_key = (
            config.GEMINI_API_KEY[:8] + "..." + config.GEMINI_API_KEY[-4:]
            if len(config.GEMINI_API_KEY) > 12
            else "***"
        )
        console.print(f"[green]✅ GEMINI_API_KEY:[/green] {masked_key}")
    else:
        console.print("[red]❌ GEMINI_API_KEY:[/red] 설정되지 않음")
        console.print("   - Gemini를 사용하려면 .env 파일에 GEMINI_API_KEY 추가 필요")

    # OpenAI API Key 확인 (선택사항)
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        masked_key = (
            openai_key[:8] + "..." + openai_key[-4:] if len(openai_key) > 12 else "***"
        )
        console.print(f"[green]✅ OPENAI_API_KEY:[/green] {masked_key}")
    else:
        console.print("[yellow]⚪ OPENAI_API_KEY:[/yellow] 설정되지 않음 (선택사항)")

    # Anthropic API Key 확인 (선택사항)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        masked_key = (
            anthropic_key[:8] + "..." + anthropic_key[-4:]
            if len(anthropic_key) > 12
            else "***"
        )
        console.print(f"[green]✅ ANTHROPIC_API_KEY:[/green] {masked_key}")
    else:
        console.print("[yellow]⚪ ANTHROPIC_API_KEY:[/yellow] 설정되지 않음 (선택사항)")

    # 3. Google Drive 설정 확인 (선택사항)
    console.print(f"\n[bold yellow]☁️  Google Drive 설정[/bold yellow]")

    credentials_path = "credentials.json"
    if os.path.exists(credentials_path):
        console.print(f"[green]✅ credentials.json:[/green] 파일 존재")
        console.print("   - Google Drive 저장 기능 사용 가능")
    else:
        console.print("[yellow]⚪ credentials.json:[/yellow] 파일 없음")
        console.print("   - Google Drive 저장 기능 비활성화 (선택사항)")

    # 4. 출력 디렉토리 확인
    console.print(f"\n[bold yellow]📁 출력 디렉토리[/bold yellow]")

    output_dir = "./output"
    if os.path.exists(output_dir):
        console.print(f"[green]✅ 출력 디렉토리:[/green] {output_dir}")
        # 디렉토리 내 파일 수 확인
        file_count = len(
            [
                f
                for f in os.listdir(output_dir)
                if os.path.isfile(os.path.join(output_dir, f))
            ]
        )
        console.print(f"   - 저장된 파일 수: {file_count}개")
    else:
        console.print(f"[yellow]⚪ 출력 디렉토리:[/yellow] {output_dir} (자동 생성됨)")

    # 5. 설정 파일 확인
    console.print(f"\n[bold yellow]⚙️  설정 파일[/bold yellow]")

    config_file = "config.yml"
    if os.path.exists(config_file):
        console.print(f"[green]✅ config.yml:[/green] 파일 존재")
        console.print("   - 사용자 정의 설정 적용 가능")
    else:
        console.print("[yellow]⚪ config.yml:[/yellow] 파일 없음")
        console.print("   - 기본 설정 사용 중 (선택사항)")

    env_file = ".env"
    if os.path.exists(env_file):
        console.print(f"[green]✅ .env:[/green] 파일 존재")
    else:
        console.print("[red]❌ .env:[/red] 파일 없음")
        console.print("   - .env.example을 복사하여 .env 파일 생성 필요")

    # 6. 종합 상태 요약
    console.print(f"\n[bold blue]📊 종합 상태 요약[/bold blue]")
    console.print("=" * 60)

    required_settings = [
        ("LLM API Key", config.GEMINI_API_KEY or openai_key or anthropic_key),
    ]

    optional_settings = [
        ("이메일 발송", email_ready),
        ("Google Drive", os.path.exists(credentials_path)),
        ("설정 파일", os.path.exists(config_file)),
    ]

    # 필수 설정 확인
    console.print("\n[bold]필수 설정:[/bold]")
    all_required_ok = True
    for name, status in required_settings:
        if status:
            console.print(f"  [green]✅ {name}[/green]")
        else:
            console.print(f"  [red]❌ {name}[/red]")
            all_required_ok = False

    # 선택 설정 확인
    console.print("\n[bold]선택 설정:[/bold]")
    for name, status in optional_settings:
        if status:
            console.print(f"  [green]✅ {name}[/green]")
        else:
            console.print(f"  [yellow]⚪ {name}[/yellow]")

    # 최종 상태 메시지
    if all_required_ok:
        console.print("\n[green]🎉 Newsletter Generator 사용 준비 완료![/green]")
        console.print("다음 명령어로 뉴스레터를 생성할 수 있습니다:")
        console.print(
            '[cyan]newsletter run --keywords "AI,머신러닝" --template-style compact[/cyan]'
        )

        if email_ready:
            console.print("\n이메일 발송도 가능합니다:")
            console.print(
                '[cyan]newsletter run --keywords "AI,머신러닝" --to your@email.com --email-compatible[/cyan]'
            )
    else:
        console.print("\n[red]⚠️  필수 설정이 미완료되었습니다.[/red]")
        console.print("위의 누락된 설정을 완료한 후 다시 시도해주세요.")
        console.print("\n도움이 필요하시면 다음 명령어를 실행하세요:")
        console.print("[cyan]newsletter check-llm[/cyan]  # LLM 설정 상세 확인")
        console.print(
            "[cyan]newsletter test-email --to your@email.com --dry-run[/cyan]  # 이메일 설정 테스트"
        )


@app.command()
def check_llm():
    """현재 사용 가능한 LLM 제공자와 설정을 확인합니다."""
    console.print("\n[bold blue]🤖 LLM 제공자 상태 확인[/bold blue]")

    try:
        from . import config
        from .llm_factory import get_available_providers, get_provider_info

        # 사용 가능한 제공자 확인
        available_providers = get_available_providers()
        provider_info = get_provider_info()

        console.print(
            f"\n[bold green]✅ 사용 가능한 제공자: {len(available_providers)}개[/bold green]"
        )

        for provider_name, info in provider_info.items():
            if info["available"]:
                console.print(f"  • [green]{provider_name}[/green] - 사용 가능")
            else:
                console.print(
                    f"  • [red]{provider_name}[/red] - 사용 불가 (API 키 없음)"
                )

        # 현재 LLM 설정 표시
        console.print(f"\n[bold blue]📋 현재 LLM 설정[/bold blue]")
        llm_config = config.LLM_CONFIG
        default_provider = llm_config.get("default_provider", "gemini")
        console.print(f"기본 제공자: [blue]{default_provider}[/blue]")

        # 작업별 설정 표시
        console.print(f"\n[bold blue]🔧 작업별 LLM 할당[/bold blue]")
        models_config = llm_config.get("models", {})

        for task, task_config in models_config.items():
            provider = task_config.get("provider", "N/A")
            model = task_config.get("model", "N/A")
            temp = task_config.get("temperature", "N/A")

            # 제공자 사용 가능 여부에 따라 색상 변경
            if provider in available_providers:
                provider_color = "green"
                status = "✅"
            else:
                provider_color = "red"
                status = "❌"

            console.print(
                f"  {status} {task}: [{provider_color}]{provider}[/{provider_color}] - {model} (temp: {temp})"
            )

        # 권장사항 표시
        if len(available_providers) == 0:
            console.print(
                f"\n[bold red]⚠️  경고: 사용 가능한 LLM 제공자가 없습니다![/bold red]"
            )
            console.print("다음 중 하나 이상의 API 키를 .env 파일에 설정해주세요:")
            console.print("  • GEMINI_API_KEY")
            console.print("  • OPENAI_API_KEY")
            console.print("  • ANTHROPIC_API_KEY")
        elif len(available_providers) == 1:
            console.print(
                f"\n[yellow]💡 권장사항: 더 나은 fallback을 위해 추가 LLM 제공자를 설정하는 것을 권장합니다.[/yellow]"
            )
        else:
            console.print(
                f"\n[green]🎉 좋습니다! 여러 LLM 제공자가 설정되어 있어 안정적인 서비스가 가능합니다.[/green]"
            )

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")


@app.command()
def test_llm(
    task: str = typer.Option(
        "keyword_generation",
        "--task",
        help="테스트할 작업 유형 (keyword_generation, theme_extraction, news_summarization 등)",
    ),
    prompt: str = typer.Option(
        "안녕하세요. 이것은 테스트 메시지입니다.",
        "--prompt",
        help="테스트에 사용할 프롬프트",
    ),
):
    """특정 작업에 대한 LLM 응답을 테스트합니다."""
    console.print(f"\n[bold blue]🧪 LLM 테스트: {task}[/bold blue]")

    try:
        import time

        from .llm_factory import get_llm_for_task

        # LLM 생성
        console.print(f"[cyan]LLM 생성 중...[/cyan]")
        llm = get_llm_for_task(task, enable_fallback=False)
        console.print(f"[green]✅ LLM 생성 완료: {type(llm).__name__}[/green]")

        # 테스트 실행
        console.print(f"[cyan]테스트 실행 중...[/cyan]")
        console.print(f"프롬프트: {prompt}")

        start_time = time.time()
        response = llm.invoke(prompt)
        end_time = time.time()

        # 결과 출력
        response_time = end_time - start_time
        response_text = str(response).strip()

        console.print(f"\n[bold green]📝 응답 결과[/bold green]")
        console.print(f"응답 시간: {response_time:.2f}초")
        console.print(f"응답 길이: {len(response_text)}자")
        console.print(f"\n[blue]응답 내용:[/blue]")
        console.print(response_text)

    except Exception as e:
        console.print(f"[bold red]❌ 테스트 실패: {e}[/bold red]")

        # 429 에러인 경우 특별한 안내
        if "429" in str(e) or "quota" in str(e).lower():
            console.print(
                f"[yellow]💡 API 할당량이 초과된 것 같습니다. 다른 LLM 제공자를 사용해보세요.[/yellow]"
            )
            console.print(
                f"[yellow]   'newsletter check-llm' 명령어로 사용 가능한 제공자를 확인하세요.[/yellow]"
            )


@app.command()
def list_providers():
    """사용 가능한 LLM 제공자와 모델 정보를 표시합니다."""
    try:
        from . import config
        from .llm_factory import get_available_providers, get_provider_info

        console.print("\n[bold cyan]LLM 제공자 정보[/bold cyan]")
        console.print("=" * 50)

        # 사용 가능한 제공자 목록 표시
        available_providers = get_available_providers()
        console.print(
            f"\n[green]사용 가능한 제공자:[/green] {', '.join(available_providers) if available_providers else '없음'}"
        )

        # 기본 제공자 표시
        default_provider = config.LLM_CONFIG.get("default_provider", "gemini")
        console.print(f"[blue]기본 제공자:[/blue] {default_provider}")

        # 각 제공자의 상세 정보 표시
        provider_info = get_provider_info()
        for provider_name, info in provider_info.items():
            status = "[green]✓[/green]" if info["available"] else "[red]✗[/red]"
            console.print(f"\n{status} [bold]{provider_name.upper()}[/bold]")

            if info["available"]:
                models = info.get("models", {})
                if models:
                    console.print(f"  Fast: {models.get('fast', 'N/A')}")
                    console.print(f"  Standard: {models.get('standard', 'N/A')}")
                    console.print(f"  Advanced: {models.get('advanced', 'N/A')}")
            else:
                api_key_name = config.LLM_CONFIG.get("api_keys", {}).get(
                    provider_name, f"{provider_name.upper()}_API_KEY"
                )
                console.print(
                    f"  [yellow]API 키가 설정되지 않음: {api_key_name}[/yellow]"
                )

        # 기능별 모델 설정 표시
        console.print(f"\n[bold cyan]기능별 모델 설정[/bold cyan]")
        console.print("=" * 50)

        models_config = config.LLM_CONFIG.get("models", {})
        for task, task_config in models_config.items():
            provider = task_config.get("provider", "N/A")
            model = task_config.get("model", "N/A")
            temp = task_config.get("temperature", "N/A")
            console.print(f"{task}: [blue]{provider}[/blue] - {model} (temp: {temp})")

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")


@app.command()
def test_email(
    to: str = typer.Option(
        ...,
        "--to",
        help="Email address to send the test email to.",
    ),
    subject: Optional[str] = typer.Option(
        None,
        "--subject",
        help="Custom subject for the test email. If not provided, a default test subject will be used.",
    ),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        help="Path to HTML file to use as email content. If not provided, a simple test message will be sent.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Perform a dry run without actually sending the email. Shows what would be sent.",
    ),
):
    """
    Test email sending functionality using Postmark.

    This command allows you to test the email delivery system without generating a full newsletter.
    You can send a simple test message or use an existing HTML file as the email content.
    """
    console.print(f"\n[bold blue]📧 이메일 발송 테스트[/bold blue]")

    # EMAIL_SENDER 설정 상태 확인 및 표시
    console.print(f"\n[bold yellow]📋 이메일 설정 확인[/bold yellow]")

    # EMAIL_SENDER 상태 확인
    if config.EMAIL_SENDER:
        console.print(f"[cyan]발송자 이메일:[/cyan] {config.EMAIL_SENDER}")
        console.print("[green]✅ EMAIL_SENDER 설정 완료[/green]")
    else:
        console.print("[red]❌ EMAIL_SENDER가 설정되지 않았습니다![/red]")
        console.print("[yellow]이메일 발송을 위해 다음 설정이 필요합니다:[/yellow]")
        console.print("[cyan].env 파일에 다음을 추가하세요:[/cyan]")
        console.print("[cyan]EMAIL_SENDER=your_verified_sender@example.com[/cyan]")
        console.print("[cyan]POSTMARK_SERVER_TOKEN=your_postmark_token[/cyan]")
        console.print(
            "\n[yellow]참고: EMAIL_SENDER는 Postmark에서 인증된 이메일 주소여야 합니다.[/yellow]"
        )
        if not dry_run:
            raise typer.Exit(code=1)

    # POSTMARK_SERVER_TOKEN 상태 확인
    if config.POSTMARK_SERVER_TOKEN:
        console.print("[green]✅ POSTMARK_SERVER_TOKEN 설정 완료[/green]")
        # 토큰의 일부만 표시 (보안상 전체 표시 안함)
        masked_token = (
            config.POSTMARK_SERVER_TOKEN[:8] + "..." + config.POSTMARK_SERVER_TOKEN[-4:]
            if len(config.POSTMARK_SERVER_TOKEN) > 12
            else "***"
        )
        console.print(f"[cyan]Postmark 토큰:[/cyan] {masked_token}")
    else:
        console.print("[red]❌ POSTMARK_SERVER_TOKEN이 설정되지 않았습니다![/red]")
        console.print(
            "[yellow]이메일 발송을 위해 Postmark 토큰 설정이 필요합니다.[/yellow]"
        )
        console.print("[cyan].env 파일에 POSTMARK_SERVER_TOKEN을 추가하세요.[/cyan]")
        if not dry_run:
            raise typer.Exit(code=1)

    console.print(f"[cyan]수신자:[/cyan] {to}")

    # Set default subject if not provided
    if not subject:
        subject = f"Newsletter Generator 이메일 테스트 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # Prepare email content
    if template and os.path.exists(template):
        console.print(f"[cyan]Using template file: {template}[/cyan]")
        try:
            with open(template, "r", encoding="utf-8") as f:
                html_content = f.read()
            console.print(
                f"[green]Template loaded successfully ({len(html_content)} characters)[/green]"
            )
        except Exception as e:
            console.print(f"[red]Error reading template file: {e}[/red]")
            raise typer.Exit(code=1)
    else:
        if template:
            console.print(f"[yellow]Template file not found: {template}[/yellow]")
            console.print("[yellow]Using default test content instead[/yellow]")

        # Default test content
        html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>이메일 테스트</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f4f4f4;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #007bff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .content {{
            margin-bottom: 30px;
        }}
        .footer {{
            text-align: center;
            font-size: 0.9em;
            color: #666;
            border-top: 1px solid #eee;
            padding-top: 20px;
        }}
        .success {{
            background-color: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #28a745;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📧 Newsletter Generator 이메일 테스트</h1>
        </div>
        
        <div class="content">
            <div class="success">
                <h2>✅ 이메일 발송 테스트 성공!</h2>
                <p>이 이메일을 받으셨다면 Newsletter Generator의 Postmark 이메일 발송 기능이 정상적으로 작동하고 있습니다.</p>
            </div>
            
            <h3>📋 테스트 정보</h3>
            <ul>
                <li><strong>발송 시간:</strong> {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분 %S초')}</li>
                <li><strong>수신자:</strong> {to}</li>
                <li><strong>이메일 서비스:</strong> Postmark API</li>
                <li><strong>발송자:</strong> {config.EMAIL_SENDER}</li>
            </ul>
            
            <h3>🔧 다음 단계</h3>
            <p>이메일 테스트가 성공했다면 이제 실제 뉴스레터를 생성하고 발송할 수 있습니다:</p>
            <pre style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto;">
newsletter run --keywords "AI,머신러닝" --to {to} --output-format html
            </pre>
        </div>
        
        <div class="footer">
            <p>이 메시지는 Newsletter Generator의 이메일 테스트 기능에 의해 자동으로 생성되었습니다.</p>
            <p>문의사항이 있으시면 개발팀에 연락해 주세요.</p>
        </div>
    </div>
</body>
</html>
        """

    if dry_run:
        console.print(
            "\n[yellow]🔍 DRY RUN MODE - 실제 이메일은 발송되지 않습니다[/yellow]"
        )
        console.print(f"[cyan]수신자:[/cyan] {to}")
        console.print(f"[cyan]제목:[/cyan] {subject}")
        console.print(f"[cyan]내용 길이:[/cyan] {len(html_content)} 문자")
        console.print(
            f"[cyan]Postmark 토큰 설정 여부:[/cyan] {'✅ 설정됨' if config.POSTMARK_SERVER_TOKEN else '❌ 설정되지 않음'}"
        )
        console.print(f"[cyan]발송자 이메일:[/cyan] {config.EMAIL_SENDER}")

        if not config.POSTMARK_SERVER_TOKEN:
            console.print(
                "\n[red]⚠️  POSTMARK_SERVER_TOKEN이 설정되지 않았습니다.[/red]"
            )
            console.print(
                "[yellow].env 파일에 POSTMARK_SERVER_TOKEN을 설정해주세요.[/yellow]"
            )

        console.print(
            "\n[green]Dry run 완료. 실제 발송하려면 --dry-run 옵션을 제거하세요.[/green]"
        )
        return

    # Check Postmark configuration
    if not config.POSTMARK_SERVER_TOKEN:
        console.print("\n[red]❌ POSTMARK_SERVER_TOKEN이 설정되지 않았습니다.[/red]")
        console.print(
            "[yellow]이메일 발송을 위해 .env 파일에 다음을 설정해주세요:[/yellow]"
        )
        console.print("[cyan]POSTMARK_SERVER_TOKEN=your_postmark_server_token[/cyan]")
        console.print("[cyan]EMAIL_SENDER=your_verified_sender@example.com[/cyan]")
        raise typer.Exit(code=1)

    if not config.EMAIL_SENDER:
        console.print("\n[red]❌ EMAIL_SENDER가 설정되지 않았습니다.[/red]")
        console.print("[yellow].env 파일에 EMAIL_SENDER를 설정해주세요:[/yellow]")
        console.print("[cyan]EMAIL_SENDER=your_verified_sender@example.com[/cyan]")
        raise typer.Exit(code=1)

    # Send the test email
    console.print(f"\n[cyan]📤 이메일 발송 중...[/cyan]")
    console.print(f"[info]발송자: {config.EMAIL_SENDER}[/info]")
    console.print(f"[info]수신자: {to}[/info]")
    console.print(f"[info]제목: {subject}[/info]")

    try:
        success = news_deliver.send_email(
            to_email=to, subject=subject, html_content=html_content
        )

        if success:
            console.print(
                f"\n[bold green]✅ 이메일이 성공적으로 발송되었습니다![/bold green]"
            )
            console.print(f"[green]수신자 {to}의 받은편지함을 확인해주세요.[/green]")

            # Save test email content for reference
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = "./output"
            os.makedirs(output_dir, exist_ok=True)
            test_file_path = os.path.join(output_dir, f"test_email_{timestamp}.html")

            try:
                with open(test_file_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                console.print(
                    f"[info]테스트 이메일 내용이 저장되었습니다: {test_file_path}[/info]"
                )
            except Exception as e:
                console.print(f"[yellow]테스트 파일 저장 실패: {e}[/yellow]")

        else:
            console.print(f"\n[bold red]❌ 이메일 발송에 실패했습니다.[/bold red]")
            console.print(
                "[yellow]Postmark 설정과 네트워크 연결을 확인해주세요.[/yellow]"
            )
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(
            f"\n[bold red]❌ 이메일 발송 중 오류가 발생했습니다: {e}[/bold red]"
        )
        console.print("[yellow]설정을 확인하고 다시 시도해주세요.[/yellow]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
