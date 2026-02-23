#!/usr/bin/env python3
"""Generate top-level repository inventory and soft hygiene policy checks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any


def run_git(
    repo_root: Path, args: list[str], check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=check,
        capture_output=True,
        text=True,
    )


def git_root(start_dir: Path) -> Path:
    try:
        result = run_git(start_dir, ["rev-parse", "--show-toplevel"])
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Not a git repository") from exc
    return Path(result.stdout.strip()).resolve()


def git_ls_files(repo_root: Path) -> list[str]:
    result = run_git(repo_root, ["ls-files", "-z"])
    raw = result.stdout
    return [path for path in raw.split("\x00") if path]


def git_check_ignore(repo_root: Path, path: str) -> bool:
    result = run_git(repo_root, ["check-ignore", path], check=False)
    return result.returncode == 0


def load_policy(policy_path: Path) -> dict[str, Any]:
    raw = policy_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Policy JSON must be an object")
    return data


def match_any(name: str, patterns: list[str]) -> bool:
    return any(fnmatch(name, pattern) for pattern in patterns)


def classify_action(
    *,
    name: str,
    entry_type: str,
    git_state: str,
    root_policy: dict[str, Any],
) -> tuple[str, str]:
    move_globs = root_policy.get("move_to_scripts_file_globs", [])
    ignore_files = root_policy.get("ignore_file_globs", [])
    ignore_dirs = root_policy.get("ignore_directory_names", [])
    allow_files = root_policy.get("allowed_file_names", [])
    allow_file_globs = root_policy.get("allowed_file_globs", [])
    allow_dirs = root_policy.get("allowed_directory_names", [])

    if entry_type == "file" and match_any(name, move_globs):
        return (
            "move_to_scripts_devtools",
            "루트 실행/유틸 스크립트는 scripts/devtools로 이동",
        )

    if entry_type == "file" and match_any(name, ignore_files):
        return ("ignore_or_remove_local", "로컬 생성 산출물은 ignore 또는 정리")

    if entry_type == "directory" and name in ignore_dirs:
        return ("ignore_or_remove_local", "로컬 캐시/생성 디렉터리는 ignore 또는 정리")

    if git_state == "ignored":
        return ("ignore_or_remove_local", "이미 ignore된 로컬/생성 리소스")

    if git_state == "local-only":
        return (
            "review_or_ignore",
            "추적되지 않은 루트 엔트리. 정책 반영 또는 ignore 필요",
        )

    if entry_type == "file":
        if name in allow_files or match_any(name, allow_file_globs):
            return ("keep_in_root", "루트 허용 파일(메타/빌드/운영 진입)")
        return ("review_for_relocation", "루트 허용 목록 외 파일. 이동/삭제 검토")

    if entry_type == "directory":
        if name in allow_dirs:
            return ("keep_in_root", "루트 허용 디렉터리")
        return ("review_for_relocation", "루트 허용 목록 외 디렉터리. 이동/삭제 검토")

    return ("review_for_relocation", "정책 수동 검토 필요")


def allowed_root_entry(name: str, entry_type: str, root_policy: dict[str, Any]) -> bool:
    if entry_type == "file":
        names = root_policy.get("allowed_file_names", [])
        globs = root_policy.get("allowed_file_globs", [])
        return name in names or match_any(name, globs)
    if entry_type == "directory":
        names = root_policy.get("allowed_directory_names", [])
        return name in names
    return False


@dataclass(frozen=True)
class RootEntry:
    name: str
    entry_type: str
    git_state: str
    action: str
    rationale: str


def collect_root_entries(repo_root: Path, policy: dict[str, Any]) -> list[RootEntry]:
    tracked_files = git_ls_files(repo_root)
    tracked_roots = {path.split("/", 1)[0] for path in tracked_files}
    root_policy = policy.get("root_policy", {})

    entries: list[RootEntry] = []
    for path in sorted(repo_root.iterdir(), key=lambda p: p.name):
        if path.name == ".git":
            continue

        if path.is_dir():
            entry_type = "directory"
        elif path.is_file():
            entry_type = "file"
        elif path.is_symlink():
            entry_type = "symlink"
        else:
            entry_type = "other"

        if path.name in tracked_roots:
            git_state = "tracked"
        elif git_check_ignore(repo_root, path.name):
            git_state = "ignored"
        else:
            git_state = "local-only"

        action, rationale = classify_action(
            name=path.name,
            entry_type=entry_type,
            git_state=git_state,
            root_policy=root_policy,
        )
        entries.append(
            RootEntry(
                name=path.name,
                entry_type=entry_type,
                git_state=git_state,
                action=action,
                rationale=rationale,
            )
        )

    return entries


def dot_scope_warnings(repo_root: Path, policy: dict[str, Any]) -> list[str]:
    tracked_files = git_ls_files(repo_root)
    dot_policy = policy.get("dot_directory_policy", {})
    warnings: list[str] = []

    for dot_dir, cfg in dot_policy.items():
        allow_globs = cfg.get("allowed_tracked_file_globs", [])
        tracked = [
            path
            for path in tracked_files
            if path == dot_dir or path.startswith(f"{dot_dir}/")
        ]
        if not tracked:
            continue

        unexpected = [path for path in tracked if not match_any(path, allow_globs)]
        for path in unexpected:
            warnings.append(f"[dot-scope] {path} is not allowlisted for {dot_dir}")

    return warnings


def policy_warnings(
    entries: list[RootEntry], policy: dict[str, Any], repo_root: Path
) -> list[str]:
    root_policy = policy.get("root_policy", {})
    warnings: list[str] = []

    for entry in entries:
        if entry.git_state != "tracked":
            continue
        if entry.action == "move_to_scripts_devtools":
            warnings.append(f"[move] {entry.name} should move to scripts/devtools/")
            continue
        if entry.action == "review_for_relocation":
            warnings.append(
                f"[root-allowlist] {entry.name} is tracked in root but not allowlisted"
            )
            continue
        if not allowed_root_entry(entry.name, entry.entry_type, root_policy):
            warnings.append(
                f"[root-policy] {entry.name} needs explicit policy decision"
            )

    for entry in entries:
        if entry.git_state != "local-only":
            continue
        if entry.action == "ignore_or_remove_local":
            continue
        warnings.append(f"[local-only] {entry.name} is untracked at repository root")

    warnings.extend(dot_scope_warnings(repo_root, policy))
    return warnings


def counts_by(entries: list[RootEntry], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        bucket = getattr(entry, key)
        counts[bucket] = counts.get(bucket, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def report_markdown(
    *,
    repo_root: Path,
    entries: list[RootEntry],
    warnings: list[str],
    policy: dict[str, Any],
) -> str:
    created_at = datetime.now(timezone.utc).isoformat()
    type_counts = counts_by(entries, "entry_type")
    state_counts = counts_by(entries, "git_state")
    action_counts = counts_by(entries, "action")
    policy_name = policy.get("policy_name", "unknown")

    lines: list[str] = []
    lines.append("# Repo Audit Report")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{created_at}`")
    lines.append(f"- Repository root: `{repo_root}`")
    lines.append(f"- Policy: `{policy_name}`")
    lines.append(f"- Top-level entries: `{len(entries)}`")
    lines.append("")
    lines.append("## Counts by Type")
    lines.append("")
    lines.append("| Type | Count |")
    lines.append("|---|---:|")
    for key, value in type_counts.items():
        lines.append(f"| {key} | {value} |")
    lines.append("")
    lines.append("## Counts by Git State")
    lines.append("")
    lines.append("| Git State | Count |")
    lines.append("|---|---:|")
    for key, value in state_counts.items():
        lines.append(f"| {key} | {value} |")
    lines.append("")
    lines.append("## Counts by Suggested Action")
    lines.append("")
    lines.append("| Action | Count |")
    lines.append("|---|---:|")
    for key, value in action_counts.items():
        lines.append(f"| {key} | {value} |")
    lines.append("")
    lines.append("## Policy Warnings (Soft Gate)")
    lines.append("")
    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- No warnings.")
    lines.append("")
    lines.append("## Root Entry Inventory")
    lines.append("")
    lines.append("| Entry | Type | Git State | Suggested Action | Rationale |")
    lines.append("|---|---|---|---|---|")
    for entry in entries:
        lines.append(
            f"| `{entry.name}` | {entry.entry_type} | {entry.git_state} | {entry.action} | {entry.rationale} |"
        )

    return "\n".join(lines) + "\n"


def report_json(
    *,
    repo_root: Path,
    entries: list[RootEntry],
    warnings: list[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "policy_name": policy.get("policy_name", "unknown"),
        "top_level_entry_count": len(entries),
        "counts": {
            "entry_type": counts_by(entries, "entry_type"),
            "git_state": counts_by(entries, "git_state"),
            "action": counts_by(entries, "action"),
        },
        "warnings": warnings,
        "entries": [
            {
                "name": entry.name,
                "entry_type": entry.entry_type,
                "git_state": entry.git_state,
                "action": entry.action,
                "rationale": entry.rationale,
            }
            for entry in entries
        ],
    }


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, content: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_warning_summary(path: Path, warnings: list[str]) -> None:
    lines = ["## Repo Hygiene Soft Gate"]
    lines.append("")
    if not warnings:
        lines.append("- No policy warnings.")
    else:
        lines.append(f"- Warning count: `{len(warnings)}`")
        lines.append("")
        for warning in warnings:
            lines.append(f"- {warning}")
    lines.append("")
    write_text(path, "\n".join(lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default="artifacts/repo-audit",
        help="Directory where reports are written",
    )
    parser.add_argument(
        "--policy",
        default="scripts/repo_hygiene_policy.json",
        help="Path to hygiene policy JSON",
    )
    parser.add_argument(
        "--check-policy",
        action="store_true",
        help="Evaluate policy and emit warnings",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when warnings are found",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    start_dir = Path.cwd().resolve()
    try:
        repo_root = git_root(start_dir)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    policy_path = (repo_root / args.policy).resolve()
    if not policy_path.exists():
        print(f"error: policy file not found: {policy_path}", file=sys.stderr)
        return 2

    try:
        policy = load_policy(policy_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: failed to load policy: {exc}", file=sys.stderr)
        return 2

    entries = collect_root_entries(repo_root, policy)
    warnings = policy_warnings(entries, policy, repo_root) if args.check_policy else []
    output_dir = (repo_root / args.output_dir).resolve()

    markdown_path = output_dir / "repo_audit_report.md"
    json_path = output_dir / "repo_audit_report.json"
    warnings_path = output_dir / "policy_warnings.md"

    write_text(
        markdown_path,
        report_markdown(
            repo_root=repo_root, entries=entries, warnings=warnings, policy=policy
        ),
    )
    write_json(
        json_path,
        report_json(
            repo_root=repo_root, entries=entries, warnings=warnings, policy=policy
        ),
    )
    write_warning_summary(warnings_path, warnings)

    print(f"repo_audit: wrote {markdown_path}")
    print(f"repo_audit: wrote {json_path}")
    print(f"repo_audit: wrote {warnings_path}")
    print(f"repo_audit: top-level entries={len(entries)} warnings={len(warnings)}")

    if args.strict and warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
