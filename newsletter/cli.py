import typer
from rich.console import Console
import os
from datetime import datetime
from typing import Optional, List
import json
import traceback

from dotenv import load_dotenv

# Explicitly load .env from the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
dotenv_path = os.path.join(project_root, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print(f"[DEBUG_CLI] Loaded .env file from: {dotenv_path}")  # Debug print
else:
    print(f"[DEBUG_CLI] .env file not found at: {dotenv_path}")  # Debug print

from . import collect as news_collect
from . import summarize as news_summarize
from . import compose as news_compose
from .compose import compose_newsletter_html, compose_compact_newsletter_html
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
    template_style: str = typer.Option(
        "compact",
        "--template-style",
        help="Newsletter template style: 'compact' (short, main news focused), 'detailed' (full length with all sections).",
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

            # Template style from config
            config_template_style = newsletter_settings.get("template_style")
            if config_template_style:
                # Only override if it's a valid option
                if config_template_style in ["compact", "detailed"]:
                    template_style = config_template_style
                    console.print(
                        f"[green]Using template_style from config file: {template_style}[/green]"
                    )
                else:
                    console.print(
                        f"[yellow]Invalid template_style in config file: {config_template_style}. Using default: {template_style}[/yellow]"
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

    # 날짜 및 시간 정보 설정
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")
    os.environ["GENERATION_DATE"] = current_date
    os.environ["GENERATION_TIMESTAMP"] = current_time

    console.print(f"[blue]Generation date: {current_date}, time: {current_time}[/blue]")

    html_content = ""

    # LangGraph를 사용하는 것이 이제 기본이자 유일한 방식입니다.
    console.print("\n[cyan]Using LangGraph workflow...[/cyan]")
    console.print(
        "\n[cyan]Step 1: Starting LangGraph workflow...[/cyan]"
    )  # LangGraph 워크플로우 실행

    # graph.generate_newsletter는 내부적으로 chains.get_newsletter_chain()을 호출하고,
    # chains.py의 변경으로 인해 render_data_langgraph...json 파일이 저장됩니다.
    # generate_newsletter는 (html_content, status)를 반환합니다.
    html_content, status = graph.generate_newsletter(
        keyword_list,
        news_period_days,
        domain=domain,
        template_style=template_style,  # 템플릿 스타일 추가
    )

    if status == "error":
        console.print(
            f"[yellow]Error in newsletter generation: {html_content}[/yellow]"
        )
        return

    console.print(
        f"[green]Newsletter generated successfully using {template_style} template via LangGraph.[/green]"
    )

    # 뉴스레터 주제 및 파일명 설정
    newsletter_topic = ""
    if domain:
        newsletter_topic = domain  # 도메인이 있으면 도메인 사용
    elif len(keyword_list) == 1:
        newsletter_topic = keyword_list[0]  # 단일 키워드면 해당 키워드 사용
    else:
        # 여러 키워드의 공통 주제 추출
        newsletter_topic = tools.extract_common_theme_from_keywords(keyword_list)

    current_date_str = datetime.now().strftime("%Y-%m-%d")
    current_time_str = datetime.now().strftime("%H%M%S")  # Add time for filename
    # 파일 이름에 안전한 주제 문자열 생성
    safe_topic = tools.get_filename_safe_theme(keyword_list, domain)
    filename_base = f"{current_date_str}_{current_time_str}_newsletter_{safe_topic}"

    # 뉴스레터 파일 저장
    if output_format:
        console.print(
            f"\n[cyan]Saving newsletter locally as {output_format.upper()}...[/cyan]"
        )
        save_path = os.path.join(output_directory, f"{filename_base}.{output_format}")
        console.print(f"[info]Saving to: {save_path}[/info]")

        if news_deliver.save_locally(
            html_content, filename_base, output_format, output_directory
        ):
            console.print(f"[green]Newsletter saved locally as {save_path}.[/green]")
            # 파일 존재 확인
            if os.path.exists(save_path):
                file_size = os.path.getsize(save_path)
                console.print(
                    f"[green]File created successfully - Size: {file_size} bytes[/green]"
                )
            else:
                console.print(
                    f"[bold red]Error: File was not created at {save_path}[/bold red]"
                )
        else:
            console.print(
                f"[yellow]Failed to save newsletter locally as {output_format.upper()}.[/yellow]"
            )

    # Google Drive에 저장(드라이브 옵션이 활성화된 경우)
    if drive:
        console.print(f"\n[cyan]Uploading to Google Drive...[/cyan]")
        if news_deliver.save_to_drive(html_content, filename_base, output_directory):
            console.print(
                "[green]Successfully uploaded newsletter to Google Drive.[/green]"
            )
        else:
            console.print(
                "[yellow]Failed to upload newsletter to Google Drive. Check your credentials.[/yellow]"
            )

    # 이메일 전송 로직 (LangGraph 경로에도 추가)
    if to:
        console.print(f"\n[cyan]Sending email to {to}...[/cyan]")
        email_subject = (
            f"주간 산업 동향 뉴스 클리핑: {newsletter_topic} ({current_date_str})"
        )
        if news_deliver.send_email(
            to_email=to, subject=email_subject, html_content=html_content
        ):
            console.print(f"[green]Email sent successfully to {to}.[/green]")
        else:
            console.print(f"[yellow]Failed to send email to {to}.[/yellow]")
    else:
        console.print(
            "\n[yellow]Email sending skipped as no recipient was provided.[/yellow]"
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
        output_dir = os.path.join(os.getcwd(), "output")
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, f"{filename_base}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        console.print(f"[green]Results saved to {output_path}[/green]")
    else:
        # 단순한 기사 목록을 텍스트로 저장
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
                "[cyan]Running in template mode - just re-rendering existing data[/cyan]"
            )

            # HTML 템플릿 로드
            from .chains import load_html_template
            from jinja2 import Template

            html_template_content = load_html_template()
            if not html_template_content:
                console.print("[red]Error: Failed to load HTML template.[/red]")
                raise typer.Exit(code=1)

            template = Template(html_template_content)

            # 렌더링
            console.print(
                f"[cyan]Rendering newsletter using loaded template and data...[/cyan]"
            )
            html_content = template.render(**data)

            # 파일명 생성 및 저장
            if output is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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
                output_filename = (
                    f"test_newsletter_result_{timestamp}_template_{topic_part}.html"
                )
                output = os.path.join("output", output_filename)

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

            # 파일 이름에 안전한 주제 문자열 생성
            from .tools import get_filename_safe_theme

            safe_topic = get_filename_safe_theme(keywords, domain)
            filename_base = (
                f"{current_date_str}_{current_time_str}_newsletter_{safe_topic}"
            )

            # 출력 파일명 설정
            if output is None:
                output_format = "html"
                save_path = os.path.join("output", f"{filename_base}.{output_format}")
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


if __name__ == "__main__":
    app()
