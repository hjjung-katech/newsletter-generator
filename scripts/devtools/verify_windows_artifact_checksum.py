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


def _expected_hash(checksum_file: Path, artifact_name: str) -> str:
    if not checksum_file.exists():
        raise SystemExit(f"missing checksum file: {checksum_file}")

    for raw_line in checksum_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        hash_value, file_token = parts[0], parts[1].lstrip("*")
        if file_token == artifact_name:
            return hash_value
    raise SystemExit(f"artifact {artifact_name} not found in {checksum_file}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", default="dist/newsletter_web.exe")
    parser.add_argument("--checksum-file", default="dist/SHA256SUMS.txt")
    args = parser.parse_args()

    artifact_path = Path(args.artifact)
    if not artifact_path.exists():
        raise SystemExit(f"missing artifact: {artifact_path}")

    checksum_path = Path(args.checksum_file)
    expected = _expected_hash(checksum_path, artifact_path.name)
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
