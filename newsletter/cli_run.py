#!/usr/bin/env python3
# flake8: noqa

import os
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console

from . import config
from .utils.logger import get_logger, set_log_level

console = Console()


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
) -> None:
    """
    Generate and optionally send a newsletter based on keywords or domain.

    This command creates a newsletter by searching for recent news articles,
    processing them using AI, and optionally sending via email or saving to various formats.
    """
    from newsletter_core.public.generation import (
        GenerateNewsletterRequest,
        NewsletterGenerationError,
    )
    from newsletter_core.public.generation import (
        generate_newsletter as generate_newsletter_public,
    )

    from . import deliver as news_deliver
    from . import tools

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
            console.print("\n[yellow]참고: Postmark에서 발송자 이메일 주소가 인증되어야 합니다.[/yellow]")
            raise typer.Exit(code=1)

        # POSTMARK_SERVER_TOKEN 설정 상태 확인
        if config.POSTMARK_SERVER_TOKEN:
            console.print("[green]✅ Postmark 토큰 설정 완료[/green]")
        else:
            console.print("[red]❌ POSTMARK_SERVER_TOKEN이 설정되지 않았습니다![/red]")
            console.print("[yellow]이메일 발송을 위해 Postmark 토큰 설정이 필요합니다.[/yellow]")
            console.print("[cyan].env 파일에 POSTMARK_SERVER_TOKEN을 추가하세요.[/cyan]")
            raise typer.Exit(code=1)

        # 이메일 호환 모드 권장
        if not email_compatible:
            console.print(
                "[yellow]💡 이메일 발송 시 --email-compatible 옵션 사용을 권장합니다.[/yellow]"
            )
            console.print("[yellow]   이 옵션은 이메일 클라이언트 호환성을 개선합니다.[/yellow]")

    elif email_compatible:
        console.print(
            "[yellow]💡 --email-compatible 옵션이 활성화되었지만 이메일 수신자가 지정되지 않았습니다.[/yellow]"
        )
        console.print("[yellow]   이메일 발송을 원하시면 --to 옵션을 추가하세요.[/yellow]")

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
        import yaml  # type: ignore[import-untyped]

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

    try:
        generation_result = generate_newsletter_public(
            GenerateNewsletterRequest(
                keywords=keyword_list,
                domain=domain,
                template_style=template_style,
                email_compatible=email_compatible,
                period=news_period_days,
                suggest_count=suggest_count,
            )
        )
    except NewsletterGenerationError as exc:
        logger.error(f"Error in newsletter generation: {exc}")
        return
    except Exception as exc:
        logger.error(f"Unexpected newsletter generation error: {exc}")
        return

    html_content = generation_result["html_content"]
    generation_stats = generation_result.get("generation_stats", {})
    step_times = generation_stats.get("step_times", {})
    total_time = generation_stats.get("total_time")
    cost_summary = generation_stats.get("cost_summary")

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
        with logger.step_context("local_save", f"뉴스레터를 {output_format.upper()}로 로컬 저장"):
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
            email_subject = f"주간 산업 동향 뉴스 클리핑: {newsletter_topic} ({current_date_str})"

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
