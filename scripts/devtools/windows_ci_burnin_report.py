#!/usr/bin/env python3
"""Measure Windows build-check burn-in success rate from recent CI runs."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class RunResult:
    run_id: int
    url: str
    created_at: str
    windows_job: str
    windows_conclusion: str
    passed: bool


def _gh_json(args: list[str]) -> Any:
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit((result.stdout + result.stderr).strip())
    return json.loads(result.stdout)


def _resolve_windows_job(jobs: list[dict[str, Any]]) -> tuple[str, str]:
    candidates = []
    for job in jobs:
        name = str(job.get("name", ""))
        lowered = name.lower()
        if "build check" in lowered and "windows" in lowered:
            candidates.append(job)

    if not candidates:
        return "missing", "missing"

    selected = candidates[0]
    conclusion = str(selected.get("conclusion", "unknown") or "unknown")
    return str(selected.get("name", "unknown")), conclusion


def _success_rate(results: list[RunResult]) -> float:
    if not results:
        return 0.0
    passed = sum(1 for item in results if item.passed)
    return (passed / len(results)) * 100.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", default="Main CI Pipeline")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--scan-limit", type=int, default=60)
    parser.add_argument("--min-success-rate", type=float, default=95.0)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    runs = _gh_json(
        [
            "run",
            "list",
            "--workflow",
            args.workflow,
            "--branch",
            args.branch,
            "--limit",
            str(args.scan_limit),
            "--json",
            "databaseId,createdAt,url,status,conclusion",
        ]
    )

    candidate_results: list[RunResult] = []
    for run in runs:
        run_id = int(run["databaseId"])
        detail = _gh_json(
            [
                "run",
                "view",
                str(run_id),
                "--json",
                "jobs,url,createdAt",
            ]
        )
        jobs = detail.get("jobs", [])
        windows_job, windows_conclusion = _resolve_windows_job(jobs)
        if windows_job == "missing":
            continue
        passed = windows_conclusion == "success"
        candidate_results.append(
            RunResult(
                run_id=run_id,
                url=str(detail.get("url", run.get("url", ""))),
                created_at=str(detail.get("createdAt", run.get("createdAt", ""))),
                windows_job=windows_job,
                windows_conclusion=windows_conclusion,
                passed=passed,
            )
        )
        if len(candidate_results) >= args.limit:
            break

    if len(candidate_results) < args.limit:
        raise SystemExit(
            "insufficient windows build-check history: "
            f"requested={args.limit}, found={len(candidate_results)} "
            f"(scan_limit={args.scan_limit})"
        )

    results = candidate_results

    success_rate = _success_rate(results)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "workflow": args.workflow,
        "branch": args.branch,
        "scan_limit": args.scan_limit,
        "sample_size": len(results),
        "minimum_success_rate": args.min_success_rate,
        "success_rate": success_rate,
        "passed": success_rate >= args.min_success_rate,
        "runs": [item.__dict__ for item in results],
    }

    print(json.dumps(summary, indent=2, ensure_ascii=True))

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )

    if success_rate < args.min_success_rate:
        raise SystemExit(
            f"burn-in failed: success_rate={success_rate:.1f}% < {args.min_success_rate:.1f}%"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
