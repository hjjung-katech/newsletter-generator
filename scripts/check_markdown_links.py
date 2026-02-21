#!/usr/bin/env python3
"""Check internal Markdown link integrity for tracked .md files."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
CODE_FENCE_RE = re.compile(r"^```")
LINK_RE = re.compile(r"(?<!\!)\[[^\]]+\]\(([^)]+)\)")

EXTERNAL_PREFIXES = (
    "http://",
    "https://",
    "mailto:",
    "tel:",
    "data:",
)


def tracked_markdown_files() -> list[Path]:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(ROOT), "ls-files", "*.md"],
            text=True,
        )
    except subprocess.CalledProcessError:
        return sorted(ROOT.rglob("*.md"))
    return [ROOT / line.strip() for line in out.splitlines() if line.strip()]


def normalize_target(raw_target: str) -> str:
    target = raw_target.strip()

    # Trim optional title in links like: (path "title")
    if " " in target and not target.startswith("<"):
        first, _rest = target.split(" ", 1)
        target = first

    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]

    return unquote(target)


def is_external(target: str) -> bool:
    return target.startswith(EXTERNAL_PREFIXES)


def validate_link(file_path: Path, target: str) -> bool:
    if not target or target == "#" or target.startswith("#"):
        return True

    if is_external(target):
        return True

    target_path = target.split("#", 1)[0]
    if not target_path:
        return True

    if target_path.startswith("/"):
        candidate = ROOT / target_path.lstrip("/")
    else:
        candidate = (file_path.parent / target_path).resolve()

    return candidate.exists()


def main() -> int:
    failures: list[str] = []

    for file_path in tracked_markdown_files():
        if not file_path.exists():
            # Allow renamed/deleted files in working tree before commit.
            continue
        in_code_block = False
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            failures.append(f"{file_path}: unable to read as UTF-8")
            continue

        for lineno, line in enumerate(lines, start=1):
            if CODE_FENCE_RE.match(line.strip()):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            for match in LINK_RE.finditer(line):
                target = normalize_target(match.group(1))
                if not validate_link(file_path, target):
                    rel_file = file_path.relative_to(ROOT)
                    failures.append(f"{rel_file}:{lineno} broken link -> {target}")

    if failures:
        print("Broken markdown links detected:")
        for issue in failures:
            print(f"- {issue}")
        return 1

    print("Markdown link integrity check passed (0 broken internal links).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
