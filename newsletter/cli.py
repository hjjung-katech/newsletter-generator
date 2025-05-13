import typer
from rich.console import Console
import os
from datetime import datetime
from typing import Optional, List

from . import collect as news_collect
from . import summarize as news_summarize
from . import compose as news_compose
from . import deliver as news_deliver
from . import config
from . import graph  # 새로운 LangGraph 모듈 임포트
from . import tools  # Import the tools module

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
    drive: bool = typer.Option(
        False,
        "--drive",
        help="Save the newsletter to Google Drive (HTML and Markdown).",
    ),
    use_langgraph: bool = typer.Option(
        True, "--langgraph/--no-langgraph", help="Use LangGraph workflow (recommended)."
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
    max_per_source: int = typer.Option(
        3, "--max-per-source", min=1, help="Maximum number of articles per source."
    ),
):
    """
    Run the newsletter generation and saving process.
    Can generate keywords from a domain or use provided keywords, or load from a config file.
    """
    # 나머지 코드는 그대로 유지
    if not output_format and not drive:
        console.print(
            "[yellow]No output option selected. Defaulting to local HTML save.[/yellow]"
        )
        output_format = "html"  # Default to local html if no other option

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
                    console.print(
                        f"[green]Using keywords from config file: {keywords}[/green]"
                    )
                else:
                    keywords = str(config_keywords)
                    console.print(
                        f"[yellow]Keywords in config file is not a list. Converted to string: {keywords}[/yellow]"
                    )

            config_domain = newsletter_settings.get("domain")
            if config_domain and not domain:
                domain = config_domain
                console.print(f"[green]Using domain from config file: {domain}[/green]")

            config_suggest_count = newsletter_settings.get("suggest_count")
            if config_suggest_count:
                suggest_count = config_suggest_count
                console.print(
                    f"[green]Using suggest_count from config file: {suggest_count}[/green]"
                )

            config_output_format = newsletter_settings.get("output_format")
            if config_output_format and not output_format:
                output_format = config_output_format
                console.print(
                    f"[green]Using output_format from config file: {output_format}[/green]"
                )

            # Extract and log output directory from config
            output_directory = newsletter_settings.get(
                "output_directory", output_directory
            )
            console.print(
                f"[green]Output directory from config file: {output_directory}[/green]"
            )

            # If email distribution is enabled in config, set it up
            distribution_settings = config_data.get("distribution", {})
            if distribution_settings.get("send_email") and not to:
                email_recipients = distribution_settings.get("email_recipients", [])
                if email_recipients and isinstance(email_recipients, list):
                    to = ",".join(email_recipients)
                    console.print(
                        f"[green]Using email recipients from config file[/green]"
                    )

            console.print(f"[info]Loaded configuration from {config_file}[/info]")
        except Exception as e:
            console.print(
                f"[error]Failed to load or parse config file {config_file}: {e}[/error]"
            )
            # Continue with CLI options

    # 디렉토리가 존재하는지 확인하고 생성
    os.makedirs(output_directory, exist_ok=True)

    final_keywords_str = ""
    keyword_list = []

    if domain:
        console.print(
            f"[bold green]Attempting to generate {suggest_count} keywords for domain: '{domain}'[/bold green]"
        )
        if not config.GEMINI_API_KEY:
            console.print(
                "[bold red]Error: GEMINI_API_KEY is not set. Cannot generate keywords from domain.[/bold red]"
            )
            if not keywords:
                console.print(
                    "[bold red]No fallback keywords provided. Exiting.[/bold red]"
                )
                raise typer.Exit(code=1)
            else:
                console.print(
                    f"[yellow]Falling back to provided keywords: '{keywords}'[/yellow]"
                )
                final_keywords_str = keywords
        else:
            generated_keywords = tools.generate_keywords_with_gemini(
                domain, count=suggest_count
            )
            if generated_keywords:
                keyword_list = generated_keywords
                final_keywords_str = ",".join(keyword_list)
                console.print(
                    f"[bold blue]Generated keywords: {final_keywords_str}[/bold blue]"
                )
            else:
                console.print(
                    f"[yellow]Failed to generate keywords for domain '{domain}'.[/yellow]"
                )
                if not keywords:
                    console.print(
                        "[bold red]No fallback keywords provided. Exiting.[/bold red]"
                    )
                    raise typer.Exit(code=1)
                else:
                    console.print(
                        f"[yellow]Falling back to provided keywords: '{keywords}'[/yellow]"
                    )
                    final_keywords_str = keywords
    elif keywords:
        final_keywords_str = keywords
    else:
        console.print(
            "[bold red]Error: No keywords provided and no domain specified for keyword generation. Exiting.[/bold red]"
        )
        raise typer.Exit(code=1)

    if not final_keywords_str:  # Should be caught by above, but as a safeguard
        console.print("[bold red]Error: Keyword list is empty. Exiting.[/bold red]")
        raise typer.Exit(code=1)

    if (
        not keyword_list
    ):  # If domain was not used or failed and fell back to keywords string
        keyword_list = [
            kw.strip() for kw in final_keywords_str.split(",") if kw.strip()
        ]

    console.print(
        f"[bold green]Starting newsletter generation for final keywords: '{final_keywords_str}'[/bold green]"
    )
    if output_format:
        console.print(f"[bold green]Local output format: {output_format}[/bold green]")
    if drive:
        console.print(f"[bold green]Save to Google Drive: Enabled[/bold green]")

    # 날짜 정보 설정
    os.environ["GENERATION_DATE"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html_content = ""

    # LangGraph를 사용하는 경우
    if use_langgraph:
        console.print("\n[cyan]Using LangGraph workflow...[/cyan]")
        console.print(
            "\n[cyan]Step 1: Starting LangGraph workflow...[/cyan]"
        )  # LangGraph 워크플로우 실행
        html_content, status = graph.generate_newsletter(
            keyword_list, news_period_days
        )  # Use the final keyword_list and news period

        if status == "error":
            console.print(
                f"[yellow]Error in newsletter generation: {html_content}[/yellow]"
            )
            return

        console.print(
            "[green]Newsletter generated successfully using LangGraph.[/green]"
        )

    # 기존 방식 사용하는 경우
    else:
        # 1. Collect articles
        console.print("\n[cyan]Step 1: Collecting articles...[/cyan]")
        articles = news_collect.collect_articles(
            final_keywords_str,
            max_per_source=max_per_source,
            filter_duplicates=filter_duplicates,
            group_by_keywords=group_by_keywords,
            use_major_sources_filter=use_major_sources,
        )  # Use final_keywords_str for collection
        if not articles:
            console.print("[yellow]No articles found. Exiting.[/yellow]")
            return

        # 그룹화된 결과인 경우 출력 형식 변경
        if isinstance(articles, dict):
            total_articles = sum(len(group) for group in articles.values())
            console.print(
                f"Collected {total_articles} articles grouped by {len(articles)} keywords."
            )
            for keyword, keyword_articles in articles.items():
                console.print(f"- {keyword}: {len(keyword_articles)} articles")
        else:
            console.print(f"Collected {len(articles)} articles.")

        # 2. Summarize articles
        console.print("\n[cyan]Step 2: Summarizing articles...[/cyan]")
        summaries = news_summarize.summarize_articles(
            keyword_list, articles
        )  # Use final keyword_list for summarization context
        if not summaries:
            console.print("[yellow]Failed to summarize articles. Exiting.[/yellow]")
            return  # 이제 summaries는 HTML 문자열이므로 변수명을 변경
        html_content = summaries
        console.print(
            "\n[green]Newsletter generated successfully using legacy pipeline.[/green]"
        )

    current_date_str = datetime.now().strftime("%Y-%m-%d")
    filename_base = f"{current_date_str}_newsletter_{final_keywords_str.replace(',', '_').replace(' ', '')}"  # Use final_keywords_str

    # 3. Send email
    step_num = 3  # 현재 단계 번호 추적

    if to:
        console.print(f"\n[cyan]Step {step_num}: Sending email...[/cyan]")
        email_subject = (
            f"오늘의 뉴스레터: {final_keywords_str}"  # Use final_keywords_str
        )
        news_deliver.send_email(
            to_email=to, subject=email_subject, html_content=html_content
        )
    else:
        console.print(
            f"\n[yellow]Step {step_num}: Email sending skipped as no recipient was provided.[/yellow]"
        )

    step_num += 1

    # 4. Save or Upload
    saved_locally = False
    if output_format:
        console.print(
            f"\n[cyan]Step {step_num}: Saving newsletter locally as {output_format.upper()}...[/cyan]"
        )
        save_path = os.path.join(output_directory, f"{filename_base}.{output_format}")
        if news_deliver.save_locally(
            html_content, filename_base, output_format, output_directory
        ):
            console.print(f"Newsletter saved locally as {save_path}.")
            saved_locally = True
        else:
            console.print(
                f"[yellow]Failed to save newsletter locally as {output_format.upper()}.[/yellow]"
            )

    step_num += 1

    # 5. Upload to Google Drive
    if drive:
        console.print(f"\n[cyan]Step {step_num}: Uploading to Google Drive...[/cyan]")
        if news_deliver.save_to_drive(html_content, filename_base, output_directory):
            console.print(
                "[green]Successfully uploaded newsletter to Google Drive.[/green]"
            )
        else:
            console.print(
                "[yellow]Failed to upload newsletter to Google Drive. Check your credentials.[/yellow]"
            )

    if not saved_locally and not drive:
        console.print(
            "\n[yellow]Warning: Newsletter was not saved locally or uploaded to Google Drive.[/yellow]"
        )
        console.print(
            "[yellow]Use --output-format=html or --drive to save/upload the newsletter.[/yellow]"
        )

    console.print("\n[bold green]Newsletter process completed.[/bold green]")


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
):
    """
    Collect articles based on keywords with improved filtering and grouping.
    """
    console.print(f"Collecting articles for keywords: {keywords}")

    # 기사 수집 및 처리
    articles = news_collect.collect_articles(
        keywords,
        max_per_source=max_per_source,
        filter_duplicates=not no_filter_duplicates,
        group_by_keywords=not no_group_by_keywords,
        use_major_sources_filter=not no_major_sources_filter,
    )

    # 결과 출력
    if isinstance(articles, dict):  # 그룹화된 결과인 경우
        console.print(
            f"[green]Collected articles grouped by {len(articles)} keywords:[/green]"
        )
        for keyword, keyword_articles in articles.items():
            console.print(
                f"[bold cyan]Keyword: {keyword} - {len(keyword_articles)} articles[/bold cyan]"
            )
            for i, article in enumerate(keyword_articles, 1):
                console.print(
                    f"  {i}. {article.get('title', 'No title')} ({article.get('source', 'Unknown')})"
                )
    else:  # 그룹화되지 않은 결과인 경우
        console.print(f"[green]Collected {len(articles)} articles:[/green]")
        for i, article in enumerate(articles, 1):
            console.print(
                f"{i}. {article.get('title', 'No title')} ({article.get('source', 'Unknown')})"
            )

    # 생성 날짜 설정
    current_date_str = datetime.now().strftime("%Y-%m-%d")
    # 파일 이름 생성
    filename_base = f"{current_date_str}_collected_articles_{keywords.replace(',', '_').replace(' ', '')}"

    # 결과 저장
    if isinstance(articles, dict):
        # 그룹화된 결과를 JSON으로 저장
        import json

        output_dir = os.path.join(os.getcwd(), "output")
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, f"{filename_base}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        console.print(f"[green]Results saved to {output_path}[/green]")
    else:
        # 단순한 기사 목록을 텍스트로 저장
        import json

        output_dir = os.path.join(os.getcwd(), "output")
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, f"{filename_base}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        console.print(f"[green]Results saved to {output_path}[/green]")


