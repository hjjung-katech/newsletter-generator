#!/usr/bin/env python3
"""Module import cycle checker (fails on SCC size > 1)."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set


def _load_json_like(path: Path) -> Dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid rules format in {path}: {exc}") from exc


def _relative_module(source_module: str, level: int, module: Optional[str]) -> str:
    if level == 0:
        return module or ""

    package = source_module.split(".")[:-1]
    up = level - 1
    if up >= len(package):
        base: List[str] = []
    else:
        base = package[: len(package) - up]

    if module:
        return ".".join(base + [module])
    return ".".join(base)


def _collect_modules(repo_root: Path, rules_data: Dict) -> Dict[str, Path]:
    module_map: Dict[str, Path] = {}
    for root in rules_data.get("module_roots", []):
        root_path = (repo_root / root["path"]).resolve()
        module_prefix = root["module_prefix"]
        if not root_path.exists():
            continue
        for file_path in sorted(root_path.rglob("*.py")):
            rel = file_path.relative_to(root_path)
            stem = rel.with_suffix("")
            parts = [module_prefix] + list(stem.parts)
            if parts[-1] == "__init__":
                parts = parts[:-1]
            module_name = ".".join(parts)
            module_map[module_name] = file_path
    return module_map


def _iter_import_strings(source_module: str, source_file: Path) -> Iterable[str]:
    try:
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
    except SyntaxError:
        return

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            base = _relative_module(source_module, node.level, node.module)
            if not base:
                continue
            for alias in node.names:
                if alias.name == "*":
                    yield base
                else:
                    yield f"{base}.{alias.name}"


def _resolve_known_module(imported: str, known_modules: Set[str]) -> Optional[str]:
    parts = imported.split(".")
    while parts:
        candidate = ".".join(parts)
        if candidate in known_modules:
            return candidate
        parts.pop()
    return None


def _tarjan_scc(graph: Dict[str, Set[str]]) -> List[List[str]]:
    index = 0
    stack: List[str] = []
    on_stack: Set[str] = set()
    indexes: Dict[str, int] = {}
    lowlinks: Dict[str, int] = {}
    sccs: List[List[str]] = []

    def strongconnect(node: str) -> None:
        nonlocal index
        indexes[node] = index
        lowlinks[node] = index
        index += 1

        stack.append(node)
        on_stack.add(node)

        for nxt in graph.get(node, set()):
            if nxt not in indexes:
                strongconnect(nxt)
                lowlinks[node] = min(lowlinks[node], lowlinks[nxt])
            elif nxt in on_stack:
                lowlinks[node] = min(lowlinks[node], indexes[nxt])

        if lowlinks[node] == indexes[node]:
            comp: List[str] = []
            while True:
                popped = stack.pop()
                on_stack.remove(popped)
                comp.append(popped)
                if popped == node:
                    break
            sccs.append(comp)

    for node in graph:
        if node not in indexes:
            strongconnect(node)

    return sccs


def main() -> int:
    parser = argparse.ArgumentParser(description="Check module import cycles")
    parser.add_argument(
        "--rules",
        default="scripts/architecture/boundary_rules.yml",
        help="Path to boundary rules (JSON content)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    rules_path = (repo_root / args.rules).resolve()
    rules_data = _load_json_like(rules_path)

    module_map = _collect_modules(repo_root, rules_data)
    known_modules = set(module_map.keys())
    graph: Dict[str, Set[str]] = {name: set() for name in known_modules}

    for source_module, source_file in module_map.items():
        for imported in _iter_import_strings(source_module, source_file):
            resolved = _resolve_known_module(imported, known_modules)
            if resolved and resolved != source_module:
                graph[source_module].add(resolved)

    sccs = _tarjan_scc(graph)
    cycles = [sorted(comp) for comp in sccs if len(comp) > 1]

    print("=== IMPORT CYCLE CHECK ===")
    print(f"Rules file: {rules_path}")
    print(f"Scanned modules: {len(module_map)}")
    print(f"Cycles (SCC>1): {len(cycles)}")

    if not cycles:
        print("RESULT: PASSED")
        return 0

    print("RESULT: FAILED")
    for idx, cycle in enumerate(sorted(cycles, key=len, reverse=True), start=1):
        print(f"- Cycle #{idx} (size={len(cycle)}):")
        for module in cycle:
            print(f"  - {module}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
