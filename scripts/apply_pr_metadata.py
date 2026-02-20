#!/usr/bin/env python3
"""Apply labels/reviewers to a GitHub PR using gh CLI.

Supports solo-maintainer mode via role mapping file:
- code_owner: real GitHub handle
- ops_owner: real handle or virtual role (e.g. virtual:ops-owner)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(
        cmd,
        text=True,
        check=False,
        capture_output=capture,
    )
    if not capture:
        return p
    return p


def parse_csv(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def is_virtual_reviewer(handle: str) -> bool:
    normalized = handle.strip().lower()
    return normalized.startswith("virtual:") or normalized.endswith("_virtual")


def load_roles(path: str) -> dict[str, str]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in roles file: {path}") from exc


def get_pr_author(pr: str) -> str:
    p = run(
        ["gh", "pr", "view", pr, "--json", "author", "--jq", ".author.login"],
        capture=True,
    )
    if p.returncode != 0:
        return ""
    return p.stdout.strip()


def get_requested_reviewers(
    explicit_reviewers: str, roles_file: str
) -> tuple[list[str], list[str]]:
    if explicit_reviewers.strip():
        return parse_csv(explicit_reviewers), []

    roles = load_roles(roles_file)
    if not roles:
        return [], []

    ordered_roles = [
        ("code_owner", roles.get("code_owner", "")),
        ("ops_owner", roles.get("ops_owner", "")),
    ]
    reviewers: list[str] = []
    virtual_notes: list[str] = []
    for role_name, handle in ordered_roles:
        handle = handle.strip()
        if not handle:
            continue
        reviewers.append(handle)
        if is_virtual_reviewer(handle):
            virtual_notes.append(f"{role_name}={handle}")
    return reviewers, virtual_notes


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item.strip())
    return result


def print_info(message: str) -> None:
    print(message)


def ensure_gh() -> bool:
    if shutil.which("gh") is None:
        fallback = Path("/Users/hojungjung/development/bin")
        candidate = fallback / "gh"
        if candidate.exists():
            os.environ["PATH"] = f"{fallback}:{os.environ.get('PATH', '')}"
    if shutil.which("gh") is None:
        print("gh CLI is not installed. Cannot apply metadata automatically.")
        return False
    return True


def apply_labels(pr: str, labels: list[str]) -> bool:
    if not labels:
        return True
    label_cmd = ["gh", "pr", "edit", pr]
    for label in labels:
        label_cmd.extend(["--add-label", label])
    p = run(label_cmd)
    return p.returncode == 0


def apply_reviewers(pr: str, reviewers: list[str]) -> bool:
    if not reviewers:
        return True
    review_cmd = ["gh", "pr", "edit", pr]
    for reviewer in reviewers:
        review_cmd.extend(["--add-reviewer", reviewer])
    p = run(review_cmd)
    return p.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", required=True, help="PR number")
    parser.add_argument("--labels", default="release,risk:medium,area:ci")
    parser.add_argument(
        "--reviewers",
        default="",
        help="comma-separated GitHub handles (overrides --roles-file)",
    )
    parser.add_argument(
        "--roles-file",
        default=".release/reviewer_roles.json",
        help="JSON file with code_owner/ops_owner reviewer mapping",
    )
    args = parser.parse_args()

    if not ensure_gh():
        return 1

    labels = parse_csv(args.labels)
    if not apply_labels(args.pr, labels):
        return 1

    requested_reviewers, virtual_notes = get_requested_reviewers(
        args.reviewers, args.roles_file
    )
    requested_reviewers = dedupe(requested_reviewers)
    author = get_pr_author(args.pr)

    real_reviewers: list[str] = []
    virtual_reviewers: list[str] = []
    skipped_self: list[str] = []
    for reviewer in requested_reviewers:
        if is_virtual_reviewer(reviewer):
            virtual_reviewers.append(reviewer)
            continue
        if author and reviewer.lower() == author.lower():
            skipped_self.append(reviewer)
            continue
        real_reviewers.append(reviewer)

    applied_ok = apply_reviewers(args.pr, real_reviewers)
    if not applied_ok:
        return 1

    print_info("PR metadata applied successfully.")
    if real_reviewers:
        print_info(f"- real reviewers applied: {', '.join(real_reviewers)}")
    else:
        print_info("- no real reviewers applied")

    if virtual_reviewers:
        print_info(f"- virtual reviewer roles: {', '.join(virtual_reviewers)}")
    if virtual_notes:
        print_info(f"- role mapping notes: {', '.join(virtual_notes)}")
    if skipped_self:
        print_info(f"- skipped self-reviewer(s): {', '.join(skipped_self)}")

    if not real_reviewers and (virtual_reviewers or skipped_self):
        print_info(
            "- solo-maintainer mode detected; use PR template 'PR Metadata Applied' section as approval record."
        )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
