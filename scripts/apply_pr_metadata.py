#!/usr/bin/env python3
"""Apply labels/reviewers to a GitHub PR using gh CLI."""

from __future__ import annotations

import argparse
import shutil
import subprocess


def run(cmd: list[str]) -> int:
    p = subprocess.run(cmd, text=True, check=False)
    return p.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", required=True, help="PR number")
    parser.add_argument("--labels", default="release,risk:medium,area:ci")
    parser.add_argument("--reviewers", default="", help="comma-separated GitHub handles")
    args = parser.parse_args()

    if shutil.which("gh") is None:
        print("gh CLI is not installed. Cannot apply metadata automatically.")
        return 1

    labels = [x.strip() for x in args.labels.split(",") if x.strip()]
    label_cmd = ["gh", "pr", "edit", args.pr]
    for label in labels:
        label_cmd.extend(["--add-label", label])
    if run(label_cmd) != 0:
        return 1

    reviewers = [x.strip() for x in args.reviewers.split(",") if x.strip()]
    if reviewers:
        review_cmd = ["gh", "pr", "edit", args.pr]
        for reviewer in reviewers:
            review_cmd.extend(["--add-reviewer", reviewer])
        if run(review_cmd) != 0:
            return 1

    print("PR metadata applied successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
