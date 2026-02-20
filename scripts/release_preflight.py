#!/usr/bin/env python3
"""Release integration preflight checks."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REQUIRED_FILES = [
    ".github/PULL_REQUEST_TEMPLATE/release_integration.md",
    "docs/dev/MAIN_INTEGRATION_EXECUTION_PLAN.md",
    "docs/dev/BRANCH_MAIN_GAP_ANALYSIS.md",
    "Makefile",
    ".release/baseline.json",
    ".release/manifests/release-ci-platform.txt",
]
REQUIRED_CMD_GROUPS = [
    ("python", "python3"),
    ("git",),
]
REQUIRED_PY_PACKAGES = ["flake8", "bandit"]


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return p.returncode, (p.stdout + p.stderr).strip()


def git_rev_parse(ref: str) -> tuple[bool, str]:
    code, out = run(["git", "rev-parse", "--verify", ref])
    return code == 0, out.strip()


def load_baseline() -> tuple[dict, str]:
    path = Path(".release/baseline.json")
    if not path.exists():
        return {}, "missing file: .release/baseline.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, f"invalid baseline json: {exc}"

    for key in ["tag", "commit", "owner"]:
        if not data.get(key):
            return {}, f"baseline json missing required key: {key}"
    return data, ""


def check_python_package(pkg: str) -> tuple[bool, str]:
    code, out = run([sys.executable, "-m", "pip", "show", pkg])
    return code == 0, (out.splitlines()[0] if out else f"missing package: {pkg}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-tag", default="")
    args = parser.parse_args()

    failures: list[str] = []

    for cmd_group in REQUIRED_CMD_GROUPS:
        if not any(shutil.which(cmd) for cmd in cmd_group):
            failures.append(f"missing command: {' or '.join(cmd_group)}")

    for rel in REQUIRED_FILES:
        if not Path(rel).exists():
            failures.append(f"missing file: {rel}")

    baseline, baseline_err = load_baseline()
    if baseline_err:
        failures.append(baseline_err)
        baseline_tag = args.baseline_tag or "baseline/main-equivalent"
        baseline_commit = ""
    else:
        baseline_tag = args.baseline_tag or baseline["tag"]
        baseline_commit = baseline["commit"]

    ok_tag, tag_sha = git_rev_parse(baseline_tag)
    if not ok_tag:
        failures.append(f"baseline tag check failed: missing tag `{baseline_tag}`")

    if baseline_commit and ok_tag:
        # allow short commit ids in config
        if not tag_sha.startswith(baseline_commit):
            failures.append(
                "baseline tag "
                f"`{baseline_tag}` mismatch: expected {baseline_commit}, "
                f"got {tag_sha[:12]}"
            )

    for pkg in REQUIRED_PY_PACKAGES:
        ok, msg = check_python_package(pkg)
        if not ok:
            failures.append(f"required package unavailable: {pkg} ({msg})")

    print("=== RELEASE PREFLIGHT REPORT ===")
    print(f"baseline tag: {baseline_tag}")
    if baseline_commit:
        print(f"baseline commit(expected): {baseline_commit}")

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
