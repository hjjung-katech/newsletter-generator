from __future__ import annotations

import json

import pytest

from scripts.devtools import web_health_smoke


def test_validate_health_payload_accepts_expected_contract() -> None:
    payload = {
        "status": "healthy",
        "dependencies": {
            "config": {"status": "healthy"},
            "database": {"status": "healthy"},
            "filesystem": {"status": "healthy"},
            "newsletter_cli": {"status": "healthy"},
        },
    }

    assert web_health_smoke.validate_health_payload(payload) == payload


@pytest.mark.parametrize(
    ("payload", "expected_message"),
    [
        ({}, "unexpected health status"),
        (
            {"status": "healthy", "dependencies": {"database": {"status": "healthy"}}},
            "missing dependency keys",
        ),
        ("not-a-dict", "JSON object"),
    ],
)
def test_validate_health_payload_rejects_invalid_payloads(
    payload: object,
    expected_message: str,
) -> None:
    with pytest.raises(SystemExit, match=expected_message):
        web_health_smoke.validate_health_payload(payload)


def test_run_http_smoke_accepts_valid_health_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "status": "degraded",
        "dependencies": {
            "config": {"status": "warning"},
            "database": {"status": "healthy"},
            "filesystem": {"status": "healthy"},
            "newsletter_cli": {"status": "healthy"},
        },
    }

    monkeypatch.setattr(
        web_health_smoke,
        "_request_health",
        lambda _base_url: (200, json.dumps(payload).encode("utf-8")),
    )

    web_health_smoke.run_http_smoke(
        base_url="http://127.0.0.1:58080",
        timeout_seconds=0.01,
        interval_seconds=0.0,
    )
