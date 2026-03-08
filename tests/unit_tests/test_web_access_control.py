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


def _build_app(*, testing: bool, monkeypatch: pytest.MonkeyPatch) -> Flask:
    monkeypatch.setenv("APP_ENV", "production")
    app = Flask(__name__)
    app.config["TESTING"] = testing
    configure_access_control(app)

    @app.route("/api/schedules")
    def schedules():
        return jsonify({"ok": True})

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


def test_protected_route_matcher_covers_sensitive_paths() -> None:
    assert is_protected_route("/api/schedule")
    assert is_protected_route("/api/schedule/demo/run")
    assert is_protected_route("/api/presets")
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
