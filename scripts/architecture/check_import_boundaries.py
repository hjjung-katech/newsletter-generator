#!/usr/bin/env python3
"""Architecture import boundary checker with ratchet mode."""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass
class ModuleRoot:
    path: Path
    module_prefix: str


@dataclass
class ImportOccurrence:
    source_file: Path
    source_module: str
    imported: str
    lineno: int


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


def _collect_module_files(module_roots: Sequence[ModuleRoot]) -> Dict[str, Path]:
    module_map: Dict[str, Path] = {}
    for root in module_roots:
        if not root.path.exists():
            continue
        for file_path in sorted(root.path.rglob("*.py")):
            rel = file_path.relative_to(root.path)
            stem = rel.with_suffix("")
            parts = [root.module_prefix] + list(stem.parts)
            if parts[-1] == "__init__":
                parts = parts[:-1]
            module_name = ".".join(parts)
            module_map[module_name] = file_path
    return module_map


def _extract_imports(
    source_module: str, source_file: Path
) -> Iterable[ImportOccurrence]:
    try:
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
    except SyntaxError:
        return

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield ImportOccurrence(
                    source_file=source_file,
                    source_module=source_module,
                    imported=alias.name,
                    lineno=node.lineno,
                )
        elif isinstance(node, ast.ImportFrom):
            base = _relative_module(source_module, node.level, node.module)
            for alias in node.names:
                if alias.name == "*" or not base:
                    imported = base
                else:
                    imported = f"{base}.{alias.name}"
                if imported:
                    yield ImportOccurrence(
                        source_file=source_file,
                        source_module=source_module,
                        imported=imported,
                        lineno=node.lineno,
                    )


def _module_startswith(module_name: str, prefix: str) -> bool:
    return module_name == prefix or module_name.startswith(f"{prefix}.")


def _is_allowed_import(imported: str, allowed_targets: Sequence[str]) -> bool:
    for allowed in allowed_targets:
        if _module_startswith(imported, allowed):
            return True
    return False


def _evaluate_rule(rule: Dict, occ: ImportOccurrence) -> Optional[str]:
    rule_type = rule["type"]

    if rule_type == "forbid_prefix":
        if _module_startswith(
            occ.source_module, rule["source_prefix"]
        ) and _module_startswith(occ.imported, rule["target_prefix"]):
            return rule.get("message", "forbidden import")
        return None

    if rule_type == "allowlist_target_modules":
        if not _module_startswith(occ.source_module, rule["source_prefix"]):
            return None
        if not _module_startswith(occ.imported, rule["target_root"]):
            return None
        if _is_allowed_import(occ.imported, rule.get("allowed_targets", [])):
            return None
        return rule.get("message", "import not in allowlist")

    if rule_type == "target_prefix_allow_source_prefixes":
        if not _module_startswith(occ.imported, rule["target_prefix"]):
            return None
        for allowed in rule.get("allowed_source_prefixes", []):
            if _module_startswith(occ.source_module, allowed):
                return None
        return rule.get("message", "target import not allowed from source")

    raise SystemExit(f"Unsupported rule type: {rule_type}")


def _violation_signature(rule_id: str, occ: ImportOccurrence) -> str:
    return f"{rule_id}|{occ.source_module}|{occ.imported}"


def _load_baseline(path: Path) -> Dict[str, int]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    violations = data.get("violations", {})
    if not isinstance(violations, dict):
        raise SystemExit(f"Invalid baseline violations format: {path}")
    return {str(k): int(v) for k, v in violations.items()}


def _write_baseline(path: Path, violations: Dict[str, int]) -> None:
    payload = {
        "version": 1,
        "generated_at": "2026-02-22",
        "mode": "ratchet",
        "violations": dict(sorted(violations.items())),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check architecture import boundaries")
    parser.add_argument(
        "--rules",
        default="scripts/architecture/boundary_rules.yml",
        help="Path to boundary rules (JSON content)",
    )
    parser.add_argument(
        "--baseline",
        default="scripts/architecture/boundary_baseline.json",
        help="Path to ratchet baseline",
    )
    parser.add_argument(
        "--mode",
        choices=["ratchet", "strict"],
        default="ratchet",
        help="ratchet blocks only new/expanded violations; strict blocks all",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Write current violations into baseline and exit 0",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    rules_path = (repo_root / args.rules).resolve()
    baseline_path = (repo_root / args.baseline).resolve()

    rules_data = _load_json_like(rules_path)
    module_roots = [
        ModuleRoot(
            path=(repo_root / item["path"]).resolve(),
            module_prefix=item["module_prefix"],
        )
        for item in rules_data.get("module_roots", [])
    ]
    rules = rules_data.get("rules", [])

    module_map = _collect_module_files(module_roots)

    detailed: List[Tuple[str, ImportOccurrence, str]] = []
    violation_counts: Dict[str, int] = {}

    for source_module, source_file in module_map.items():
        for occ in _extract_imports(source_module, source_file):
            for rule in rules:
                message = _evaluate_rule(rule, occ)
                if not message:
                    continue
                rule_id = rule["id"]
                sig = _violation_signature(rule_id, occ)
                violation_counts[sig] = violation_counts.get(sig, 0) + 1
                detailed.append((rule_id, occ, message))

    if args.update_baseline:
        _write_baseline(baseline_path, violation_counts)
        print(f"Updated baseline: {baseline_path}")
        print(f"Captured violations: {len(violation_counts)}")
        return 0

    if args.mode == "strict":
        failed_sigs = set(violation_counts.keys())
    else:
        baseline_counts = _load_baseline(baseline_path)
        failed_sigs = {
            sig
            for sig, count in violation_counts.items()
            if count > baseline_counts.get(sig, 0)
        }

    print("=== IMPORT BOUNDARY CHECK ===")
    print(f"Rules file: {rules_path}")
    print(f"Mode: {args.mode}")
    print(f"Scanned modules: {len(module_map)}")
    print(f"Current violations: {len(violation_counts)}")

    if not failed_sigs:
        print("RESULT: PASSED")
        return 0

    print("RESULT: FAILED")
    printed = 0
    for rule_id, occ, message in detailed:
        sig = _violation_signature(rule_id, occ)
        if sig not in failed_sigs:
            continue
        rel_file = occ.source_file.relative_to(repo_root)
        print(
            f"- [{rule_id}] {rel_file}:{occ.lineno} "
            f"{occ.source_module} -> {occ.imported} | {message}"
        )
        printed += 1
        if printed >= 100:
            print("- ... truncated after 100 lines")
            break
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
