#!/usr/bin/env python3
"""Create a sanitized support bundle for Windows EXE troubleshooting."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

SENSITIVE_ENV_KEYS = (
    "KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "API",
    "AUTH",
)

SENSITIVE_LINE_RE = re.compile(
    r"(?i)\b([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|AUTH)[A-Z0-9_]*)\s*=\s*(.+)$"
)
SENSITIVE_JSON_RE = re.compile(
    r'(?i)("?[A-Za-z0-9_\-]*(?:key|token|secret|password|auth)[A-Za-z0-9_\-]*"?\s*:\s*)(".*?"|\S+)'
)
ERROR_LINE_RE = re.compile(r"(?i)\b(error|exception|traceback|fatal|critical)\b")
MAX_ERROR_LINES = 200


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


def _is_sensitive_key(key: str) -> bool:
    upper = key.upper()
    return any(token in upper for token in SENSITIVE_ENV_KEYS)


def _redact_text(content: str) -> str:
    redacted_lines: list[str] = []
    for line in content.splitlines():
        match = SENSITIVE_LINE_RE.search(line)
        if match and _is_sensitive_key(match.group(1)):
            redacted_lines.append(f"{match.group(1)}=<redacted>")
            continue

        line = SENSITIVE_JSON_RE.sub(r'\1"<redacted>"', line)
        line = re.sub(r"(?i)bearer\s+[a-z0-9\-\._~\+/]+=*", "Bearer <redacted>", line)
        redacted_lines.append(line)
    return "\n".join(redacted_lines) + ("\n" if content.endswith("\n") else "")


def _copy_sanitized(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.name == ".env" or src.suffix.lower() in {".log", ".txt", ".json"}:
        text = src.read_text(encoding="utf-8", errors="replace")
        dst.write_text(_redact_text(text), encoding="utf-8")
        return
    shutil.copy2(src, dst)


def _collect_logs(log_dir: Path, bundle_dir: Path) -> int:
    if not log_dir.exists():
        return 0

    selected = sorted(
        (
            path
            for path in log_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in {".log", ".txt", ".json"}
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:20]

    for path in selected:
        rel = path.relative_to(log_dir)
        _copy_sanitized(path, bundle_dir / "logs" / rel)
    return len(selected)


def _write_recent_errors(bundle_dir: Path) -> None:
    hits: list[str] = []
    logs_dir = bundle_dir / "logs"
    if logs_dir.exists():
        for log_file in sorted(logs_dir.rglob("*")):
            if not log_file.is_file():
                continue
            if log_file.suffix.lower() not in {".log", ".txt", ".json"}:
                continue
            lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
            for line_num, line in enumerate(lines, start=1):
                if not ERROR_LINE_RE.search(line):
                    continue
                rel = log_file.relative_to(bundle_dir)
                hits.append(f"{rel}:{line_num}: {line.strip()}")
                if len(hits) >= MAX_ERROR_LINES:
                    break
            if len(hits) >= MAX_ERROR_LINES:
                break

    if not hits:
        hits.append("No error/exception lines found in collected logs.")

    (bundle_dir / "recent-errors.txt").write_text(
        "\n".join(hits) + "\n", encoding="utf-8"
    )


def _write_bundle_manifest(
    bundle_dir: Path, artifact: Path, logs_collected: int
) -> None:
    manifest_path = bundle_dir / "bundle-manifest.json"
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_name": artifact.name,
        "artifact_exists": artifact.exists(),
        "logs_collected": logs_collected,
        "max_recent_error_lines": MAX_ERROR_LINES,
        "redaction_rules": [
            "*KEY*=<redacted>",
            "*TOKEN*=<redacted>",
            "*SECRET*=<redacted>",
            "*PASSWORD*=<redacted>",
            "Bearer <redacted>",
        ],
        "included_files": [],
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )

    manifest["included_files"] = sorted(
        str(path.relative_to(bundle_dir))
        for path in bundle_dir.rglob("*")
        if path.is_file()
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_checksums(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    checksums: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        checksums[parts[1].lstrip("*")] = parts[0]
    return checksums


def _write_checksums(path: Path, checksums: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{digest} *{name}" for name, digest in sorted(checksums.items())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _upsert_checksums(checksum_file: Path, files: list[Path]) -> None:
    checksums = _load_checksums(checksum_file)
    for file_path in files:
        if file_path.exists() and file_path.is_file():
            checksums[file_path.name] = _sha256(file_path)
    if checksums:
        _write_checksums(checksum_file, checksums)


def _write_system_info(bundle_dir: Path, artifact: Path) -> None:
    info = {
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "artifact_path": str(artifact),
        "artifact_exists": artifact.exists(),
        "git_sha": _run_git(["rev-parse", "HEAD"]),
    }
    path = bundle_dir / "system-info.json"
    path.write_text(
        json.dumps(info, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )


def _create_zip(bundle_dir: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as zip_file:
        for file_path in bundle_dir.rglob("*"):
            if file_path.is_file():
                zip_file.write(
                    file_path, arcname=str(file_path.relative_to(bundle_dir))
                )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", default="dist/newsletter_web.exe")
    parser.add_argument("--dist-dir", default="dist")
    parser.add_argument("--output", default="dist/support-bundle.zip")
    parser.add_argument("--checksum-file", default="dist/SHA256SUMS.txt")
    args = parser.parse_args()

    artifact_path = Path(args.artifact)
    dist_dir = Path(args.dist_dir)
    output_path = Path(args.output)
    checksum_path = Path(args.checksum_file)

    with tempfile.TemporaryDirectory(prefix="support-bundle-") as temp_dir:
        bundle_dir = Path(temp_dir)
        _write_system_info(bundle_dir, artifact_path)

        for candidate in (
            dist_dir / "release-metadata.json",
            dist_dir / "SHA256SUMS.txt",
            dist_dir / ".env",
        ):
            if candidate.exists() and candidate.is_file():
                _copy_sanitized(candidate, bundle_dir / candidate.name)

        logs_collected = _collect_logs(dist_dir / "logs", bundle_dir)
        _write_recent_errors(bundle_dir)
        _write_bundle_manifest(bundle_dir, artifact_path, logs_collected)
        _create_zip(bundle_dir, output_path)

    _upsert_checksums(
        checksum_path,
        [
            artifact_path,
            dist_dir / "release-metadata.json",
            output_path,
        ],
    )

    print(f"support bundle: {output_path}")
    print(f"checksums updated: {checksum_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
