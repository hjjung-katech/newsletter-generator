#!/usr/bin/env python3
"""Generate release metadata and checksum files for Windows EXE artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def _run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _resolve_version(explicit_version: str | None, git_sha: str) -> str:
    if explicit_version:
        return explicit_version

    env_version = os.getenv("RELEASE_VERSION", "").strip()
    if env_version:
        return env_version

    ref_name = os.getenv("GITHUB_REF_NAME", "").strip()
    if ref_name.startswith("v"):
        return ref_name

    latest_tag = _run_git(["describe", "--tags", "--abbrev=0"])
    if latest_tag:
        return latest_tag

    short_sha = git_sha[:7] if git_sha else "unknown"
    return f"0.0.0+{short_sha}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_checksum_file(path: Path, entries: list[tuple[str, str]]) -> None:
    lines = [f"{digest} *{name}" for name, digest in entries]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", default="dist/newsletter_web.exe")
    parser.add_argument("--output-dir", default="dist")
    parser.add_argument("--smoke-result", default="not-run")
    parser.add_argument("--signing-status", default="unsigned")
    parser.add_argument("--target-os", default="windows-x64")
    parser.add_argument("--version", default=None)
    args = parser.parse_args()

    artifact_path = Path(args.artifact)
    if not artifact_path.exists():
        raise SystemExit(f"missing artifact: {artifact_path}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    git_sha = _run_git(["rev-parse", "HEAD"])
    artifact_hash = _sha256(artifact_path)
    version = _resolve_version(args.version, git_sha)

    metadata = {
        "version": version,
        "build_time_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha,
        "python_version": platform.python_version(),
        "target_os": args.target_os,
        "artifact_name": artifact_path.name,
        "artifact_sha256": artifact_hash,
        "smoke_result": args.smoke_result,
        "signing_status": args.signing_status,
    }

    metadata_path = output_dir / "release-metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    metadata_hash = _sha256(metadata_path)

    checksum_path = output_dir / "SHA256SUMS.txt"
    _write_checksum_file(
        checksum_path,
        [
            (artifact_path.name, artifact_hash),
            (metadata_path.name, metadata_hash),
        ],
    )

    print(f"metadata: {metadata_path}")
    print(f"checksums: {checksum_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
