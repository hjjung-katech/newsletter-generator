# mypy: ignore-errors

"""
뉴스레터 생성 프로세스를 위한 체계적인 로깅 시스템

이 모듈은 다음과 같은 기능을 제공합니다:
- 레벨별 로깅 (DEBUG, INFO, WARNING, ERROR)
- 진행 상황 표시
- 단계별 시간 측정
- 통계 정보 표시
- 색상 코딩된 출력
"""

import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Rich console 인스턴스
console = Console()


def _to_console_safe(value: Any) -> Any:
    """Return an ASCII-safe fallback for console output."""
    if isinstance(value, str):
        return value.encode("ascii", "backslashreplace").decode("ascii")
    if isinstance(value, Text):
        return value.plain.encode("ascii", "backslashreplace").decode("ascii")
    return value


def _safe_console_print(*args: Any, **kwargs: Any) -> None:
    """Print to Rich console and degrade gracefully on encoding issues."""
    try:
        console.print(*args, **kwargs)
    except UnicodeEncodeError:
        fallback_args = tuple(_to_console_safe(arg) for arg in args)
        console.print(*fallback_args, **kwargs)


class NewsletterLogger:
    """뉴스레터 생성 프로세스를 위한 전용 로거"""

    def __init__(self, name: str = "newsletter", log_level: str = None):
        self.name = name

        # 환경 변수에서 로그 레벨 읽기
        if log_level is None:
            log_level = os.getenv("LOG_LEVEL", "INFO")

        self.log_level = getattr(logging, log_level.upper())
        self.step_times: Dict[str, float] = {}
        self.step_start_times: Dict[str, float] = {}
        self.statistics: Dict[str, Any] = {}

        # 표준 로거 설정
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.log_level)

        # 핸들러가 이미 있는지 확인하여 중복 방지
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def debug(self, message: str, **kwargs):
        """디버그 메시지 출력 (개발자용)"""
        if self.log_level <= logging.DEBUG:
            _safe_console_print(f"[dim cyan][DEBUG][/dim cyan] {message}", **kwargs)
        self.logger.debug(message)

    def info(self, message: str, **kwargs):
        """일반 정보 메시지"""
        if self.log_level <= logging.INFO:
            _safe_console_print(f"[blue][INFO][/blue] {message}", **kwargs)
        self.logger.info(message)

    def warning(self, message: str, **kwargs):
        """경고 메시지"""
        _safe_console_print(f"[yellow][WARNING][/yellow] {message}", **kwargs)
        self.logger.warning(message)

    def error(self, message: str, **kwargs):
        """오류 메시지"""
        _safe_console_print(f"[red][ERROR][/red] {message}", **kwargs)
        self.logger.error(message)

    def success(self, message: str, **kwargs):
        """성공 메시지"""
        _safe_console_print(f"[green][SUCCESS][/green] {message}", **kwargs)
        self.logger.info(f"SUCCESS: {message}")

    def step(self, message: str, step_name: Optional[str] = None, **kwargs):
        """단계별 진행 상황 표시"""
        if step_name:
            self.start_step(step_name)

        _safe_console_print(f"[bold cyan]🔄 {message}[/bold cyan]", **kwargs)
        self.logger.info(f"STEP: {message}")

    def step_complete(self, message: str, step_name: Optional[str] = None, **kwargs):
        """단계 완료 메시지"""
        if step_name:
            self.end_step(step_name)
            elapsed = self.step_times.get(step_name, 0)
            _safe_console_print(
                f"[bold green]✅ {message}[/bold green] [dim]({elapsed:.2f}초)[/dim]",
                **kwargs,
            )
        else:
            _safe_console_print(f"[bold green]✅ {message}[/bold green]", **kwargs)
        self.logger.info(f"STEP_COMPLETE: {message}")

    def step_brief(self, message: str, count: Optional[int] = None, **kwargs):
        """간결한 단계 진행 상황 표시 (핵심 정보만)"""
        if count is not None:
            _safe_console_print(
                f"[cyan]🔄 {message}[/cyan] [bold]({count}개)[/bold]", **kwargs
            )
        else:
            _safe_console_print(f"[cyan]🔄 {message}[/cyan]", **kwargs)
        self.logger.info(f"STEP_BRIEF: {message}")

    def step_result(self, message: str, count: Optional[int] = None, **kwargs):
        """단계 결과 간결 표시"""
        if count is not None:
            _safe_console_print(
                f"[green]→ {message}[/green] [bold white]({count}개)[/bold white]",
                **kwargs,
            )
        else:
            _safe_console_print(f"[green]→ {message}[/green]", **kwargs)
        self.logger.info(f"STEP_RESULT: {message}")

    def show_collection_brief(self, keyword_counts: Dict[str, int]):
        """키워드별 수집 결과 간략 표시"""
        total_articles = sum(keyword_counts.values())

        _safe_console_print("[cyan]📰 뉴스 수집 결과:[/cyan]")
        for keyword, count in keyword_counts.items():
            _safe_console_print(f"  • [white]{keyword}:[/white] [bold]{count}개[/bold]")
        _safe_console_print(f"[bold cyan]  총 {total_articles}개 수집[/bold cyan]")

        self.update_statistics("total_collected_articles", total_articles)
        self.update_statistics("keyword_article_counts", keyword_counts)

    def show_filter_brief(self, before: int, after: int, step_name: str = ""):
        """필터링 결과 간략 표시"""
        filtered_count = before - after
        if filtered_count > 0:
            _safe_console_print(
                f"[yellow]📋 {step_name}:[/yellow] [white]{before}개[/white] → [bold green]{after}개[/bold green] "
                f"[dim](-{filtered_count}개)[/dim]"
            )
        else:
            _safe_console_print(
                f"[yellow]📋 {step_name}:[/yellow] [bold green]{after}개[/bold green]"
            )

        self.logger.info(f"FILTER: {step_name} - {before} → {after}")

    def show_final_brief(self, final_count: int):
        """최종 활용 기사 수 간략 표시"""
        _safe_console_print(f"[bold green]🎯 최종 활용 기사: {final_count}개[/bold green]")
        self.update_statistics("final_articles_count", final_count)

    def start_step(self, step_name: str):
        """단계 시작 시간 기록"""
        self.step_start_times[step_name] = time.time()

    def end_step(self, step_name: str):
        """단계 종료 시간 기록 및 소요 시간 계산"""
        if step_name in self.step_start_times:
            elapsed = time.time() - self.step_start_times[step_name]
            self.step_times[step_name] = elapsed
            del self.step_start_times[step_name]

    def update_statistics(self, key: str, value: Any):
        """통계 정보 업데이트"""
        self.statistics[key] = value

    def show_keyword_info(self, keywords: List[str], domain: str):
        """키워드 정보 표시"""
        table = Table(title=f"🎯 키워드 정보 - 도메인: {domain}", box=box.ROUNDED)
        table.add_column("번호", style="cyan", no_wrap=True)
        table.add_column("키워드", style="magenta")

        for i, keyword in enumerate(keywords, 1):
            table.add_row(str(i), keyword)

        _safe_console_print(table)

    def show_article_collection_summary(self, keyword_counts: Dict[str, int]):
        """기사 수집 결과 요약 표시"""
        table = Table(title="📰 기사 수집 결과", box=box.ROUNDED)
        table.add_column("키워드", style="cyan")
        table.add_column("수집된 기사 수", style="green", justify="right")

        total_articles = 0
        for keyword, count in keyword_counts.items():
            table.add_row(keyword, str(count))
            total_articles += count

        table.add_row("", "", style="dim")
        table.add_row(
            "[bold]총계[/bold]", f"[bold]{total_articles}[/bold]", style="bold green"
        )

        _safe_console_print(table)
        self.update_statistics("total_collected_articles", total_articles)
        self.update_statistics("keyword_article_counts", keyword_counts)

    def show_article_processing_summary(
        self, total_collected: int, after_filtering: int, after_deduplication: int
    ):
        """기사 처리 결과 요약 표시"""
        table = Table(title="🔄 기사 처리 결과", box=box.ROUNDED)
        table.add_column("단계", style="cyan")
        table.add_column("기사 수", style="green", justify="right")
        table.add_column("변화", style="yellow", justify="right")

        table.add_row("수집된 기사", str(total_collected), "-")

        filtered_change = after_filtering - total_collected
        table.add_row(
            "필터링 후",
            str(after_filtering),
            f"{filtered_change:+d}" if filtered_change != 0 else "0",
        )

        dedup_change = after_deduplication - after_filtering
        table.add_row(
            "중복 제거 후",
            str(after_deduplication),
            f"{dedup_change:+d}" if dedup_change != 0 else "0",
        )

        _safe_console_print(table)
        self.update_statistics("articles_after_filtering", after_filtering)
        self.update_statistics("articles_after_deduplication", after_deduplication)

    def show_newsletter_info(
        self,
        domain: str,
        template_style: str,
        output_format: str,
        recipient: Optional[str] = None,
    ):
        """뉴스레터 생성 정보 표시"""
        info_text = Text()
        info_text.append("📧 뉴스레터 생성 정보\n\n", style="bold blue")
        info_text.append(f"도메인: {domain}\n", style="cyan")
        info_text.append(f"템플릿 스타일: {template_style}\n", style="magenta")
        info_text.append(f"출력 형식: {output_format}\n", style="green")
        if recipient:
            info_text.append(f"수신자: {recipient}\n", style="yellow")

        panel = Panel(info_text, box=box.ROUNDED, padding=(1, 2))
        _safe_console_print(panel)

    def show_time_summary(self):
        """단계별 소요 시간 요약 표시"""
        if not self.step_times:
            return

        table = Table(title="⏱️ 단계별 소요 시간", box=box.ROUNDED)
        table.add_column("단계", style="cyan")
        table.add_column("소요 시간", style="green", justify="right")
        table.add_column("비율", style="yellow", justify="right")

        total_time = sum(self.step_times.values())

        for step_name, elapsed_time in self.step_times.items():
            percentage = (elapsed_time / total_time * 100) if total_time > 0 else 0
            table.add_row(
                step_name.replace("_", " ").title(),
                f"{elapsed_time:.2f}초",
                f"{percentage:.1f}%",
            )

        table.add_row("", "", style="dim")
        table.add_row(
            "[bold]총 소요 시간[/bold]",
            f"[bold]{total_time:.2f}초[/bold]",
            "[bold]100.0%[/bold]",
        )

        _safe_console_print(table)

    def show_final_summary(self):
        """최종 요약 정보 표시"""
        if not self.statistics:
            return

        summary_text = Text()
        summary_text.append("📊 생성 완료 요약\n\n", style="bold green")

        # 기사 관련 통계
        if "total_collected_articles" in self.statistics:
            summary_text.append(
                f"수집된 기사: {self.statistics['total_collected_articles']}개\n",
                style="cyan",
            )

        if "articles_after_deduplication" in self.statistics:
            summary_text.append(
                f"최종 사용된 기사: {self.statistics['articles_after_deduplication']}개\n",
                style="green",
            )

        # 시간 관련 통계
        total_time = sum(self.step_times.values())
        if total_time > 0:
            summary_text.append(f"총 소요 시간: {total_time:.2f}초\n", style="yellow")

        # 생성 시간
        summary_text.append(
            f"생성 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            style="dim",
        )

        panel = Panel(
            summary_text, title="🎉 뉴스레터 생성 완료", box=box.DOUBLE, padding=(1, 2)
        )
        _safe_console_print(panel)

    @contextmanager
    def step_context(self, step_name: str, message: str):
        """단계 실행을 위한 컨텍스트 매니저"""
        self.step(message, step_name)
        try:
            yield
        finally:
            self.step_complete(f"{message} 완료", step_name)


