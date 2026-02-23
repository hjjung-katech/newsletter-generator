#!/usr/bin/env python3
"""Operational safety smoke test for idempotency/outbox contracts.

Checks:
1) `POST /api/generate` duplicate request behavior (`202`, same `job_id`, `deduplicated=true`).
2) optional `POST /api/send-email` outbox dedupe behavior.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin


class SmokeError(RuntimeError):
    """Raised when smoke validation fails."""


@dataclass
class HttpResult:
    status_code: int
    body: dict[str, Any]


def _post_json(
    base_url: str, path: str, payload: dict[str, Any], headers: dict[str, str]
) -> HttpResult:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        urljoin(base_url.rstrip("/") + "/", path.lstrip("/")),
        data=data,
        method="POST",
    )
    request.add_header("Content-Type", "application/json")
    for key, value in headers.items():
        request.add_header(key, value)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            body = json.loads(raw) if raw else {}
            return HttpResult(status_code=response.status, body=body)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {"raw": raw}
        return HttpResult(status_code=exc.code, body=body)


def _get_json(base_url: str, path: str) -> HttpResult:
    request = urllib.request.Request(
        urljoin(base_url.rstrip("/") + "/", path.lstrip("/")),
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            body = json.loads(raw) if raw else {}
            return HttpResult(status_code=response.status, body=body)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {"raw": raw}
        return HttpResult(status_code=exc.code, body=body)


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


def _poll_until_done(
    base_url: str, job_id: str, timeout_sec: int, interval_sec: float
) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    last_body: dict[str, Any] = {}

    while time.time() < deadline:
        result = _get_json(base_url, f"/api/status/{job_id}")
        _expect(
            result.status_code == 200,
            f"status endpoint failed: {result.status_code}, body={result.body}",
        )
        last_body = result.body
        status = str(last_body.get("status", "")).lower()
        if status in {"completed", "finished", "failed"}:
            return last_body
        time.sleep(interval_sec)

    raise SmokeError(f"job did not finish in {timeout_sec}s; last status={last_body}")


def run_smoke(
    base_url: str,
    keywords: str,
    period: int,
    timeout_sec: int,
    poll_interval_sec: float,
    idempotency_key: str | None,
    email: str | None,
    check_email_dedupe: bool,
) -> None:
    idem_key = idempotency_key or f"ops-smoke-{uuid.uuid4().hex}"
    payload = {
        "keywords": keywords,
        "template_style": "compact",
        "period": period,
    }

    first = _post_json(
        base_url=base_url,
        path="/api/generate",
        payload=payload,
        headers={"Idempotency-Key": idem_key},
    )
    _expect(
        first.status_code == 202,
        f"first generate failed: {first.status_code}, body={first.body}",
    )
    job_id = first.body.get("job_id")
    _expect(
        isinstance(job_id, str) and job_id,
        f"first response missing job_id: {first.body}",
    )
    _expect(
        first.body.get("idempotency_key") == idem_key,
        f"first response idempotency_key mismatch: expected={idem_key}, body={first.body}",
    )

    second = _post_json(
        base_url=base_url,
        path="/api/generate",
        payload=payload,
        headers={"Idempotency-Key": idem_key},
    )
    _expect(
        second.status_code == 202,
        f"second generate failed: {second.status_code}, body={second.body}",
    )
    _expect(
        second.body.get("job_id") == job_id, f"dedupe job_id mismatch: {second.body}"
    )
    _expect(
        second.body.get("deduplicated") is True,
        f"expected deduplicated=true: {second.body}",
    )
    _expect(
        second.body.get("idempotency_key") == idem_key,
        f"second response idempotency_key mismatch: expected={idem_key}, body={second.body}",
    )

    final_status = _poll_until_done(
        base_url, job_id=job_id, timeout_sec=timeout_sec, interval_sec=poll_interval_sec
    )
    _expect(
        str(final_status.get("status", "")).lower() in {"completed", "finished"},
        f"job ended as failed: {final_status}",
    )

    if check_email_dedupe:
        _expect(
            email is not None and email.strip(), "--check-email-dedupe requires --email"
        )
        send_payload = {"job_id": job_id, "email": email}

        send_first = _post_json(
            base_url=base_url,
            path="/api/send-email",
            payload=send_payload,
            headers={},
        )
        _expect(
            send_first.status_code == 200,
            f"first send-email failed: {send_first.status_code}, body={send_first.body}",
        )
        _expect(
            send_first.body.get("status") == "success",
            f"first send-email not success: {send_first.body}",
        )

        send_second = _post_json(
            base_url=base_url,
            path="/api/send-email",
            payload=send_payload,
            headers={},
        )
        _expect(
            send_second.status_code == 200,
            f"second send-email failed: {send_second.status_code}, body={send_second.body}",
        )
        _expect(
            send_second.body.get("deduplicated") is True,
            f"expected send-email deduplicated=true on second call: {send_second.body}",
        )

    print("ops-safety-smoke: PASS")
    print(
        json.dumps(
            {
                "base_url": base_url,
                "job_id": job_id,
                "idempotency_key": idem_key,
                "email_dedupe_checked": check_email_dedupe,
            },
            ensure_ascii=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ops safety smoke checks against deployed web API."
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="API base URL (e.g. https://your-app.railway.app)",
    )
    parser.add_argument(
        "--keywords",
        default="AI,ops-safety-smoke",
        help="keywords payload for generation request",
    )
    parser.add_argument(
        "--period",
        type=int,
        default=7,
        choices=[1, 7, 14, 30],
        help="period for generation request",
    )
    parser.add_argument(
        "--timeout-sec", type=int, default=120, help="status polling timeout"
    )
    parser.add_argument(
        "--poll-interval-sec", type=float, default=2.0, help="status polling interval"
    )
    parser.add_argument(
        "--idempotency-key", default=None, help="optional fixed idempotency key"
    )
    parser.add_argument(
        "--email", default=None, help="recipient email used by send-email dedupe check"
    )
    parser.add_argument(
        "--check-email-dedupe",
        action="store_true",
        help="validate /api/send-email outbox dedupe behavior (requires --email)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        run_smoke(
            base_url=args.base_url,
            keywords=args.keywords,
            period=args.period,
            timeout_sec=args.timeout_sec,
            poll_interval_sec=args.poll_interval_sec,
            idempotency_key=args.idempotency_key,
            email=args.email,
            check_email_dedupe=args.check_email_dedupe,
        )
    except SmokeError as exc:
        print(f"ops-safety-smoke: FAIL - {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover
        print(f"ops-safety-smoke: FAIL - unexpected error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
