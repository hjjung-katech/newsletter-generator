"""Diagnostic and utility CLI commands extracted from newsletter.cli."""

import os
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console

from . import config
from . import deliver as news_deliver

console = Console()


def check_config() -> None:
    """현재 설정 상태를 확인합니다 (이메일, LLM, 기타 설정)."""
    console.print("\n[bold blue]🔧 Newsletter Generator 설정 상태 확인[/bold blue]")
    console.print("=" * 60)

    # 1. 이메일 설정 확인
    console.print("\n[bold yellow]📧 이메일 발송 설정[/bold yellow]")

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
    console.print("\n[bold yellow]🤖 LLM 설정[/bold yellow]")

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
    console.print("\n[bold yellow]☁️  Google Drive 설정[/bold yellow]")

    credentials_path = "credentials.json"
    if os.path.exists(credentials_path):
        console.print("[green]✅ credentials.json:[/green] 파일 존재")
        console.print("   - Google Drive 저장 기능 사용 가능")
    else:
        console.print("[yellow]⚪ credentials.json:[/yellow] 파일 없음")
        console.print("   - Google Drive 저장 기능 비활성화 (선택사항)")

    # 4. 출력 디렉토리 확인
    console.print("\n[bold yellow]📁 출력 디렉토리[/bold yellow]")

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
    console.print("\n[bold yellow]⚙️  설정 파일[/bold yellow]")

    config_candidates = ["config/config.yml", "config.yml"]
    resolved_config_file = next(
        (candidate for candidate in config_candidates if os.path.exists(candidate)),
        None,
    )
    if resolved_config_file:
        console.print(f"[green]✅ config:[/green] 파일 존재 ({resolved_config_file})")
        console.print("   - 사용자 정의 설정 적용 가능")
    else:
        console.print(
            "[yellow]⚪ config:[/yellow] 파일 없음 (config/config.yml, config.yml)"
        )
        console.print("   - 기본 설정 사용 중 (선택사항)")

    env_file = ".env"
    if os.path.exists(env_file):
        console.print("[green]✅ .env:[/green] 파일 존재")
    else:
        console.print("[red]❌ .env:[/red] 파일 없음")
        console.print("   - .env.example을 복사하여 .env 파일 생성 필요")

    # 6. 종합 상태 요약
    console.print("\n[bold blue]📊 종합 상태 요약[/bold blue]")
    console.print("=" * 60)

    required_settings = [
        ("LLM API Key", config.GEMINI_API_KEY or openai_key or anthropic_key),
    ]

    optional_settings = [
        ("이메일 발송", email_ready),
        ("Google Drive", os.path.exists(credentials_path)),
        ("설정 파일", resolved_config_file is not None),
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


def check_llm() -> None:
    """현재 사용 가능한 LLM 제공자와 설정을 확인합니다."""
    console.print("\n[bold blue]🤖 LLM 제공자 상태 확인[/bold blue]")

    try:
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
                console.print(f"  • [red]{provider_name}[/red] - 사용 불가 (API 키 없음)")

        # 현재 LLM 설정 표시
        console.print("\n[bold blue]📋 현재 LLM 설정[/bold blue]")
        llm_config = config.LLM_CONFIG
        default_provider = llm_config.get("default_provider", "gemini")
        console.print(f"기본 제공자: [blue]{default_provider}[/blue]")

        # 작업별 설정 표시
        console.print("\n[bold blue]🔧 작업별 LLM 할당[/bold blue]")
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
            console.print("\n[bold red]⚠️  경고: 사용 가능한 LLM 제공자가 없습니다![/bold red]")
            console.print("다음 중 하나 이상의 API 키를 .env 파일에 설정해주세요:")
            console.print("  • GEMINI_API_KEY")
            console.print("  • OPENAI_API_KEY")
            console.print("  • ANTHROPIC_API_KEY")
        elif len(available_providers) == 1:
            console.print(
                "\n[yellow]💡 권장사항: 더 나은 fallback을 위해 추가 LLM 제공자를 설정하는 것을 권장합니다.[/yellow]"
            )
        else:
            console.print(
                "\n[green]🎉 좋습니다! 여러 LLM 제공자가 설정되어 있어 안정적인 서비스가 가능합니다.[/green]"
            )

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")


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
) -> None:
    """특정 작업에 대한 LLM 응답을 테스트합니다."""
    console.print(f"\n[bold blue]🧪 LLM 테스트: {task}[/bold blue]")

    try:
        import time

        from .llm_factory import get_llm_for_task

        # LLM 생성
        console.print("[cyan]LLM 생성 중...[/cyan]")
        llm = get_llm_for_task(task, enable_fallback=False)
        console.print(f"[green]✅ LLM 생성 완료: {type(llm).__name__}[/green]")

        # 테스트 실행
        console.print("[cyan]테스트 실행 중...[/cyan]")
        console.print(f"프롬프트: {prompt}")

        start_time = time.time()
        response = llm.invoke(prompt)
        end_time = time.time()

        # 결과 출력
        response_time = end_time - start_time
        response_text = str(response).strip()

        console.print("\n[bold green]📝 응답 결과[/bold green]")
        console.print(f"응답 시간: {response_time:.2f}초")
        console.print(f"응답 길이: {len(response_text)}자")
        console.print("\n[blue]응답 내용:[/blue]")
        console.print(response_text)

    except Exception as e:
        console.print(f"[bold red]❌ 테스트 실패: {e}[/bold red]")

        # 429 에러인 경우 특별한 안내
        if "429" in str(e) or "quota" in str(e).lower():
            console.print("[yellow]💡 API 할당량이 초과된 것 같습니다. 다른 LLM 제공자를 사용해보세요.[/yellow]")
            console.print(
                "[yellow]   'newsletter check-llm' 명령어로 사용 가능한 제공자를 확인하세요.[/yellow]"
            )


