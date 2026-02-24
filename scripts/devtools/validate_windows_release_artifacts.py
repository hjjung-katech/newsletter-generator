#!/usr/bin/env python3
"""Validate required Windows release artifacts for distribution."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile

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
BUNDLE_REQUIRED_ENTRIES = {
    "system-info.json",
    "bundle-manifest.json",
    "recent-errors.txt",
    "release-metadata.json",
    "SHA256SUMS.txt",
}
ENV_UNREDACTED_RE = re.compile(
    r"(?i)^[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|AUTH)[A-Z0-9_]*\s*=\s*(?!<redacted>$).+"
)


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


def _load_checksums(path: Path) -> dict[str, str]:
    if not path.exists():
        raise SystemExit(f"missing checksum file: {path}")

    checksums: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split()
        if len(parts) < 2:
            continue
        digest, name = parts[0], parts[1].lstrip("*")
        checksums[name] = digest
    return checksums


def _validate_bundle(bundle_path: Path) -> None:
    with ZipFile(bundle_path, "r") as zip_file:
        names = set(zip_file.namelist())
        missing = sorted(BUNDLE_REQUIRED_ENTRIES - names)
        if missing:
            raise SystemExit(
                "support bundle missing required entries: " + ", ".join(missing)
            )

        manifest_raw = zip_file.read("bundle-manifest.json").decode(
            "utf-8", errors="replace"
        )
        try:
            json.loads(manifest_raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid bundle-manifest.json: {exc}") from exc

        recent_errors = zip_file.read("recent-errors.txt").decode(
            "utf-8", errors="replace"
        )
        if not recent_errors.strip():
            raise SystemExit("recent-errors.txt is empty")

        if ".env" in names:
            env_text = zip_file.read(".env").decode("utf-8", errors="replace")
            for line in env_text.splitlines():
                if ENV_UNREDACTED_RE.match(line.strip()):
                    raise SystemExit(
                        "support bundle .env contains unredacted sensitive value"
                    )


def _validate_update_manifest(
    update_manifest_path: Path,
    metadata: dict,
    checksums: dict[str, str],
    checksum_path: Path,
    require_update_manifest: bool,
) -> None:
    if not update_manifest_path.exists():
        if require_update_manifest:
            raise SystemExit(
                f"update manifest is required but missing: {update_manifest_path}"
            )
        return

    try:
        manifest = json.loads(update_manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid update-manifest.json: {exc}") from exc

    artifact = manifest.get("artifact")
    if not isinstance(artifact, dict):
        raise SystemExit("update-manifest.json missing artifact object")

    if str(manifest.get("version", "")) != str(metadata["version"]):
        raise SystemExit("update-manifest version mismatch against release metadata")

    if str(artifact.get("name", "")) != str(metadata["artifact_name"]):
        raise SystemExit("update-manifest artifact.name mismatch")

    if str(artifact.get("sha256", "")) != str(metadata["artifact_sha256"]):
        raise SystemExit("update-manifest artifact.sha256 mismatch")

    if not str(artifact.get("download_url", "")).strip():
        raise SystemExit("update-manifest artifact.download_url is empty")
    if not str(manifest.get("metadata_url", "")).strip():
        raise SystemExit("update-manifest metadata_url is empty")
    if not str(manifest.get("checksum_url", "")).strip():
        raise SystemExit("update-manifest checksum_url is empty")

    checksum = checksums.get(update_manifest_path.name)
    if checksum is None:
        raise SystemExit(f"{update_manifest_path.name} not found in {checksum_path}")
    if _sha256(update_manifest_path) != checksum:
        raise SystemExit("update-manifest sha256 mismatch against SHA256SUMS.txt")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", default="dist")
    parser.add_argument("--require-signing", action="store_true")
    parser.add_argument("--require-update-manifest", action="store_true")
    args = parser.parse_args()

    dist_dir = Path(args.dist_dir)
    artifact_path = dist_dir / "newsletter_web.exe"
    metadata_path = dist_dir / "release-metadata.json"
    checksum_path = dist_dir / "SHA256SUMS.txt"
    bundle_path = dist_dir / "support-bundle.zip"
    update_manifest_path = dist_dir / "update-manifest.json"

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

    checksums = _load_checksums(checksum_path)
    digest_file = _sha256(artifact_path)
    digest_meta = str(metadata["artifact_sha256"])
    digest_checksum = checksums.get(artifact_path.name)
    if digest_checksum is None:
        raise SystemExit(f"{artifact_path.name} not found in {checksum_path}")

    if digest_file != digest_meta:
        raise SystemExit(
            "artifact sha256 mismatch between file and release-metadata.json"
        )

    if digest_file != digest_checksum:
        raise SystemExit("artifact sha256 mismatch between file and SHA256SUMS.txt")

    metadata_checksum = checksums.get(metadata_path.name)
    if metadata_checksum is None:
        raise SystemExit(f"{metadata_path.name} not found in {checksum_path}")
    if _sha256(metadata_path) != metadata_checksum:
        raise SystemExit("release-metadata.json sha256 mismatch against SHA256SUMS.txt")

    bundle_checksum = checksums.get(bundle_path.name)
    if bundle_checksum is None:
        raise SystemExit(f"{bundle_path.name} not found in {checksum_path}")
    if _sha256(bundle_path) != bundle_checksum:
        raise SystemExit("support-bundle.zip sha256 mismatch against SHA256SUMS.txt")

    _validate_bundle(bundle_path)
    _validate_update_manifest(
        update_manifest_path,
        metadata,
        checksums,
        checksum_path,
        args.require_update_manifest,
    )

    signing_status = str(metadata["signing_status"]).lower()
    if args.require_signing and signing_status != "signed":
        raise SystemExit("signing is required but signing_status is not 'signed'")

    print("release artifacts validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
