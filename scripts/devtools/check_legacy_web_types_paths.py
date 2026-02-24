#!/usr/bin/env python3
"""Fail CI when legacy web_types references reappear outside allowlisted files."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROOTS = ("web", "scripts", "tests")
ALLOWLIST = {
    Path("web/runtime_hook.py"),
    Path("tests/unit_tests/web/test_runtime_hook_bootstrap.py"),
}
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("legacy module path", re.compile(r"web/web_types\.py")),
    ("legacy dotted import", re.compile(r"\bweb\.web_types\b")),
    (
        "legacy dynamic module name",
        re.compile(r"""spec_from_file_location\(\s*["']web_types["']"""),
    ),
    (
        "legacy import statement",
        re.compile(r"^\s*(?:from|import)\s+web_types\b", re.MULTILINE),
    ),
)


@dataclass(frozen=True)
class Finding:
    rel_path: Path
    line: int
    rule: str
    snippet: str


def _line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _scan_file(rel_path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for rule, pattern in PATTERNS:
        for match in pattern.finditer(text):
            findings.append(
                Finding(
                    rel_path=rel_path,
                    line=_line_number(text, match.start()),
                    rule=rule,
                    snippet=match.group(0).strip(),
                )
            )
    return findings


def _iter_python_files(repo_root: Path, roots: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        root_path = repo_root / root
        if not root_path.exists():
            continue
        files.extend(root_path.rglob("*.py"))
    return sorted(set(files))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--roots",
        nargs="*",
        default=list(DEFAULT_ROOTS),
        help="Relative roots to scan (default: web scripts tests).",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    roots = tuple(args.roots)
    findings: list[Finding] = []

    for file_path in _iter_python_files(repo_root, roots):
        rel_path = file_path.relative_to(repo_root)
        if rel_path in ALLOWLIST:
            continue

        text = file_path.read_text(encoding="utf-8", errors="replace")
        findings.extend(_scan_file(rel_path, text))

    if findings:
        print(
            "Legacy web_types references are not allowed outside compatibility files:"
        )
        for item in findings:
            print(f"- {item.rel_path}:{item.line} [{item.rule}] {item.snippet}")
        return 1

    print("No legacy web_types references detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
