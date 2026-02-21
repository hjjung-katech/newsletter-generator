#!/usr/bin/env python3
"""Run lightweight Markdown style checks.

Default scope is changed Markdown files (vs origin/main when available),
so legacy baseline noise does not block incremental improvements.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git_output(args: list[str]) -> str:
    try:
        return subprocess.check_output(
            args, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except subprocess.CalledProcessError:
        return ""


def tracked_markdown_files() -> list[Path]:
    out = git_output(["git", "-C", str(ROOT), "ls-files", "*.md"])
    if not out:
        return sorted(ROOT.rglob("*.md"))
    return [ROOT / line for line in out.splitlines() if line]


def changed_markdown_files() -> list[Path]:
    # Preferred scope for branch work.
    out = git_output(
        [
            "git",
            "-C",
            str(ROOT),
            "diff",
            "--name-only",
            "--diff-filter=ACMRTUXB",
            "origin/main...HEAD",
            "--",
            "*.md",
        ]
    )
    if out:
        return [ROOT / line for line in out.splitlines() if line]

    # Fallback: local unstaged + staged markdown changes.
    unstaged = git_output(
        [
            "git",
            "-C",
            str(ROOT),
            "diff",
            "--name-only",
            "--diff-filter=ACMRTUXB",
            "--",
            "*.md",
        ]
    )
    staged = git_output(
        [
            "git",
            "-C",
            str(ROOT),
            "diff",
            "--cached",
            "--name-only",
            "--diff-filter=ACMRTUXB",
            "--",
            "*.md",
        ]
    )
    paths = {line for line in (unstaged.splitlines() + staged.splitlines()) if line}
    return [ROOT / line for line in sorted(paths)]


def resolve_files_from_args(args: list[str]) -> list[Path]:
    if not args:
        return []

    files: list[Path] = []
    for raw in args:
        path = Path(raw)
        if not path.is_absolute():
            path = ROOT / path
        files.append(path)
    return files


def main() -> int:
    # Optional explicit file list support.
    explicit_files = resolve_files_from_args(sys.argv[1:])
    if explicit_files:
        markdown_files = explicit_files
    else:
        markdown_files = changed_markdown_files() or tracked_markdown_files()

    issues: list[str] = []

    for file_path in markdown_files:
        if not file_path.exists() or file_path.suffix.lower() != ".md":
            continue

        rel_file = file_path.relative_to(ROOT)
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            issues.append(f"{rel_file}: unable to read as UTF-8")
            continue

        in_code_block = False
        has_h1 = False

        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            if line.endswith(" "):
                issues.append(f"{rel_file}:{lineno} trailing whitespace")
            if "\t" in line:
                issues.append(f"{rel_file}:{lineno} tab character")
            if stripped.startswith("# "):
                has_h1 = True

        if not has_h1:
            issues.append(f"{rel_file}: missing level-1 heading")

    if issues:
        print("Markdown style check failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("Markdown style check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
