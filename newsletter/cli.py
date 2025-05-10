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
from . import tools # Import the tools module

app = typer.Typer()
console = Console()

@app.command()
def run(
    keywords: Optional[str] = typer.Option(None, help="Keywords to search for, comma-separated. Used if --domain is not provided."),
    domain: Optional[str] = typer.Option(None, "--domain", help="Domain to generate keywords from. If provided, --keywords will be ignored unless keyword generation fails."),
    suggest_count: int = typer.Option(10, "--suggest-count", min=1, help="Number of keywords to generate if --domain is used."),
    to: Optional[str] = typer.Option(None, "--to", help="Email address to send the newsletter to. If not provided, email sending will be skipped."),
    output_format: Optional[str] = typer.Option(None, "--output-format", help="Format to save the newsletter locally (html or md). If not provided, saves to Drive if --drive is used, otherwise defaults to html."),
    drive: bool = typer.Option(False, "--drive", help="Save the newsletter to Google Drive (HTML and Markdown)."),
    use_langgraph: bool = typer.Option(True, "--langgraph/--no-langgraph", help="Use LangGraph workflow (recommended).")
):
    """
    Run the newsletter generation and saving process.
    Can generate keywords from a domain or use provided keywords.
    """
    if not output_format and not drive:
        console.print("[yellow]No output option selected. Defaulting to local HTML save.[/yellow]")
        output_format = "html" # Default to local html if no other option

    final_keywords_str = ""
    keyword_list = []

    if domain:
        console.print(f"[bold green]Attempting to generate {suggest_count} keywords for domain: '{domain}'[/bold green]")
        if not config.GEMINI_API_KEY:
            console.print("[bold red]Error: GEMINI_API_KEY is not set. Cannot generate keywords from domain.[/bold red]")
            if not keywords:
                console.print("[bold red]No fallback keywords provided. Exiting.[/bold red]")
                raise typer.Exit(code=1)
            else:
                console.print(f"[yellow]Falling back to provided keywords: '{keywords}'[/yellow]")
                final_keywords_str = keywords
        else:
            generated_keywords = tools.generate_keywords_with_gemini(domain, count=suggest_count)
            if generated_keywords:
                keyword_list = generated_keywords
                final_keywords_str = ",".join(keyword_list)
                console.print(f"[bold blue]Generated keywords: {final_keywords_str}[/bold blue]")
            else:
                console.print(f"[yellow]Failed to generate keywords for domain '{domain}'.[/yellow]")
                if not keywords:
                    console.print("[bold red]No fallback keywords provided. Exiting.[/bold red]")
                    raise typer.Exit(code=1)
                else:
                    console.print(f"[yellow]Falling back to provided keywords: '{keywords}'[/yellow]")
                    final_keywords_str = keywords
    elif keywords:
        final_keywords_str = keywords
    else:
        console.print("[bold red]Error: No keywords provided and no domain specified for keyword generation. Exiting.[/bold red]")
        raise typer.Exit(code=1)
    
    if not final_keywords_str: # Should be caught by above, but as a safeguard
        console.print("[bold red]Error: Keyword list is empty. Exiting.[/bold red]")
        raise typer.Exit(code=1)

    if not keyword_list: # If domain was not used or failed and fell back to keywords string
        keyword_list = [kw.strip() for kw in final_keywords_str.split(",") if kw.strip()]

    console.print(f"[bold green]Starting newsletter generation for final keywords: '{final_keywords_str}'[/bold green]")
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
        console.print("\n[cyan]Step 1: Starting LangGraph workflow...[/cyan]")
        
        # LangGraph 워크플로우 실행
        html_content, status = graph.generate_newsletter(keyword_list) # Use the final keyword_list
        
        if status == "error":
            console.print(f"[yellow]Error in newsletter generation: {html_content}[/yellow]")
            return
        
        console.print("[green]Newsletter generated successfully using LangGraph.[/green]")
    
    # 기존 방식 사용하는 경우
    else:
        # 1. Collect articles
        console.print("\n[cyan]Step 1: Collecting articles...[/cyan]")
        articles = news_collect.collect_articles(final_keywords_str) # Use final_keywords_str for collection
        if not articles:
            console.print("[yellow]No articles found. Exiting.[/yellow]")
            return
        console.print(f"Collected {len(articles)} articles.")
        
        # 2. Summarize articles
        console.print("\n[cyan]Step 2: Summarizing articles...[/cyan]")
        summaries = news_summarize.summarize_articles(keyword_list, articles) # Use final keyword_list for summarization context
        if not summaries:
            console.print("[yellow]Failed to summarize articles. Exiting.[/yellow]")
            return        # 이제 summaries는 HTML 문자열이므로 변수명을 변경
        html_content = summaries
        console.print("\n[green]Newsletter generated successfully using legacy pipeline.[/green]")
    
    current_date_str = datetime.now().strftime('%Y-%m-%d')
    filename_base = f"{current_date_str}_newsletter_{final_keywords_str.replace(',', '_').replace(' ', '')}" # Use final_keywords_str

    # 3. Send email
    step_num = 3  # 현재 단계 번호 추적
    
    if to:
        console.print(f"\n[cyan]Step {step_num}: Sending email...[/cyan]")
        email_subject = f"오늘의 뉴스레터: {final_keywords_str}" # Use final_keywords_str
        news_deliver.send_email(to_email=to, subject=email_subject, html_content=html_content)
    else:
        console.print(f"\n[yellow]Step {step_num}: Email sending skipped as no recipient was provided.[/yellow]")
    
    step_num += 1
    
    # 4. Save or Upload
    saved_locally = False
    if output_format:
        console.print(f"\n[cyan]Step {step_num}: Saving newsletter locally as {output_format.upper()}...[/cyan]")
        if news_deliver.save_locally(html_content, filename_base, output_format):
            console.print(f"Newsletter saved locally as {output_format.upper()}.")
            saved_locally = True
        else:
            console.print(f"[red]Failed to save newsletter locally as {output_format.upper()}.[/red]")
        
        step_num += 1

    if drive:
        console.print(f"\n[cyan]Step {step_num}: Saving to Google Drive...[/cyan]")
        if news_deliver.save_to_drive(html_content, filename_base):
            console.print(f"Newsletter (HTML and Markdown) saved to Google Drive.")
        else:
            console.print("[red]Failed to save to Google Drive.[/red]")
    
    if not saved_locally and not drive:
        console.print("[yellow]No output method was successful.[/yellow]")

    console.print("\n[bold green]Newsletter process completed.[/bold green]")

# The 'collect' command can remain if it's used for other purposes or direct testing.
@app.command()
def collect(keywords: str):
    """
    Collect articles based on keywords.
    """
    console.print(f"Collecting articles for keywords: {keywords}")
    # Placeholder
    console.print("Article collection completed (simulated).")

@app.command()
def suggest(
    domain: str = typer.Option(..., "--domain", help="Domain to suggest keywords for."),
    count: int = typer.Option(10, "--count", min=1, help="Number of keywords to generate.")
):
    """
    Suggests trend keywords for a given domain using Google Gemini.
    """
    console.print(f"[bold green]Suggesting {count} keywords for domain: '{domain}'[/bold green]")

    if not config.GEMINI_API_KEY: # GOOGLE_API_KEY 대신 GEMINI_API_KEY 사용
        console.print("[bold red]Error: GEMINI_API_KEY is not set in the environment variables or .env file.[/bold red]")
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
        console.print(f"\n[bold yellow]To generate a newsletter with these keywords, you can use the following command:[/bold yellow]")
        console.print(f"[cyan]{run_command}[/cyan]")
    else:
        console.print("\n[yellow]Could not generate keywords for the given domain. Please check the logs for errors.[/yellow]")

if __name__ == "__main__":
    app()
