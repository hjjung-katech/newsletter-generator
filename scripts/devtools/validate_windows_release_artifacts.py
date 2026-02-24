#!/usr/bin/env python3
"""Validate required Windows release artifacts for distribution."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REQUIRED_METADATA_KEYS = {
    "version",
    "build_time_utc",
    "git_sha",
    "python_version",
    "target_os",
    "artifact_name",
    "artifact_sha256",
    "smoke_result",
    "signing_status",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_metadata(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"missing metadata: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_checksum(path: Path, artifact_name: str) -> str:
    if not path.exists():
        raise SystemExit(f"missing checksum file: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split()
        if len(parts) < 2:
            continue
        digest, name = parts[0], parts[1].lstrip("*")
        if name == artifact_name:
            return digest
    raise SystemExit(f"{artifact_name} not found in {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", default="dist")
    parser.add_argument("--require-signing", action="store_true")
    args = parser.parse_args()

    dist_dir = Path(args.dist_dir)
    artifact_path = dist_dir / "newsletter_web.exe"
    metadata_path = dist_dir / "release-metadata.json"
    checksum_path = dist_dir / "SHA256SUMS.txt"
    bundle_path = dist_dir / "support-bundle.zip"

    for path in (artifact_path, metadata_path, checksum_path, bundle_path):
        if not path.exists():
            raise SystemExit(f"missing required artifact: {path}")

    metadata = _load_metadata(metadata_path)
    missing_keys = sorted(REQUIRED_METADATA_KEYS - set(metadata.keys()))
    if missing_keys:
        raise SystemExit(f"metadata missing keys: {', '.join(missing_keys)}")

    if metadata["artifact_name"] != artifact_path.name:
        raise SystemExit(
            f"artifact_name mismatch: metadata={metadata['artifact_name']} expected={artifact_path.name}"
        )

    digest_file = _sha256(artifact_path)
    digest_meta = str(metadata["artifact_sha256"])
    digest_checksum = _load_checksum(checksum_path, artifact_path.name)

    if digest_file != digest_meta:
        raise SystemExit(
            "artifact sha256 mismatch between file and release-metadata.json"
        )

    if digest_file != digest_checksum:
        raise SystemExit("artifact sha256 mismatch between file and SHA256SUMS.txt")

    signing_status = str(metadata["signing_status"]).lower()
    if args.require_signing and signing_status != "signed":
        raise SystemExit("signing is required but signing_status is not 'signed'")

    print("release artifacts validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
