#!/usr/bin/env python3
"""Verify SHA256 checksum for Windows EXE artifacts."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_checksums(checksum_file: Path) -> dict[str, str]:
    if not checksum_file.exists():
        raise SystemExit(f"missing checksum file: {checksum_file}")

    checksums: dict[str, str] = {}
    for raw_line in checksum_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        hash_value, file_token = parts[0], parts[1].lstrip("*")
        checksums[file_token] = hash_value
    return checksums


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--artifact",
        dest="artifacts",
        action="append",
        help="Artifact path to verify. Repeat this flag to verify multiple files.",
    )
    parser.add_argument("--checksum-file", default="dist/SHA256SUMS.txt")
    args = parser.parse_args()

    artifact_args = args.artifacts or ["dist/newsletter_web.exe"]
    artifact_paths = [Path(item) for item in artifact_args]
    checksums = _load_checksums(Path(args.checksum_file))

    for artifact_path in artifact_paths:
        if not artifact_path.exists():
            raise SystemExit(f"missing artifact: {artifact_path}")

        expected = checksums.get(artifact_path.name)
        if expected is None:
            raise SystemExit(
                f"artifact {artifact_path.name} not found in {args.checksum_file}"
            )

        actual = _sha256(artifact_path)
        if actual != expected:
            raise SystemExit(
                "checksum mismatch: "
                f"expected={expected} actual={actual} artifact={artifact_path.name}"
            )

        print(f"checksum verified: {artifact_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
