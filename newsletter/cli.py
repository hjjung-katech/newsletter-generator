import typer
from rich.console import Console
import os # Added
from datetime import datetime # Added

from . import collect as news_collect
from . import summarize as news_summarize
from . import compose as news_compose
from . import deliver as news_deliver
from . import config # Added

app = typer.Typer()
console = Console()

@app.command()
def run(
    keywords: str = typer.Option("AI,LLM", help="Keywords to search for, comma-separated."),
    to: str = typer.Option("test@example.com", help="Email address to send the newsletter to."),
    drive: bool = typer.Option(False, "--drive", help="Save the newsletter to Google Drive.")
):
    """
    Run the newsletter generation and sending process.
    """
    console.print(f"[bold green]Starting newsletter generation for keywords: '{keywords}', to: '{to}', Drive: {drive}[/bold green]")

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

    # 4. Send email
    console.print("\n[cyan]Step 4: Sending email...[/cyan]")
    email_subject = f"오늘의 뉴스레터: {keywords}"
    # 실제 API를 사용하려면 config.SENDGRID_API_KEY 등을 설정해야 합니다.
    news_deliver.send_email(to_email=to, subject=email_subject, html_content=html_content)
    
    # 5. Optionally save to Google Drive
    if drive:
        console.print("\n[cyan]Step 5: Saving to Google Drive...[/cyan]")
        drive_filename = f"{datetime.now().strftime('%Y-%m-%d')}_newsletter.html"
        # 실제 Google Drive API 연동 필요
        if news_deliver.save_to_drive(html_content, drive_filename):
            console.print(f"Newsletter saved to Google Drive as {drive_filename} (simulated).")
        else:
            console.print("[red]Failed to save to Google Drive.[/red]")

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
