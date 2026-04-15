#!/usr/bin/env python3
"""Measure LOC and complexity for frozen maintenance-mode shell modules.

Exit code is always 0 (soft-gate — CI blocking is not intended).
Output: GitHub-flavoured Markdown table suitable for PR comments / Step Summary.

Freeze modules declared in ARCHITECTURE.md §0.2 and PRD.md §5:
  newsletter/llm_factory.py, newsletter/tools.py, newsletter/graph.py,
  web/routes_generation.py, web/static/js/app.js
"""

from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Freeze-module manifest
# ---------------------------------------------------------------------------

FREEZE_MODULES = [
    "newsletter/llm_factory.py",
    "newsletter/tools.py",
    "newsletter/graph.py",
    "web/routes_generation.py",
    "web/static/js/app.js",
]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class ModuleStats(NamedTuple):
    path: str
    loc: int  # non-empty, non-comment physical lines
    functions: int  # function / method definitions
    max_complexity: int  # McCabe estimate (.py) or total branch count (.js)


# ---------------------------------------------------------------------------
# Python analysis — standard-library ast only
# ---------------------------------------------------------------------------


class _ComplexityVisitor(ast.NodeVisitor):
    """Accumulate McCabe-style branch points inside a single function."""

    def __init__(self) -> None:
        self.complexity = 1  # every function starts with one execution path

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # `and` / `or` — each extra operand is a branch point
        self.complexity += len(node.values) - 1
        self.generic_visit(node)


def _function_complexity(func: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    v = _ComplexityVisitor()
    v.visit(func)
    return v.complexity


def _analyze_python(path: Path) -> tuple[int, int, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    loc = sum(
        1
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    )
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return loc, 0, 0

    funcs = [
        n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    max_cc = max((_function_complexity(f) for f in funcs), default=0)
    return loc, len(funcs), max_cc


# ---------------------------------------------------------------------------
# JavaScript analysis — regex-based (no external parser)
# ---------------------------------------------------------------------------

_JS_FUNC_RE = re.compile(
    r"\bfunction\s+\w+\s*\("  # function foo(
    r"|\bfunction\s*\("  # anonymous: function(
    r"|\b\w+\s*[:=]\s*function\s*\("  # x = function(  |  x: function(
    r"|\([^)]*\)\s*=>"  # (params) =>
    r"|\b\w+\s*=>"  # param =>
)
_JS_BRANCH_RE = re.compile(r"\b(?:if|else\s+if|for|while|catch|case)\b|&&|\|\|")


def _analyze_js(path: Path) -> tuple[int, int, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    loc = sum(1 for line in text.splitlines() if line.strip())
    functions = len(_JS_FUNC_RE.findall(text))
    # Per-function complexity not feasible without a JS parser;
    # report total branch count as a size proxy instead.
    branches = len(_JS_BRANCH_RE.findall(text))
    return loc, functions, branches


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def analyze(module_rel: str, repo_root: Path) -> ModuleStats:
    p = repo_root / module_rel
    if not p.exists():
        return ModuleStats(module_rel, -1, -1, -1)
    if module_rel.endswith(".py"):
        loc, funcs, max_cc = _analyze_python(p)
    elif module_rel.endswith(".js"):
        loc, funcs, max_cc = _analyze_js(p)
    else:
        text = p.read_text(encoding="utf-8", errors="replace")
        loc = sum(1 for line in text.splitlines() if line.strip())
        funcs, max_cc = 0, 0
    return ModuleStats(module_rel, loc, funcs, max_cc)


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------


def render_markdown(stats: list[ModuleStats]) -> str:
    lines = [
        "## Freeze Module Size Report",
        "",
        "| Module | LOC | Functions | Max Complexity |",
        "|--------|----:|----------:|---------------:|",
    ]
    for s in stats:
        loc = str(s.loc) if s.loc >= 0 else "N/A"
        funcs = str(s.functions) if s.functions >= 0 else "N/A"
        cc = str(s.max_complexity) if s.max_complexity >= 0 else "N/A"
        lines.append(f"| `{s.path}` | {loc} | {funcs} | {cc} |")
    lines += [
        "",
        "_LOC: non-empty non-comment lines. "
        "Max Complexity: McCabe estimate per function (`.py`) "
        "/ total branch count (`.js`)._",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    stats = [analyze(m, repo_root) for m in FREEZE_MODULES]
    report = render_markdown(stats)
    print(report)

    # Write to GitHub Step Summary when running in CI (works for fork PRs too)
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as fh:
            fh.write(report + "\n")

    return 0  # always 0 — soft-gate, must never block CI


if __name__ == "__main__":
    sys.exit(main())
