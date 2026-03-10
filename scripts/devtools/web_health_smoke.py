#!/usr/bin/env python3
"""Python smoke harness for source and HTTP health checks."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

EXPECTED_HEALTH_STATUSES = {"healthy", "degraded"}
REQUIRED_DEPENDENCIES = {"config", "database", "filesystem", "newsletter_cli"}
DEFAULT_HTTP_TIMEOUT_SECONDS = 90.0
DEFAULT_HTTP_INTERVAL_SECONDS = 2.0
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

MOCK_ENV_DEFAULTS = {
    "MOCK_MODE": "true",
    "TESTING": "1",
    "OPENAI_API_KEY": "test-key",
    "SERPER_API_KEY": "test-key",
    "GEMINI_API_KEY": "test-key",
    "ANTHROPIC_API_KEY": "test-key",
    "POSTMARK_SERVER_TOKEN": "dummy-token",
    "EMAIL_SENDER": "test@example.com",
}


def apply_smoke_env(repo_root: Path = REPO_ROOT) -> None:
    debug_dir = repo_root / ".local" / "debug_files"
    debug_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("PYTHONPATH", str(repo_root))
    os.environ.setdefault("NEWSLETTER_DEBUG_DIR", str(debug_dir))
    for key, value in MOCK_ENV_DEFAULTS.items():
        os.environ.setdefault(key, value)


def validate_health_payload(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise SystemExit("health payload must be a JSON object")

    status = payload.get("status")
    if status not in EXPECTED_HEALTH_STATUSES:
        raise SystemExit(f"unexpected health status: {status!r}")

    dependencies = payload.get("dependencies")
    if not isinstance(dependencies, dict):
        raise SystemExit("health payload is missing dependency details")

    missing_dependencies = sorted(REQUIRED_DEPENDENCIES - set(dependencies))
    if missing_dependencies:
        raise SystemExit(
            "health payload is missing dependency keys: "
            + ", ".join(missing_dependencies)
        )

    return payload


def run_source_smoke() -> None:
    apply_smoke_env()

    from web.app import create_app

    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        response = client.get("/health")

    if response.status_code != 200:
        raise SystemExit(f"source health smoke failed with HTTP {response.status_code}")

    validate_health_payload(response.get_json())
    print("web-source-smoke: ok")


def _request_health(base_url: str) -> tuple[int, bytes]:
    url = f"{base_url.rstrip('/')}/health"
    request = Request(url, headers={"User-Agent": "newsletter-generator-ci-smoke"})
    with urlopen(request, timeout=10) as response:
        status = getattr(response, "status", response.getcode())
        body = response.read()
    return status, body


def run_http_smoke(
    *,
    base_url: str,
    timeout_seconds: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
    interval_seconds: float = DEFAULT_HTTP_INTERVAL_SECONDS,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = "container did not become healthy"

    while time.monotonic() < deadline:
        try:
            status_code, body = _request_health(base_url)
            if status_code != 200:
                last_error = f"received HTTP {status_code}"
            else:
                validate_health_payload(json.loads(body.decode("utf-8")))
                print(f"web-http-smoke: ok ({base_url.rstrip('/')}/health)")
                return
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = str(exc)
        time.sleep(interval_seconds)

    raise SystemExit(f"http health smoke failed: {last_error}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cross-platform smoke harness for source and HTTP web health checks."
    )
    parser.add_argument(
        "--mode",
        choices=("source", "http"),
        required=True,
        help="Run against the Flask source runtime or an already running HTTP endpoint.",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:58080",
        help="Base URL for --mode http.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_HTTP_TIMEOUT_SECONDS,
        help="Total wait time for --mode http before failing.",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=DEFAULT_HTTP_INTERVAL_SECONDS,
        help="Retry interval for --mode http.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.mode == "source":
        run_source_smoke()
        return 0

    run_http_smoke(
        base_url=args.base_url,
        timeout_seconds=args.timeout_seconds,
        interval_seconds=args.interval_seconds,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