# 전역 로거 인스턴스
_global_logger: Optional[NewsletterLogger] = None


def get_logger(name: str = "newsletter", log_level: str = None) -> NewsletterLogger:
    """전역 로거 인스턴스 반환"""
    global _global_logger
    if _global_logger is None:
        _global_logger = NewsletterLogger(name, log_level)
    return _global_logger


def set_log_level(level: str):
    """로그 레벨 설정"""
    if _global_logger:
        _global_logger.log_level = getattr(logging, level.upper())
        _global_logger.logger.setLevel(_global_logger.log_level)


# 편의 함수들
def debug(message: str, **kwargs):
    """디버그 메시지"""
    get_logger().debug(message, **kwargs)


def info(message: str, **kwargs):
    """정보 메시지"""
    get_logger().info(message, **kwargs)


def warning(message: str, **kwargs):
    """경고 메시지"""
    get_logger().warning(message, **kwargs)


def error(message: str, **kwargs):
    """오류 메시지"""
    get_logger().error(message, **kwargs)


def success(message: str, **kwargs):
    """성공 메시지"""
    get_logger().success(message, **kwargs)


def step(message: str, step_name: Optional[str] = None, **kwargs):
    """단계 진행 메시지"""
    get_logger().step(message, step_name, **kwargs)


def step_complete(message: str, step_name: Optional[str] = None, **kwargs):
    """단계 완료 메시지"""
    get_logger().step_complete(message, step_name, **kwargs)


def step_brief(message: str, count: Optional[int] = None, **kwargs):
    """간결한 단계 진행 메시지"""
    get_logger().step_brief(message, count, **kwargs)


def step_result(message: str, count: Optional[int] = None, **kwargs):
    """단계 결과 간결 표시"""
    get_logger().step_result(message, count, **kwargs)


def show_collection_brief(keyword_counts: Dict[str, int]):
    """키워드별 수집 결과 간략 표시"""
    get_logger().show_collection_brief(keyword_counts)


def show_filter_brief(before: int, after: int, step_name: str = ""):
    """필터링 결과 간략 표시"""
    get_logger().show_filter_brief(before, after, step_name)


def show_final_brief(final_count: int):
    """최종 활용 기사 수 간략 표시"""
    get_logger().show_final_brief(final_count)