@app.command()
def suggest(
    domain: str = typer.Option(..., "--domain", help="Domain to suggest keywords for."),
    count: int = typer.Option(
        10, "--count", min=1, help="Number of keywords to generate."
    ),
):
    """
    Suggests trend keywords for a given domain using Google Gemini.
    """
    console.print(
        f"[bold green]Suggesting {count} keywords for domain: '{domain}'[/bold green]"
    )

    if not config.GEMINI_API_KEY:  # GOOGLE_API_KEY 대신 GEMINI_API_KEY 사용
        console.print(
            "[bold red]Error: GEMINI_API_KEY is not set in the environment variables or .env file.[/bold red]"
        )
        console.print("Please set it to use the keyword suggestion feature.")
        raise typer.Exit(code=1)

    suggested_keywords = tools.generate_keywords_with_gemini(domain, count=count)

    if suggested_keywords:
        console.print("\n[bold blue]Suggested Keywords:[/bold blue]")
        for keyword in suggested_keywords:
            console.print(f"- {keyword}")

        # Construct the command for the user
        keywords_str = ",".join(suggested_keywords)
        run_command = f'newsletter run --keywords "{keywords_str}"'
        console.print(
            f"\n[bold yellow]To generate a newsletter with these keywords, you can use the following command:[/bold yellow]"
        )
        console.print(f"[cyan]{run_command}[/cyan]")
    else:
        console.print(
            "\n[yellow]Could not generate keywords for the given domain. Please check the logs for errors.[/yellow]"
        )


if __name__ == "__main__":
    app()
