#!/usr/bin/env python3
"""Release integration preflight checks.

Purpose:
- Fail fast before creating release/* branches or opening PRs
- Separate environment/setup failures from code failures
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REQUIRED_FILES = [
    ".github/PULL_REQUEST_TEMPLATE/release_integration.md",
    "docs/dev/MAIN_INTEGRATION_EXECUTION_PLAN.md",
    "docs/dev/BRANCH_MAIN_GAP_ANALYSIS.md",
    "Makefile",
]

REQUIRED_CMDS = ["python", "git"]
REQUIRED_PY_PACKAGES = ["flake8", "bandit"]


def run(cmd: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return p.returncode, (p.stdout + p.stderr).strip()
    except Exception as exc:  # defensive runtime error reporting
        return 2, str(exc)


def check_baseline_tag(tag: str) -> tuple[bool, str]:
    code, out = run(["git", "rev-parse", "--verify", tag])
    return (code == 0, out if out else f"missing tag: {tag}")


def check_python_package(pkg: str) -> tuple[bool, str]:
    code, out = run([sys.executable, "-m", "pip", "show", pkg])
    return (code == 0, out.splitlines()[0] if out else f"missing package: {pkg}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-tag", default="baseline/main-equivalent")
    args = parser.parse_args()

    failures: list[str] = []
    warnings: list[str] = []

    # command checks
    for cmd in REQUIRED_CMDS:
        if shutil.which(cmd) is None:
            failures.append(f"missing command: {cmd}")

    # file checks
    for rel in REQUIRED_FILES:
        if not Path(rel).exists():
            failures.append(f"missing file: {rel}")

    ok, msg = check_baseline_tag(args.baseline_tag)
    if not ok:
        failures.append(f"baseline tag check failed: {msg}")

    for pkg in REQUIRED_PY_PACKAGES:
        ok, msg = check_python_package(pkg)
        if not ok:
            failures.append(f"required package unavailable: {pkg} ({msg})")

    print("=== RELEASE PREFLIGHT REPORT ===")
    print(f"baseline tag: {args.baseline_tag}")

    if warnings:
        print("\n[WARNINGS]")
        for w in warnings:
            print(f"- {w}")

    if failures:
        print("\n[FAILURES]")
        for f in failures:
            print(f"- {f}")
        print("\nRESULT: FAILED (preflight)")
        return 1

    print("\nRESULT: PASSED (preflight)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
