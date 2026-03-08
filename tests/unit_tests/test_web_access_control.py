from __future__ import annotations

import sys
from pathlib import Path

import pytest
from flask import Flask, jsonify

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from access_control import configure_access_control, is_protected_route  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def _build_app(
    *,
    testing: bool,
    monkeypatch: pytest.MonkeyPatch,
    generate_rate_limit: int = 5,
    generate_window_seconds: int = 60,
    protected_rate_limit: int = 30,
    protected_window_seconds: int = 60,
    generate_max_body_bytes: int = 32 * 1024,
) -> Flask:
    monkeypatch.setenv("APP_ENV", "production")
    app = Flask(__name__)
    app.config["TESTING"] = testing
    configure_access_control(
        app,
        generate_rate_limit=generate_rate_limit,
        generate_window_seconds=generate_window_seconds,
        protected_rate_limit=protected_rate_limit,
        protected_window_seconds=protected_window_seconds,
        generate_max_body_bytes=generate_max_body_bytes,
    )

    @app.route("/api/schedules")
    def schedules():
        return jsonify({"ok": True})

    @app.route("/api/generate", methods=["POST"])
    def generate():
        return jsonify({"ok": True})

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


def test_protected_route_matcher_covers_sensitive_paths() -> None:
    assert is_protected_route("/api/approvals")
    assert is_protected_route("/api/analytics")
    assert is_protected_route("/api/archive")
    assert is_protected_route("/api/archive/search")
    assert is_protected_route("/api/schedule")
    assert is_protected_route("/api/schedule/demo/run")
    assert is_protected_route("/api/presets")
    assert is_protected_route("/api/source-policies")
    assert is_protected_route("/api/send-email")
    assert not is_protected_route("/api/generate")
    assert not is_protected_route("/health")


def test_testing_mode_bypasses_admin_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    app = _build_app(testing=True, monkeypatch=monkeypatch)

    with app.test_client() as client:
        response = client.get("/api/schedules")

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}


def test_production_like_runtime_requires_admin_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_API_TOKEN", "top-secret-token")
    app = _build_app(testing=False, monkeypatch=monkeypatch)

    with app.test_client() as client:
        response = client.get("/api/schedules")

    assert response.status_code == 401
    assert response.get_json() == {"error": "Admin API token required"}


@pytest.mark.parametrize(
    "headers",
    [
        {"X-Admin-Token": "top-secret-token"},
        {"Authorization": "Bearer top-secret-token"},
    ],
)
def test_production_like_runtime_accepts_valid_admin_token(
    monkeypatch: pytest.MonkeyPatch, headers: dict[str, str]
) -> None:
    monkeypatch.setenv("ADMIN_API_TOKEN", "top-secret-token")
    app = _build_app(testing=False, monkeypatch=monkeypatch)

    with app.test_client() as client:
        response = client.get("/api/schedules", headers=headers)

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}


def test_production_like_runtime_fails_closed_when_token_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    app = _build_app(testing=False, monkeypatch=monkeypatch)

    with app.test_client() as client:
        response = client.get("/api/schedules")

    assert response.status_code == 503
    assert response.get_json() == {
        "error": "ADMIN_API_TOKEN is required for protected routes"
    }


def test_public_routes_remain_open_in_production_like_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_API_TOKEN", "top-secret-token")
    app = _build_app(testing=False, monkeypatch=monkeypatch)

    with app.test_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_generate_route_is_rate_limited_in_production_like_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app(
        testing=False,
        monkeypatch=monkeypatch,
        generate_rate_limit=2,
        generate_window_seconds=60,
    )

    with app.test_client() as client:
        first = client.post("/api/generate", json={"keywords": "AI"})
        second = client.post("/api/generate", json={"keywords": "AI"})
        third = client.post("/api/generate", json={"keywords": "AI"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.get_json()["error"] == "Generate rate limit exceeded"
    assert int(third.headers["Retry-After"]) >= 1


def test_generate_route_rejects_large_request_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app(
        testing=False,
        monkeypatch=monkeypatch,
        generate_max_body_bytes=16,
    )

    with app.test_client() as client:
        response = client.post(
            "/api/generate",
            data=b"x" * 17,
            content_type="application/json",
        )

    assert response.status_code == 413
    assert response.get_json() == {"error": "Generate request body is too large"}


def test_protected_routes_are_rate_limited_even_with_valid_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_API_TOKEN", "top-secret-token")
    app = _build_app(
        testing=False,
        monkeypatch=monkeypatch,
        protected_rate_limit=2,
        protected_window_seconds=60,
    )

    with app.test_client() as client:
        headers = {"X-Admin-Token": "top-secret-token"}
        first = client.get("/api/schedules", headers=headers)
        second = client.get("/api/schedules", headers=headers)
        third = client.get("/api/schedules", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.get_json()["error"] == "Protected route rate limit exceeded"
    assert int(third.headers["Retry-After"]) >= 1