def list_providers() -> None:
    """사용 가능한 LLM 제공자와 모델 정보를 표시합니다."""
    try:
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
                console.print(f"  [yellow]API 키가 설정되지 않음: {api_key_name}[/yellow]")

        # 기능별 모델 설정 표시
        console.print("\n[bold cyan]기능별 모델 설정[/bold cyan]")
        console.print("=" * 50)

        models_config = config.LLM_CONFIG.get("models", {})
        for task, task_config in models_config.items():
            provider = task_config.get("provider", "N/A")
            model = task_config.get("model", "N/A")
            temp = task_config.get("temperature", "N/A")
            console.print(f"{task}: [blue]{provider}[/blue] - {model} (temp: {temp})")

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")


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
) -> None:
    """
    Test email sending functionality using Postmark.

    This command allows you to test the email delivery system without generating a full newsletter.
    You can send a simple test message or use an existing HTML file as the email content.
    """
    console.print("\n[bold blue]📧 이메일 발송 테스트[/bold blue]")

    # EMAIL_SENDER 설정 상태 확인 및 표시
    console.print("\n[bold yellow]📋 이메일 설정 확인[/bold yellow]")

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
        console.print("[yellow]이메일 발송을 위해 Postmark 토큰 설정이 필요합니다.[/yellow]")
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
<html lang=\"ko\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
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
    <div class=\"container\">
        <div class=\"header\">
            <h1>📧 Newsletter Generator 이메일 테스트</h1>
        </div>

        <div class=\"content\">
            <div class=\"success\">
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
            <pre style=\"background-color: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto;\">
newsletter run --keywords \"AI,머신러닝\" --to {to} --output-format html
            </pre>
        </div>

        <div class=\"footer\">
            <p>이 메시지는 Newsletter Generator의 이메일 테스트 기능에 의해 자동으로 생성되었습니다.</p>
            <p>문의사항이 있으시면 개발팀에 연락해 주세요.</p>
        </div>
    </div>
</body>
</html>
        """

    if dry_run:
        console.print("\n[yellow]🔍 DRY RUN MODE - 실제 이메일은 발송되지 않습니다[/yellow]")
        console.print(f"[cyan]수신자:[/cyan] {to}")
        console.print(f"[cyan]제목:[/cyan] {subject}")
        console.print(f"[cyan]내용 길이:[/cyan] {len(html_content)} 문자")
        console.print(
            f"[cyan]Postmark 토큰 설정 여부:[/cyan] {'✅ 설정됨' if config.POSTMARK_SERVER_TOKEN else '❌ 설정되지 않음'}"
        )
        console.print(f"[cyan]발송자 이메일:[/cyan] {config.EMAIL_SENDER}")

        if not config.POSTMARK_SERVER_TOKEN:
            console.print("\n[red]⚠️  POSTMARK_SERVER_TOKEN이 설정되지 않았습니다.[/red]")
            console.print("[yellow].env 파일에 POSTMARK_SERVER_TOKEN을 설정해주세요.[/yellow]")

        console.print("\n[green]Dry run 완료. 실제 발송하려면 --dry-run 옵션을 제거하세요.[/green]")
        return

    # Check Postmark configuration
    if not config.POSTMARK_SERVER_TOKEN:
        console.print("\n[red]❌ POSTMARK_SERVER_TOKEN이 설정되지 않았습니다.[/red]")
        console.print("[yellow]이메일 발송을 위해 .env 파일에 다음을 설정해주세요:[/yellow]")
        console.print("[cyan]POSTMARK_SERVER_TOKEN=your_postmark_server_token[/cyan]")
        console.print("[cyan]EMAIL_SENDER=your_verified_sender@example.com[/cyan]")
        raise typer.Exit(code=1)

    if not config.EMAIL_SENDER:
        console.print("\n[red]❌ EMAIL_SENDER가 설정되지 않았습니다.[/red]")
        console.print("[yellow].env 파일에 EMAIL_SENDER를 설정해주세요:[/yellow]")
        console.print("[cyan]EMAIL_SENDER=your_verified_sender@example.com[/cyan]")
        raise typer.Exit(code=1)

    # Send the test email
    console.print("\n[cyan]📤 이메일 발송 중...[/cyan]")
    console.print(f"[info]발송자: {config.EMAIL_SENDER}[/info]")
    console.print(f"[info]수신자: {to}[/info]")
    console.print(f"[info]제목: {subject}[/info]")

    try:
        success = news_deliver.send_email(
            to_email=to, subject=subject, html_content=html_content
        )

        if success:
            console.print("\n[bold green]✅ 이메일이 성공적으로 발송되었습니다![/bold green]")
            console.print(f"[green]수신자 {to}의 받은편지함을 확인해주세요.[/green]")

            # Save test email content for reference
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = "./output"
            os.makedirs(output_dir, exist_ok=True)
            test_file_path = os.path.join(output_dir, f"test_email_{timestamp}.html")

            try:
                with open(test_file_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                console.print(f"[info]테스트 이메일 내용이 저장되었습니다: {test_file_path}[/info]")
            except Exception as e:
                console.print(f"[yellow]테스트 파일 저장 실패: {e}[/yellow]")

        else:
            console.print("\n[bold red]❌ 이메일 발송에 실패했습니다.[/bold red]")
            console.print("[yellow]Postmark 설정과 네트워크 연결을 확인해주세요.[/yellow]")
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"\n[bold red]❌ 이메일 발송 중 오류가 발생했습니다: {e}[/bold red]")
        console.print("[yellow]설정을 확인하고 다시 시도해주세요.[/yellow]")
        raise typer.Exit(code=1)
