from __future__ import annotations

import sys
from pathlib import Path

import pytest
from flask import Flask

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

import cors_config  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def _build_app() -> Flask:
    app = Flask(__name__)

    @app.get("/api/ping")
    def ping() -> dict[str, str]:
        return {"status": "ok"}

    return app


def test_production_default_disables_cross_origin_requests() -> None:
    app = _build_app()
    cors_config.configure_cors(app, environ={})

    with app.test_client() as client:
        response = client.get("/api/ping", headers={"Origin": "https://example.com"})

    assert response.headers.get("Access-Control-Allow-Origin") is None


def test_testing_mode_allows_localhost_origins() -> None:
    app = _build_app()
    app.config["TESTING"] = True
    cors_config.configure_cors(app, environ={})

    with app.test_client() as client:
        response = client.get("/api/ping", headers={"Origin": "http://localhost:3000"})

    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"


def test_explicit_origin_allowlist_is_applied() -> None:
    app = _build_app()
    cors_config.configure_cors(
        app,
        environ={
            "ALLOWED_ORIGINS": "https://app.example.com,https://admin.example.com"
        },
    )

    with app.test_client() as client:
        allowed = client.get("/api/ping", headers={"Origin": "https://app.example.com"})
        blocked = client.get(
            "/api/ping", headers={"Origin": "https://evil.example.com"}
        )

    assert allowed.headers["Access-Control-Allow-Origin"] == "https://app.example.com"
    assert blocked.headers.get("Access-Control-Allow-Origin") is None


def test_wildcard_origin_is_ignored_outside_development(caplog) -> None:
    app = _build_app()

    with caplog.at_level("WARNING"):
        origins = cors_config.resolve_allowed_cors_origins(
            app, environ={"ALLOWED_ORIGINS": "*"}
        )

    assert origins == ()
    assert "Ignoring wildcard ALLOWED_ORIGINS" in caplog.text
