#!/usr/bin/env python3
"""Fail when new Python modules are added under the legacy newsletter package."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class SurfaceDiff:
    unexpected: tuple[str, ...]
    removed: tuple[str, ...]


def discover_python_paths(package_root: Path) -> list[str]:
    return sorted(
        file_path.relative_to(package_root).as_posix()
        for file_path in package_root.rglob("*.py")
        if "__pycache__" not in file_path.parts
    )


def load_allowed_paths(manifest_path: Path) -> set[str]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    allowed_paths = data.get("allowed_paths", [])
    if not isinstance(allowed_paths, list):
        raise SystemExit(f"Invalid manifest format: {manifest_path}")
    return {str(path) for path in allowed_paths}


def diff_surface(actual_paths: list[str], allowed_paths: set[str]) -> SurfaceDiff:
    actual = set(actual_paths)
    unexpected = tuple(sorted(actual - allowed_paths))
    removed = tuple(sorted(allowed_paths - actual))
    return SurfaceDiff(unexpected=unexpected, removed=removed)


def write_manifest(manifest_path: Path, actual_paths: list[str]) -> None:
    payload = {
        "version": 1,
        "captured_at": date.today().isoformat(),
        "allowed_paths": actual_paths,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--package-root",
        default="newsletter",
        help="Relative package root to scan (default: newsletter).",
    )
    parser.add_argument(
        "--manifest",
        default="scripts/architecture/newsletter_legacy_surface.json",
        help="Relative manifest path (default: scripts/architecture/newsletter_legacy_surface.json).",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Write the current legacy package surface to the manifest and exit 0.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    package_root = (repo_root / args.package_root).resolve()
    manifest_path = (repo_root / args.manifest).resolve()

    if not package_root.exists():
        raise SystemExit(f"Package root does not exist: {package_root}")

    actual_paths = discover_python_paths(package_root)

    if args.update_baseline:
        write_manifest(manifest_path, actual_paths)
        print(f"Updated legacy newsletter surface manifest: {manifest_path}")
        print(f"Captured paths: {len(actual_paths)}")
        return 0

    if not manifest_path.exists():
        raise SystemExit(f"Manifest file does not exist: {manifest_path}")

    allowed_paths = load_allowed_paths(manifest_path)
    diff = diff_surface(actual_paths, allowed_paths)

    if diff.unexpected:
        print("Unexpected Python modules were added under newsletter/:")
        for rel_path in diff.unexpected:
            print(f"- {rel_path}")
        print(
            "New runtime modules must land under newsletter_core/ or update the "
            "manifest as an explicit compatibility decision."
        )
        return 1

    if diff.removed:
        print("Legacy newsletter surface shrank; manifest can be updated later:")
        for rel_path in diff.removed:
            print(f"- {rel_path}")

    print("Legacy newsletter surface matches the approved manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
