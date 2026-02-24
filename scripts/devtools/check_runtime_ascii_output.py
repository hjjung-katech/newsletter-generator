#!/usr/bin/env python3
"""Fail when runtime print/logger literals contain non-ASCII characters.

Windows CI runners can use legacy console encodings; non-ASCII startup/output
messages have caused flaky EXE smoke failures. This guard keeps critical runtime
messages ASCII-safe.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path

DEFAULT_FILES = [
    "web/app.py",
    "web/newsletter_clients.py",
    "web/runtime_hook.py",
    "web/binary_compatibility.py",
]

LOG_METHODS = {"debug", "info", "warning", "error", "critical", "exception"}


@dataclass
class Violation:
    file_path: Path
    line: int
    call_name: str
    text: str


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _string_literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value

    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                parts.append("{expr}")
        return "".join(parts)

    return None


def _is_runtime_output_call(call_name: str) -> bool:
    if call_name == "print":
        return True

    parts = call_name.split(".")
    if not parts:
        return False

    if parts[-1] in LOG_METHODS and (
        "logger" in parts or parts[0] == "logging" or "logging" in parts
    ):
        return True

    return False


def _scan_file(file_path: Path) -> list[Violation]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    violations: list[Violation] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        call_name = _call_name(node.func)
        if not _is_runtime_output_call(call_name):
            continue

        candidate_args: list[ast.AST] = []
        if node.args:
            candidate_args.append(node.args[0])
        for keyword in node.keywords:
            if keyword.arg in {"msg", "message"}:
                candidate_args.append(keyword.value)

        for candidate in candidate_args:
            text = _string_literal(candidate)
            if text is None or text.isascii():
                continue
            violations.append(
                Violation(
                    file_path=file_path,
                    line=getattr(candidate, "lineno", getattr(node, "lineno", 1)),
                    call_name=call_name,
                    text=text,
                )
            )

    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "files",
        nargs="*",
        help="Target files. Defaults to startup/runtime critical web files.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    file_args = args.files or DEFAULT_FILES
    paths = [repo_root / item for item in file_args]

    missing = [path for path in paths if not path.exists()]
    if missing:
        for path in missing:
            print(f"[ASCII-GUARD] Missing file: {path}")
        return 2

    violations: list[Violation] = []
    for path in paths:
        violations.extend(_scan_file(path))

    if violations:
        print("[ASCII-GUARD] Non-ASCII runtime output literals detected:")
        for item in violations:
            preview = item.text.encode("ascii", "backslashreplace").decode("ascii")
            print(f"- {item.file_path}:{item.line} [{item.call_name}] {preview[:120]}")
        return 1

    print("[ASCII-GUARD] PASS - runtime output literals are ASCII-safe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
