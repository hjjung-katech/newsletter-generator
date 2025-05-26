#!/usr/bin/env python3
"""
이메일 발송 기능 통합 테스트

이 스크립트는 Newsletter Generator의 이메일 발송 기능을
실제 환경에서 테스트하기 위한 통합 테스트입니다.

⚠️  주의: 이 테스트는 실제 Postmark API를 호출합니다.
GitHub Actions에서는 API 키가 없어 자동으로 스킵됩니다.

테스트 분류:
- @pytest.mark.integration: 실제 API 호출 테스트
- @pytest.mark.requires_quota: API 할당량 소모 테스트

사용법:
    python tests/api_tests/test_email_integration.py --to your-email@example.com
    python tests/api_tests/test_email_integration.py --to your-email@example.com --send-real
"""

import argparse
import os
import sys
import glob
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from newsletter import config
from newsletter import deliver as news_deliver
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def check_email_configuration():
    """이메일 설정 확인"""
    console.print("\n[bold blue]📧 이메일 설정 확인[/bold blue]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("설정 항목", style="cyan")
    table.add_column("상태", style="green")
    table.add_column("값", style="yellow")

    # Postmark 토큰 확인
    postmark_status = (
        "✅ 설정됨" if config.POSTMARK_SERVER_TOKEN else "❌ 설정되지 않음"
    )
    postmark_value = (
        config.POSTMARK_SERVER_TOKEN[:10] + "..."
        if config.POSTMARK_SERVER_TOKEN
        else "없음"
    )
    table.add_row("POSTMARK_SERVER_TOKEN", postmark_status, postmark_value)

    # 발송자 이메일 확인
    sender_status = "✅ 설정됨" if config.EMAIL_SENDER else "❌ 설정되지 않음"
    sender_value = config.EMAIL_SENDER if config.EMAIL_SENDER else "없음"
    table.add_row("EMAIL_SENDER", sender_status, sender_value)

    console.print(table)

    # 설정 검증
    if not config.POSTMARK_SERVER_TOKEN or not config.EMAIL_SENDER:
        console.print("\n[red]⚠️  이메일 설정이 완전하지 않습니다.[/red]")
        console.print("[yellow].env 파일에 다음 설정을 추가해주세요:[/yellow]")
        console.print("[cyan]POSTMARK_SERVER_TOKEN=your_postmark_server_token[/cyan]")
        console.print("[cyan]EMAIL_SENDER=your_verified_sender@example.com[/cyan]")
        return False

    console.print("\n[green]✅ 이메일 설정이 완료되었습니다.[/green]")
    return True


def find_html_files():
    """테스트용 HTML 파일 찾기"""
    console.print("\n[bold blue]📁 테스트용 HTML 파일 검색[/bold blue]")

    html_files = glob.glob("output/*.html")
    if not html_files:
        console.print("[yellow]⚠️  output 디렉토리에 HTML 파일이 없습니다.[/yellow]")
        return []

    # 최근 파일 5개 선택
    recent_files = sorted(html_files, key=os.path.getctime, reverse=True)[:5]

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("번호", style="cyan", width=4)
    table.add_column("파일명", style="green")
    table.add_column("크기", style="yellow", width=10)
    table.add_column("수정일", style="blue")

    for i, file_path in enumerate(recent_files, 1):
        file_size = os.path.getsize(file_path)
        file_size_str = f"{file_size:,} bytes"
        mod_time = datetime.fromtimestamp(os.path.getctime(file_path)).strftime(
            "%Y-%m-%d %H:%M"
        )
        filename = os.path.basename(file_path)

        table.add_row(str(i), filename, file_size_str, mod_time)

    console.print(table)
    console.print(
        f"\n[info]총 {len(html_files)}개의 HTML 파일 중 최근 {len(recent_files)}개를 표시했습니다.[/info]"
    )

    return recent_files


def send_default_email(to_email, send_real=False):
    """기본 테스트 이메일 발송"""
    console.print(
        f"\n[bold blue]📤 기본 테스트 이메일 발송 {'(실제 발송)' if send_real else '(DRY RUN)'}[/bold blue]"
    )

    subject = (
        f"Newsletter Generator 테스트 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    # 기본 테스트 HTML 생성
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>이메일 테스트</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; border-radius: 5px; }}
            .content {{ padding: 20px; background-color: #f8f9fa; margin: 20px 0; border-radius: 5px; }}
            .footer {{ text-align: center; color: #666; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📧 Newsletter Generator 이메일 테스트</h1>
        </div>
        <div class="content">
            <h2>✅ 테스트 성공!</h2>
            <p>이 이메일을 받으셨다면 Newsletter Generator의 Postmark 이메일 발송 기능이 정상적으로 작동하고 있습니다.</p>
            <ul>
                <li><strong>발송 시간:</strong> {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}</li>
                <li><strong>수신자:</strong> {to_email}</li>
                <li><strong>발송자:</strong> {config.EMAIL_SENDER}</li>
                <li><strong>테스트 모드:</strong> {'실제 발송' if send_real else 'DRY RUN'}</li>
            </ul>
        </div>
        <div class="footer">
            <p>이 메시지는 Newsletter Generator 통합 테스트에 의해 생성되었습니다.</p>
        </div>
    </body>
    </html>
    """

    if not send_real:
        console.print(
            "[yellow]🔍 DRY RUN 모드 - 실제 이메일은 발송되지 않습니다[/yellow]"
        )
        console.print(f"[cyan]수신자:[/cyan] {to_email}")
        console.print(f"[cyan]제목:[/cyan] {subject}")
        console.print(f"[cyan]내용 길이:[/cyan] {len(html_content)} 문자")
        return True

    try:
        success = news_deliver.send_email(
            to_email=to_email, subject=subject, html_content=html_content
        )

        if success:
            console.print(
                "[green]✅ 기본 테스트 이메일이 성공적으로 발송되었습니다![/green]"
            )
            return True
        else:
            console.print("[red]❌ 기본 테스트 이메일 발송에 실패했습니다.[/red]")
            console.print("[yellow]💡 문제 해결 팁:[/yellow]")
            console.print(
                "   - 422 오류: 수신자가 비활성화됨 → 다른 이메일 주소로 테스트"
            )
            console.print(
                "   - 401 오류: 잘못된 토큰 → Postmark 대시보드에서 토큰 확인"
            )
            console.print(
                "   - 403 오류: 계정 승인 대기 → 같은 도메인 내 이메일로 테스트"
            )
            return False

    except Exception as e:
        console.print(f"[red]❌ 이메일 발송 중 오류 발생: {e}[/red]")
        console.print(
            "[yellow]💡 네트워크 연결이나 Postmark 설정을 확인해주세요.[/yellow]"
        )
        return False


def send_newsletter_email(to_email, html_file, send_real=False):
    """뉴스레터 파일을 사용한 이메일 테스트"""
    console.print(
        f"\n[bold blue]📰 뉴스레터 이메일 테스트 {'(실제 발송)' if send_real else '(DRY RUN)'}[/bold blue]"
    )

    try:
        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()

        filename = os.path.basename(html_file)
        subject = (
            f"뉴스레터 테스트: {filename} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        console.print(f"[cyan]파일:[/cyan] {filename}")
        console.print(f"[cyan]크기:[/cyan] {len(html_content):,} 문자")

        if not send_real:
            console.print(
                "[yellow]🔍 DRY RUN 모드 - 실제 이메일은 발송되지 않습니다[/yellow]"
            )
            console.print(f"[cyan]수신자:[/cyan] {to_email}")
            console.print(f"[cyan]제목:[/cyan] {subject}")
            return True

        success = news_deliver.send_email(
            to_email=to_email, subject=subject, html_content=html_content
        )

        if success:
            console.print(
                "[green]✅ 뉴스레터 이메일이 성공적으로 발송되었습니다![/green]"
            )
            return True
        else:
            console.print("[red]❌ 뉴스레터 이메일 발송에 실패했습니다.[/red]")
            console.print("[yellow]💡 문제 해결 팁:[/yellow]")
            console.print(
                "   - 422 오류: 수신자가 비활성화됨 → 다른 이메일 주소로 테스트"
            )
            console.print(
                "   - 401 오류: 잘못된 토큰 → Postmark 대시보드에서 토큰 확인"
            )
            console.print(
                "   - 403 오류: 계정 승인 대기 → 같은 도메인 내 이메일로 테스트"
            )
            return False

    except Exception as e:
        console.print(f"[red]❌ 뉴스레터 이메일 발송 중 오류 발생: {e}[/red]")
        console.print(
            "[yellow]💡 네트워크 연결이나 Postmark 설정을 확인해주세요.[/yellow]"
        )
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Newsletter Generator 이메일 발송 통합 테스트"
    )
    parser.add_argument("--to", required=True, help="테스트 이메일을 받을 이메일 주소")
    parser.add_argument(
        "--send-real", action="store_true", help="실제 이메일 발송 (기본값: dry-run)"
    )
    parser.add_argument("--newsletter-file", help="특정 뉴스레터 파일 지정 (선택사항)")

    args = parser.parse_args()

    console.print(
        Panel.fit(
            "[bold green]Newsletter Generator 이메일 발송 통합 테스트[/bold green]\n"
            f"수신자: {args.to}\n"
            f"모드: {'실제 발송' if args.send_real else 'DRY RUN'}",
            title="🧪 통합 테스트",
        )
    )

    # 1. 설정 확인
    if not check_email_configuration():
        return 1

    # 2. 기본 이메일 테스트
    if not send_default_email(args.to, args.send_real):
        return 1

    # 3. 뉴스레터 파일 테스트
    if args.newsletter_file:
        if os.path.exists(args.newsletter_file):
            send_newsletter_email(args.to, args.newsletter_file, args.send_real)
        else:
            console.print(
                f"[red]❌ 지정된 파일을 찾을 수 없습니다: {args.newsletter_file}[/red]"
            )
    else:
        html_files = find_html_files()
        if html_files:
            # 가장 최근 파일로 테스트
            latest_file = html_files[0]
            send_newsletter_email(args.to, latest_file, args.send_real)

    # 4. 결과 요약
    console.print(
        Panel.fit(
            (
                "[bold green]✅ 통합 테스트 완료[/bold green]\n"
                f"{'실제 이메일이 발송되었습니다.' if args.send_real else 'DRY RUN 모드로 실행되었습니다.'}\n"
                f"수신자 {args.to}의 받은편지함을 확인해주세요."
                if args.send_real
                else "실제 발송하려면 --send-real 옵션을 추가하세요."
            ),
            title="🎉 테스트 결과",
        )
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
