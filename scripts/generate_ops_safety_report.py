#!/usr/bin/env python3
"""Generate an operational safety report for release readiness."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _check(label: str, condition: bool, detail: str) -> dict[str, str]:
    return {
        "label": label,
        "status": "PASS" if condition else "FAIL",
        "detail": detail,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ops safety report")
    parser.add_argument(
        "--output",
        default=".release/ops-safety-report.md",
        help="Output markdown report path",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    output_path = (root / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    routes_generation = _read_text(root / "web" / "routes_generation.py")
    tasks_py = _read_text(root / "web" / "tasks.py")
    schedule_runner = _read_text(root / "web" / "schedule_runner.py")
    routes_send_email = _read_text(root / "web" / "routes_send_email.py")
    config_manager = _read_text(root / "newsletter" / "config_manager.py")
    centralized_settings = _read_text(root / "newsletter" / "centralized_settings.py")
    app_py = _read_text(root / "web" / "app.py")

    checks = [
        _check(
            "Idempotency header handling",
            "Idempotency-Key" in routes_generation
            and "deduplicated" in routes_generation,
            "web/routes_generation.py contains Idempotency-Key parsing and deduplicated response.",
        ),
        _check(
            "Shared DB state transitions",
            "update_history_status(" in tasks_py
            and "create_or_get_history_job(" in routes_generation,
            "Task updates and route job creation use shared DB helpers.",
        ),
        _check(
            "Outbox duplicate prevention",
            "email_outbox" in app_py
            and "get_or_create_outbox_record(" in routes_send_email
            and "get_or_create_outbox_record(" in tasks_py,
            "Schema and runtime paths reference outbox dedupe flow.",
        ),
        _check(
            "Scheduler deterministic key",
            "build_schedule_idempotency_key(" in schedule_runner
            and "schedule_" in schedule_runner,
            "Schedule runner derives deterministic run identity from schedule + intended run time.",
        ),
        _check(
            "Config import side-effect removal",
            "load_dotenv()" not in config_manager
            and "_load_dotenv_if_needed()" in config_manager
            and "_load_dotenv_if_needed()" in centralized_settings,
            "dotenv loading moved behind callable paths, not bare module import calls.",
        ),
    ]

    generated_at = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Ops Safety Report",
        "",
        f"- Generated at (UTC): `{generated_at}`",
        "",
        "## Summary",
        "",
        f"- Total checks: `{len(checks)}`",
        f"- Passed: `{sum(1 for c in checks if c['status'] == 'PASS')}`",
        f"- Failed: `{sum(1 for c in checks if c['status'] == 'FAIL')}`",
        "",
        "## Checks",
        "",
    ]

    for check in checks:
        lines.extend(
            [
                f"- `{check['status']}` {check['label']}",
                f"  - {check['detail']}",
            ]
        )

    lines.extend(
        [
            "",
            "## Required Manual Addendum",
            "",
            "- Idempotency key 적용 범위 요약",
            "- Outbox 중복 방지 시나리오 결과",
            "- Import side-effect 검증 로그",
            "- 미실행 테스트 및 사유",
        ]
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Ops safety report written: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
