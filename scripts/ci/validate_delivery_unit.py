#!/usr/bin/env python3
"""Validate RR/Delivery Unit governance rules for pull requests."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any, Iterable

RR_VALUE_PATTERN = re.compile(r"#(\d+)")
PLACEHOLDER_PATTERN = re.compile(r"<[^>\n]+>")

EXEMPT_COMMIT_COUNT_LABELS = {"docs-only", "trivial", "hotfix"}
MIN_COMMITS = 1
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


def _extract_field_value(pr_body: str, label: str) -> str | None:
    pattern = re.compile(
        rf"(?im)^[ \t]*[-*]?[ \t]*{re.escape(label)}[ \t]*:[ \t]*(.*?)\s*$"
    )
    match = pattern.search(pr_body or "")
    if not match:
        return None
    return match.group(1).strip()


def _looks_like_placeholder(value: str | None) -> bool:
    if not value:
        return False
    return bool(PLACEHOLDER_PATTERN.search(value.strip()))


def _validate_delivery_unit_fields(
    pr_body: str,
) -> tuple[list[str], int | None, str | None]:
    errors: list[str] = []
    rr_number: int | None = None
    delivery_unit: str | None = None

    if "## Delivery Unit" not in pr_body:
        errors.append("Missing PR section: `## Delivery Unit`.")

    rr_value = _extract_field_value(pr_body, "RR")
    if rr_value is None:
        errors.append("Missing `RR: #<number>` in `## Delivery Unit` section.")
    elif _looks_like_placeholder(rr_value):
        errors.append(
            "Placeholder `RR: #<n>` must be replaced in `## Delivery Unit` section."
        )
    else:
        rr_match = RR_VALUE_PATTERN.fullmatch(rr_value)
        if rr_match is None:
            errors.append("Invalid `RR: #<number>` in `## Delivery Unit` section.")
        else:
            rr_number = int(rr_match.group(1))

    delivery_unit_value = _extract_field_value(pr_body, "Delivery Unit ID")
    if delivery_unit_value is None or not delivery_unit_value:
        errors.append("Missing `Delivery Unit ID: <id>` in `## Delivery Unit` section.")
    elif _looks_like_placeholder(delivery_unit_value):
        errors.append(
            "Placeholder `Delivery Unit ID:` value must be replaced in "
            "`## Delivery Unit` section."
        )
    else:
        delivery_unit = delivery_unit_value

    for label in ("Merge Boundary", "Rollback Boundary"):
        value = _extract_field_value(pr_body, label)
        if value is None or not value:
            errors.append(
                f"Missing non-empty `{label}:` in `## Delivery Unit` section."
            )
        elif _looks_like_placeholder(value):
            errors.append(
                f"Placeholder `{label}:` value must be replaced in "
                "`## Delivery Unit` section."
            )

    return errors, rr_number, delivery_unit


def _extract_rr_and_du(pr_body: str) -> tuple[int | None, str | None]:
    _, rr_number, delivery_unit = _validate_delivery_unit_fields(pr_body or "")
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

    body_errors, rr_number, delivery_unit = _validate_delivery_unit_fields(pr_body)
    errors.extend(body_errors)

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
