"""Unit tests for quota/abuse observability (RR-28).

Tests cover:
- _QuotaAbuseTracker bounded ring-buffer behaviour
- /newsletter GET rate limit enforcement
- Abuse events recorded when rate limit exceeded (/api/generate and /newsletter)
- /api/ops/quota-abuse ops endpoint
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from flask import Flask, jsonify

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from access_control import (  # noqa: E402
    AbuseEvent,
    _QuotaAbuseTracker,
    configure_access_control,
)
from routes_ops_quota_abuse import register_quota_abuse_routes  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PROD_ENV = {"APP_ENV": "production"}
_OPS_TOKEN = "test-ops-secret"
_OPS_ENV = {**_PROD_ENV, "ADMIN_API_TOKEN_OPS": _OPS_TOKEN}


def _build_app(
    *,
    generate_rate_limit: int = 5,
    newsletter_rate_limit: int = 3,
    environ: dict[str, str] | None = None,
) -> Flask:
    """Build a minimal Flask app with access control and quota-abuse routes."""
    app = Flask(__name__)
    app.config["TESTING"] = False
    configure_access_control(
        app,
        environ=environ or _OPS_ENV,
        generate_rate_limit=generate_rate_limit,
        newsletter_rate_limit=newsletter_rate_limit,
    )
    register_quota_abuse_routes(app, ":memory:")

    @app.route("/api/generate", methods=["POST"])  # type: ignore[misc]
    def generate():
        return jsonify({"ok": True})

    @app.route("/newsletter")  # type: ignore[misc]
    def newsletter():
        return jsonify({"ok": True})

    return app


# ---------------------------------------------------------------------------
# _QuotaAbuseTracker unit tests
# ---------------------------------------------------------------------------


def test_tracker_records_event() -> None:
    tracker = _QuotaAbuseTracker()
    event = AbuseEvent(
        timestamp="2026-01-01T00:00:00Z",
        client_id="1.2.3.4",
        path="/api/generate",
        retry_after_seconds=30,
    )
    tracker.record(event)
    assert tracker.total_recorded == 1
    events = tracker.recent()
    assert len(events) == 1
    assert events[0].client_id == "1.2.3.4"


def test_tracker_bounded_ring_buffer() -> None:
    tracker = _QuotaAbuseTracker(maxlen=3)
    for i in range(5):
        tracker.record(
            AbuseEvent(
                timestamp="t",
                client_id=str(i),
                path="/p",
                retry_after_seconds=1,
            )
        )
    # total_recorded counts all 5 even though deque only holds 3
    assert tracker.total_recorded == 5
    events = tracker.recent()
    assert len(events) == 3
    assert events[-1].client_id == "4"  # most recent is last


def test_tracker_recent_limit() -> None:
    tracker = _QuotaAbuseTracker()
    for i in range(10):
        tracker.record(
            AbuseEvent(
                timestamp="t", client_id=str(i), path="/p", retry_after_seconds=1
            )
        )
    assert len(tracker.recent(limit=3)) == 3


# ---------------------------------------------------------------------------
# /newsletter GET rate limit
# ---------------------------------------------------------------------------


def test_newsletter_allows_under_limit() -> None:
    app = _build_app(newsletter_rate_limit=3)
    with app.test_client() as client:
        for _ in range(3):
            resp = client.get("/newsletter")
            assert resp.status_code == 200


def test_newsletter_enforces_limit() -> None:
    app = _build_app(newsletter_rate_limit=2)
    with app.test_client() as client:
        client.get("/newsletter")
        client.get("/newsletter")
        resp = client.get("/newsletter")
    assert resp.status_code == 429
    body = resp.get_json()
    assert "retry_after_seconds" in body
    assert resp.headers.get("Retry-After") is not None


def test_newsletter_rate_limit_records_abuse_event() -> None:
    app = _build_app(newsletter_rate_limit=1)
    with app.test_client() as client:
        client.get("/newsletter")  # allowed
        client.get("/newsletter")  # denied → abuse recorded

    tracker = app.extensions["quota_abuse_tracker"]
    assert tracker.total_recorded == 1
    events = tracker.recent()
    assert events[0].path == "/newsletter"
    assert events[0].retry_after_seconds >= 1


# ---------------------------------------------------------------------------
# /api/generate abuse recording
# ---------------------------------------------------------------------------


def test_generate_rate_limit_records_abuse_event() -> None:
    app = _build_app(generate_rate_limit=1)
    with app.test_client() as client:
        client.post("/api/generate", json={})  # allowed
        client.post("/api/generate", json={})  # denied → abuse recorded

    tracker = app.extensions["quota_abuse_tracker"]
    assert tracker.total_recorded == 1
    events = tracker.recent()
    assert events[0].path == "/api/generate"


# ---------------------------------------------------------------------------
# /api/ops/quota-abuse endpoint
# ---------------------------------------------------------------------------


def test_ops_endpoint_returns_empty_when_no_violations() -> None:
    app = _build_app()
    with app.test_client() as client:
        resp = client.get(
            "/api/ops/quota-abuse",
            headers={"X-Admin-Token": _OPS_TOKEN},
        )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["events"] == []
    assert body["summary"]["tracker_enabled"] is True
    assert body["summary"]["total_recorded"] == 0


def test_ops_endpoint_returns_violations() -> None:
    app = _build_app(newsletter_rate_limit=1)
    with app.test_client() as client:
        client.get("/newsletter")  # ok
        client.get("/newsletter")  # denied → recorded
        resp = client.get(
            "/api/ops/quota-abuse",
            headers={"X-Admin-Token": _OPS_TOKEN},
        )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["summary"]["total_recorded"] == 1
    assert len(body["events"]) == 1
    event = body["events"][0]
    assert event["path"] == "/newsletter"
    assert event["retry_after_seconds"] >= 1
    assert "timestamp" in event
    assert "client_id" in event


def test_ops_endpoint_requires_ops_token() -> None:
    app = _build_app()
    with app.test_client() as client:
        resp = client.get("/api/ops/quota-abuse")
    assert resp.status_code == 401


def test_ops_endpoint_wrong_scope_token_rejected() -> None:
    environ = {**_PROD_ENV, "ADMIN_API_TOKEN_DATA": "data-token"}
    app = _build_app(environ=environ)
    with app.test_client() as client:
        resp = client.get(
            "/api/ops/quota-abuse",
            headers={"X-Admin-Token": "data-token"},
        )
    assert resp.status_code == 403


def test_ops_endpoint_when_no_tracker() -> None:
    """Graceful response when tracker is not attached (e.g. custom app setup)."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_quota_abuse_routes(app, ":memory:")

    with app.test_client() as client:
        resp = client.get("/api/ops/quota-abuse")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["summary"]["tracker_enabled"] is False
    assert body["events"] == []
