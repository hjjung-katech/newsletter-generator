import typer
from rich.console import Console
import os
from datetime import datetime
from typing import Optional

from . import collect as news_collect
from . import summarize as news_summarize
from . import compose as news_compose
from . import deliver as news_deliver
from . import config

app = typer.Typer()
console = Console()

@app.command()
def run(
    keywords: str = typer.Option("AI,LLM", help="Keywords to search for, comma-separated."),
    to: Optional[str] = typer.Option(None, "--to", help="Email address to send the newsletter to. If not provided, email sending will be skipped."),
    output_format: Optional[str] = typer.Option(None, "--output-format", help="Format to save the newsletter locally (html or md). If not provided, saves to Drive if --drive is used, otherwise defaults to html."),
    drive: bool = typer.Option(False, "--drive", help="Save the newsletter to Google Drive (HTML and Markdown).")
):
    """
    Run the newsletter generation and saving process.
    """
    if not output_format and not drive:
        console.print("[yellow]No output option selected. Defaulting to local HTML save.[/yellow]")
        output_format = "html" # Default to local html if no other option

    console.print(f"[bold green]Starting newsletter generation for keywords: '{keywords}'[/bold green]")
    if output_format:
        console.print(f"[bold green]Local output format: {output_format}[/bold green]")
    if drive:
        console.print(f"[bold green]Save to Google Drive: Enabled[/bold green]")

    # 1. Collect articles
    console.print("\n[cyan]Step 1: Collecting articles...[/cyan]")
    # 실제 API를 사용하려면 config.NEWS_API_KEY 등을 설정해야 합니다.
    # 여기서는 예시로 collect_articles를 직접 호출합니다.
    articles = news_collect.collect_articles(keywords)
    if not articles:
        console.print("[yellow]No articles found. Exiting.[/yellow]")
        return
    console.print(f"Collected {len(articles)} articles.")

    # 2. Summarize articles
    console.print("\n[cyan]Step 2: Summarizing articles...[/cyan]")
    # 실제 API를 사용하려면 config.GEMINI_API_KEY 등을 설정해야 합니다.
    summaries = news_summarize.summarize_articles(articles)
    if not summaries:
        console.print("[yellow]Failed to summarize articles. Exiting.[/yellow]")
        return
    console.print(f"Summarized {len(summaries)} articles.")

    # 3. Compose newsletter
    console.print("\n[cyan]Step 3: Composing newsletter...[/cyan]")
    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    template_name = "newsletter_template.html"
    # Set generation date for the template
    os.environ["GENERATION_DATE"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_content = news_compose.compose_newsletter_html(summaries, template_dir, template_name)
    console.print("Newsletter composed successfully.")

    current_date_str = datetime.now().strftime('%Y-%m-%d')
    filename_base = f"{current_date_str}_newsletter_{keywords.replace(',', '_').replace(' ', '')}"

    # 4. Send email
    if to:
        console.print("\n[cyan]Step 4: Sending email...[/cyan]")
        email_subject = f"오늘의 뉴스레터: {keywords}"
        news_deliver.send_email(to_email=to, subject=email_subject, html_content=html_content)
    else:
        console.print("\n[yellow]Step 4: Email sending skipped as no recipient was provided.[/yellow]")
    
    # 5. Save or Upload
    saved_locally = False
    if output_format:
        console.print(f"\n[cyan]Step 5: Saving newsletter locally as {output_format.upper()}...[/cyan]")
        if news_deliver.save_locally(html_content, filename_base, output_format):
            console.print(f"Newsletter saved locally as {output_format.upper()}.")
            saved_locally = True
        else:
            console.print(f"[red]Failed to save newsletter locally as {output_format.upper()}.[/red]")

    if drive:
        step_number = 6 if saved_locally else 5
        console.print(f"\n[cyan]Step {step_number}: Saving to Google Drive...[/cyan]")
        if news_deliver.save_to_drive(html_content, filename_base):
            console.print(f"Newsletter (HTML and Markdown) saved to Google Drive.")
        else:
            console.print("[red]Failed to save to Google Drive.[/red]")
    
    if not saved_locally and not drive:
        console.print("[yellow]No output method was successful.[/yellow]")

    console.print("\n[bold green]Newsletter process completed.[/bold green]")

@app.command()
def collect(keywords: str):
    """
    Collect articles based on keywords.
    """
    console.print(f"Collecting articles for keywords: {keywords}")
    # Placeholder
    console.print("Article collection completed (simulated).")

@app.command()
def suggest(domain: str = ""):
    """
    Suggest keywords based on a domain or general trends.
    """
    console.print(f"Suggesting keywords for domain: {domain}")
    # Placeholder
    console.print("Keyword suggestion completed (simulated).")

if __name__ == "__main__":
    app()
