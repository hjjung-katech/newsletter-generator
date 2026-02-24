#!/usr/bin/env python3
"""Generate update-manifest.json for semi-automatic Windows updates."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", default="dist/release-metadata.json")
    parser.add_argument("--output", default="dist/update-manifest.json")
    parser.add_argument("--base-url", default="")
    args = parser.parse_args()

    metadata_path = Path(args.metadata)
    if not metadata_path.exists():
        raise SystemExit(f"missing metadata: {metadata_path}")

    base_url = args.base_url.strip().rstrip("/")
    if not base_url:
        raise SystemExit("base-url is required for update-manifest generation")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    artifact_name = str(metadata["artifact_name"])
    artifact_sha = str(metadata["artifact_sha256"])

    manifest = {
        "version": str(metadata["version"]),
        "published_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact": {
            "name": artifact_name,
            "sha256": artifact_sha,
            "download_url": f"{base_url}/{artifact_name}",
        },
        "metadata_url": f"{base_url}/release-metadata.json",
        "checksum_url": f"{base_url}/SHA256SUMS.txt",
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    print(f"update manifest: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
