#!/usr/bin/env python3
"""Validate release manifest inventory and staged scope truth."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

MANIFESTS_DIR = Path(".release/manifests")


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise SystemExit((result.stdout + result.stderr).strip())
    return result.stdout.strip()


def read_manifest(path: Path) -> list[str]:
    entries: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        candidate = raw.strip()
        if not candidate or candidate.startswith("#"):
            continue
        entries.append(candidate)
    return entries


def discover_manifests(root: Path | None = None) -> list[Path]:
    manifest_root = (root or Path.cwd()) / MANIFESTS_DIR
    return sorted(manifest_root.glob("*.txt"))


def find_duplicate_entries(entries: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for entry in entries:
        if entry in seen and entry not in duplicates:
            duplicates.append(entry)
        seen.add(entry)
    return duplicates


def find_missing_manifest_paths(
    entries: list[str], repo_root: Path | None = None
) -> list[str]:
    root = repo_root or Path.cwd()
    missing: list[str] = []
    for entry in entries:
        if not (root / entry).exists():
            missing.append(entry)
    return missing


def find_out_of_scope_files(
    changed_files: set[str], allowed_entries: set[str]
) -> list[str]:
    return sorted(changed_files - allowed_entries)


def changed_files_for_source(source: str) -> set[str]:
    if source == "staged":
        diff_args = ["--cached"]
    elif source == "head":
        diff_args = ["HEAD"]
    else:
        baseline_ref = os.getenv("CI_BASELINE_REF", "baseline/main-equivalent")
        diff_args = [f"{baseline_ref}...HEAD"]

    changed = run(["git", "diff", "--name-only", *diff_args])
    return {path for path in changed.splitlines() if path.strip()}


def validate_manifest_inventory(
    manifest: Path, repo_root: Path | None = None
) -> tuple[list[str], list[str]]:
    entries = read_manifest(manifest)
    duplicates = find_duplicate_entries(entries)
    missing = find_missing_manifest_paths(entries, repo_root=repo_root)
    return duplicates, missing


def _print_manifest_failure_block(
    manifest: Path, duplicates: list[str], missing: list[str], extra: list[str]
) -> None:
    print(f"\nmanifest: {manifest}")
    if duplicates:
        print("[DUPLICATE MANIFEST ENTRIES]")
        for entry in duplicates:
            print(f"- {entry}")
    if missing:
        print("[STALE MANIFEST ENTRIES]")
        for entry in missing:
            print(f"- {entry}")
    if extra:
        print("[OUT OF SCOPE FILES]")
        for entry in extra:
            print(f"- {entry}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default="",
        help="Validate a single manifest. If omitted, validate all manifests for stale/duplicate entries.",
    )
    parser.add_argument(
        "--source",
        default="staged",
        choices=["staged", "head", "baseline"],
        help="Check staged files, working tree against HEAD, or baseline...HEAD.",
    )
    args = parser.parse_args()

    repo_root = Path.cwd()

    if args.manifest:
        manifests = [Path(args.manifest)]
    else:
        manifests = discover_manifests(repo_root)

    if not manifests:
        raise SystemExit("no release manifests found")

    print("=== RELEASE MANIFEST VALIDATION ===")

    if not args.manifest:
        print("mode: inventory")
        failures = 0
        for manifest in manifests:
            duplicates, missing = validate_manifest_inventory(manifest, repo_root)
            print(f"manifest: {manifest} (entries={len(read_manifest(manifest))})")
            if duplicates or missing:
                failures += 1
                if duplicates:
                    print("  duplicate entries:")
                    for entry in duplicates:
                        print(f"  - {entry}")
                if missing:
                    print("  stale entries:")
                    for entry in missing:
                        print(f"  - {entry}")
            else:
                print("  inventory: ok")

        if failures:
            print("\nRESULT: FAILED (manifest inventory)")
            return 1

        print("\nRESULT: PASSED (manifest inventory)")
        return 0

    manifest = manifests[0]
    if not manifest.exists():
        raise SystemExit(f"missing manifest file: {manifest}")

    entries = read_manifest(manifest)
    duplicates, missing = validate_manifest_inventory(manifest, repo_root)
    changed = changed_files_for_source(args.source)
    extra = find_out_of_scope_files(changed, set(entries))

    print(f"manifest: {manifest}")
    print(f"source: {args.source}")
    print(f"changed files: {len(changed)}")

    if duplicates or missing or extra:
        _print_manifest_failure_block(manifest, duplicates, missing, extra)
        print("\nRESULT: FAILED (manifest)")
        return 1

    print("\nRESULT: PASSED (manifest)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
