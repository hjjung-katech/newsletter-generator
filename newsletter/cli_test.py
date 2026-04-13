#!/usr/bin/env python3
# flake8: noqa
# mypy: disable-error-code=unreachable

import json
import os
import traceback
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console

from newsletter_core.application.generation import collect as news_collect

from . import tools

console = Console()


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
) -> None:
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
            from .template_paths import get_newsletter_template_dir

            template_dir = get_newsletter_template_dir()

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
