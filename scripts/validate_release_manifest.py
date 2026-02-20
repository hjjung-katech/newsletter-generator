#!/usr/bin/env python3
"""Validate staged file set against a release manifest."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if p.returncode != 0:
        raise SystemExit((p.stdout + p.stderr).strip())
    return p.stdout.strip()


def read_manifest(path: Path) -> set[str]:
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return set(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument(
        "--source",
        default="staged",
        choices=["staged", "head", "baseline"],
        help="Check staged files, working tree against HEAD, or baseline...HEAD.",
    )
    args = parser.parse_args()

    manifest = Path(args.manifest)
    if not manifest.exists():
        raise SystemExit(f"missing manifest file: {manifest}")

    allowed = read_manifest(manifest)
    if args.source == "staged":
        diff_args = ["--cached"]
    elif args.source == "head":
        diff_args = ["HEAD"]
    else:
        baseline_ref = os.getenv("CI_BASELINE_REF", "baseline/main-equivalent")
        diff_args = [f"{baseline_ref}...HEAD"]

    changed = run(["git", "diff", "--name-only", *diff_args])
    changed_files = {x for x in changed.splitlines() if x.strip()}

    extra = sorted(changed_files - allowed)

    print("=== RELEASE MANIFEST VALIDATION ===")
    print(f"manifest: {manifest}")
    print(f"source: {args.source}")
    print(f"changed files: {len(changed_files)}")

    if extra:
        print("\n[OUT OF SCOPE FILES]")
        for p in extra:
            print(f"- {p}")
        print("\nRESULT: FAILED (manifest)")
        return 1

    print("\nRESULT: PASSED (manifest)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
