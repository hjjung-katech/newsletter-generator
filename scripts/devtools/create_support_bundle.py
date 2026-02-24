#!/usr/bin/env python3
"""Create a sanitized support bundle for Windows EXE troubleshooting."""

from __future__ import annotations

import argparse
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


def _collect_logs(log_dir: Path, bundle_dir: Path) -> None:
    if not log_dir.exists():
        return

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
    args = parser.parse_args()

    artifact_path = Path(args.artifact)
    dist_dir = Path(args.dist_dir)
    output_path = Path(args.output)

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

        _collect_logs(dist_dir / "logs", bundle_dir)
        _create_zip(bundle_dir, output_path)

    print(f"support bundle: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
