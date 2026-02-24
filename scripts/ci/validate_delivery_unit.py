#!/usr/bin/env python3
"""Validate RR/Delivery Unit governance rules for pull requests."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any, Iterable, Tuple

RR_PATTERN = re.compile(r"RR\s*:\s*#(\d+)", re.IGNORECASE)
DELIVERY_UNIT_PATTERN = re.compile(
    r"Delivery Unit ID\s*:\s*([A-Za-z0-9._-]+)", re.IGNORECASE
)

EXEMPT_COMMIT_COUNT_LABELS = {"docs-only", "trivial", "hotfix"}
MIN_COMMITS = 2
MAX_COMMITS = 6


def _parse_next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip().split(";")
        if len(section) < 2:
            continue
        url_part = section[0].strip()
        rel_part = section[1].strip()
        if (
            rel_part == 'rel="next"'
            and url_part.startswith("<")
            and url_part.endswith(">")
        ):
            return url_part[1:-1]
    return None


def _github_paginate(url: str, token: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    next_url: str | None = url
    while next_url:
        req = urllib.request.Request(
            next_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "delivery-unit-validator",
            },
        )
        try:
            with urllib.request.urlopen(req) as resp:
                payload = json.load(resp)
                if not isinstance(payload, list):
                    raise RuntimeError(f"Unexpected GitHub payload type at {next_url}")
                entries.extend(payload)
                next_url = _parse_next_link(resp.headers.get("Link"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"GitHub API request failed: {exc.code} {exc.reason} ({next_url}) {body}"
            ) from exc
    return entries


def _extract_rr_and_du(pr_body: str) -> Tuple[int | None, str | None]:
    rr_match = RR_PATTERN.search(pr_body or "")
    du_match = DELIVERY_UNIT_PATTERN.search(pr_body or "")

    rr_number = int(rr_match.group(1)) if rr_match else None
    delivery_unit = du_match.group(1).strip() if du_match else None
    return rr_number, delivery_unit


def _non_merge_commit_count(commit_data: Iterable[dict[str, Any]]) -> int:
    count = 0
    for commit in commit_data:
        message = commit.get("commit", {}).get("message", "")
        first_line = message.splitlines()[0].strip() if message else ""
        if first_line.startswith("Merge "):
            continue
        count += 1
    return count


def main() -> int:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")

    errors: list[str] = []

    if not event_path or not os.path.exists(event_path):
        errors.append("GITHUB_EVENT_PATH is missing or invalid.")
    if not repository or "/" not in repository:
        errors.append("GITHUB_REPOSITORY is missing or invalid.")
    if not token:
        errors.append("GITHUB_TOKEN is missing.")
    if errors:
        print("\n".join(errors))
        return 1

    with open(event_path, "r", encoding="utf-8") as fh:
        event = json.load(fh)
    pr = event.get("pull_request") or {}
    pr_number = pr.get("number")
    pr_body = pr.get("body") or ""
    labels = {label.get("name", "") for label in pr.get("labels", [])}

    if not pr_number:
        print("No pull_request payload found in event.")
        return 1

    if "## Delivery Unit" not in pr_body:
        errors.append("Missing PR section: `## Delivery Unit`.")

    rr_number, delivery_unit = _extract_rr_and_du(pr_body)
    if rr_number is None:
        errors.append("Missing `RR: #<number>` in `## Delivery Unit` section.")
    if not delivery_unit:
        errors.append("Missing `Delivery Unit ID: <id>` in `## Delivery Unit` section.")
    if not re.search(r"Merge Boundary\s*:\s*\S+", pr_body, re.IGNORECASE):
        errors.append(
            "Missing non-empty `Merge Boundary:` in `## Delivery Unit` section."
        )
    if not re.search(r"Rollback Boundary\s*:\s*\S+", pr_body, re.IGNORECASE):
        errors.append(
            "Missing non-empty `Rollback Boundary:` in `## Delivery Unit` section."
        )

    owner, repo = repository.split("/", 1)
    api_base = f"https://api.github.com/repos/{owner}/{repo}"

    open_prs = _github_paginate(f"{api_base}/pulls?state=open&per_page=100", token)
    conflicting_rr: list[int] = []
    conflicting_du: list[int] = []
    for open_pr in open_prs:
        other_number = open_pr.get("number")
        if other_number == pr_number:
            continue
        other_rr, other_du = _extract_rr_and_du(open_pr.get("body") or "")
        if rr_number is not None and other_rr == rr_number:
            conflicting_rr.append(other_number)
        if delivery_unit and other_du and other_du.lower() == delivery_unit.lower():
            conflicting_du.append(other_number)

    if conflicting_rr:
        errors.append(
            "RR is already linked to another open PR: "
            + ", ".join(f"#{n}" for n in sorted(conflicting_rr))
        )
    if conflicting_du:
        errors.append(
            "Delivery Unit ID is already used by another open PR: "
            + ", ".join(f"#{n}" for n in sorted(conflicting_du))
        )

    exempt = not labels.isdisjoint(EXEMPT_COMMIT_COUNT_LABELS)
    if not exempt:
        commit_data = _github_paginate(
            f"{api_base}/pulls/{pr_number}/commits?per_page=100", token
        )
        commit_count = _non_merge_commit_count(commit_data)
        if commit_count < MIN_COMMITS or commit_count > MAX_COMMITS:
            errors.append(
                "Commit count out of policy range: "
                f"{commit_count} (expected {MIN_COMMITS}-{MAX_COMMITS}, "
                "labels to exempt: docs-only|trivial|hotfix)."
            )

    if errors:
        print("\n".join(errors))
        return 1

    print("Delivery unit governance check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
