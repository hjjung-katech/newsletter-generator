from __future__ import annotations

import sys
from pathlib import Path

import pytest
from flask import Flask, jsonify

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from access_control import (  # noqa: E402
    ALL_SCOPES,
    SCOPE_DATA,
    SCOPE_EMAIL,
    SCOPE_OPS,
    SCOPE_SCHEDULE,
    _check_token_auth,
    _resolve_all_token_configs,
    _scope_for_path,
    _TokenConfig,
    configure_access_control,
    is_protected_route,
)

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


# ---------------------------------------------------------------------------
# Scope constant and helper unit tests
# ---------------------------------------------------------------------------


def test_all_scopes_contains_every_defined_scope() -> None:
    assert SCOPE_DATA in ALL_SCOPES
    assert SCOPE_SCHEDULE in ALL_SCOPES
    assert SCOPE_EMAIL in ALL_SCOPES
    assert SCOPE_OPS in ALL_SCOPES


def test_scope_for_path_maps_known_prefixes() -> None:
    assert _scope_for_path("/api/history") == SCOPE_DATA
    assert _scope_for_path("/api/history/123") == SCOPE_DATA
    assert _scope_for_path("/api/analytics") == SCOPE_DATA
    assert _scope_for_path("/api/presets") == SCOPE_DATA
    assert _scope_for_path("/api/approvals") == SCOPE_DATA
    assert _scope_for_path("/api/source-policies") == SCOPE_DATA
    assert _scope_for_path("/api/archive") == SCOPE_DATA
    assert _scope_for_path("/api/schedule") == SCOPE_SCHEDULE
    assert _scope_for_path("/api/schedules") == SCOPE_SCHEDULE
    assert _scope_for_path("/api/schedules/abc/run") == SCOPE_SCHEDULE
    assert _scope_for_path("/api/send-email") == SCOPE_EMAIL
    assert _scope_for_path("/api/email-config") == SCOPE_EMAIL
    assert _scope_for_path("/api/test-email") == SCOPE_EMAIL
    assert _scope_for_path("/api/ops") == SCOPE_OPS
    assert _scope_for_path("/api/ops/failed-jobs") == SCOPE_OPS


def test_scope_for_path_returns_none_for_public_routes() -> None:
    assert _scope_for_path("/health") is None
    assert _scope_for_path("/api/generate") is None
    assert _scope_for_path("/") is None


def test_resolve_all_token_configs_root_token_has_all_scopes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_API_TOKEN", "root-secret")
    monkeypatch.delenv("ADMIN_API_TOKEN_DATA", raising=False)
    monkeypatch.delenv("ADMIN_API_TOKEN_SCHEDULE", raising=False)
    monkeypatch.delenv("ADMIN_API_TOKEN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_API_TOKEN_OPS", raising=False)

    configs = _resolve_all_token_configs()

    assert len(configs) == 1
    assert configs[0].label == "root"
    assert configs[0].scopes == ALL_SCOPES


def test_resolve_all_token_configs_scoped_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    monkeypatch.setenv("ADMIN_API_TOKEN_SCHEDULE", "sched-secret")
    monkeypatch.delenv("ADMIN_API_TOKEN_DATA", raising=False)
    monkeypatch.delenv("ADMIN_API_TOKEN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_API_TOKEN_OPS", raising=False)

    configs = _resolve_all_token_configs()

    assert len(configs) == 1
    assert configs[0].label == "ADMIN_API_TOKEN_SCHEDULE"
    assert configs[0].scopes == frozenset({SCOPE_SCHEDULE})


def test_resolve_all_token_configs_empty_when_none_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    monkeypatch.delenv("ADMIN_API_TOKEN_DATA", raising=False)
    monkeypatch.delenv("ADMIN_API_TOKEN_SCHEDULE", raising=False)
    monkeypatch.delenv("ADMIN_API_TOKEN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_API_TOKEN_OPS", raising=False)

    assert _resolve_all_token_configs() == []


def test_check_token_auth_root_token_grants_any_scope() -> None:
    configs = [_TokenConfig(value="root-tok", scopes=ALL_SCOPES, label="root")]
    authorized, label = _check_token_auth("root-tok", SCOPE_SCHEDULE, configs)
    assert authorized is True
    assert label == "root"


def test_check_token_auth_scoped_token_allows_matching_scope() -> None:
    configs = [
        _TokenConfig(
            value="sched-tok",
            scopes=frozenset({SCOPE_SCHEDULE}),
            label="ADMIN_API_TOKEN_SCHEDULE",
        )
    ]
    authorized, label = _check_token_auth("sched-tok", SCOPE_SCHEDULE, configs)
    assert authorized is True


def test_check_token_auth_scoped_token_denies_wrong_scope() -> None:
    configs = [
        _TokenConfig(
            value="sched-tok",
            scopes=frozenset({SCOPE_SCHEDULE}),
            label="ADMIN_API_TOKEN_SCHEDULE",
        )
    ]
    # Schedule token should NOT access data routes.
    authorized, label = _check_token_auth("sched-tok", SCOPE_DATA, configs)
    assert authorized is False
    assert label == "ADMIN_API_TOKEN_SCHEDULE"  # token was recognised


def test_check_token_auth_unknown_token_returns_no_label() -> None:
    configs = [_TokenConfig(value="real-tok", scopes=ALL_SCOPES, label="root")]
    authorized, label = _check_token_auth("bogus-tok", SCOPE_OPS, configs)
    assert authorized is False
    assert label is None


# ---------------------------------------------------------------------------
# Integration: scoped tokens via configure_access_control
# ---------------------------------------------------------------------------


def _build_app_scoped(
    *,
    monkeypatch: pytest.MonkeyPatch,
    root_token: str | None = None,
    schedule_token: str | None = None,
    email_token: str | None = None,
    data_token: str | None = None,
    ops_token: str | None = None,
) -> Flask:
    monkeypatch.setenv("APP_ENV", "production")
    for env_var, value in [
        ("ADMIN_API_TOKEN", root_token),
        ("ADMIN_API_TOKEN_SCHEDULE", schedule_token),
        ("ADMIN_API_TOKEN_EMAIL", email_token),
        ("ADMIN_API_TOKEN_DATA", data_token),
        ("ADMIN_API_TOKEN_OPS", ops_token),
    ]:
        if value is not None:
            monkeypatch.setenv(env_var, value)
        else:
            monkeypatch.delenv(env_var, raising=False)

    app = Flask(__name__)
    app.config["TESTING"] = False
    configure_access_control(app)

    @app.route("/api/schedules")
    def schedules():  # type: ignore[return]
        return jsonify({"ok": True})

    @app.route("/api/history")
    def history():  # type: ignore[return]
        return jsonify({"ok": True})

    @app.route("/api/ops/failed-jobs")
    def failed_jobs():  # type: ignore[return]
        return jsonify({"ok": True})

    @app.route("/api/send-email", methods=["POST"])
    def send_email():  # type: ignore[return]
        return jsonify({"ok": True})

    return app


def test_scoped_schedule_token_allows_schedule_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app_scoped(monkeypatch=monkeypatch, schedule_token="sched-secret")

    with app.test_client() as client:
        response = client.get(
            "/api/schedules", headers={"X-Admin-Token": "sched-secret"}
        )

    assert response.status_code == 200


def test_scoped_schedule_token_denies_data_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app_scoped(monkeypatch=monkeypatch, schedule_token="sched-secret")

    with app.test_client() as client:
        response = client.get("/api/history", headers={"X-Admin-Token": "sched-secret"})

    assert response.status_code == 403
    body = response.get_json()
    assert body["error"] == "Insufficient token scope"
    assert body["required_scope"] == SCOPE_DATA


def test_scoped_ops_token_denies_schedule_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app_scoped(monkeypatch=monkeypatch, ops_token="ops-secret")

    with app.test_client() as client:
        response = client.get("/api/schedules", headers={"X-Admin-Token": "ops-secret"})

    assert response.status_code == 403
    body = response.get_json()
    assert body["error"] == "Insufficient token scope"
    assert body["required_scope"] == SCOPE_SCHEDULE


def test_root_token_grants_all_scopes_across_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app_scoped(monkeypatch=monkeypatch, root_token="root-secret")

    with app.test_client() as client:
        r1 = client.get("/api/schedules", headers={"X-Admin-Token": "root-secret"})
        r2 = client.get("/api/history", headers={"X-Admin-Token": "root-secret"})
        r3 = client.get(
            "/api/ops/failed-jobs", headers={"X-Admin-Token": "root-secret"}
        )

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 200


def test_multiple_scoped_tokens_each_allow_only_their_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app_scoped(
        monkeypatch=monkeypatch,
        schedule_token="sched-secret",
        data_token="data-secret",
    )

    with app.test_client() as client:
        sched_ok = client.get(
            "/api/schedules", headers={"X-Admin-Token": "sched-secret"}
        )
        sched_denied = client.get(
            "/api/history", headers={"X-Admin-Token": "sched-secret"}
        )
        data_ok = client.get("/api/history", headers={"X-Admin-Token": "data-secret"})
        data_denied = client.get(
            "/api/schedules", headers={"X-Admin-Token": "data-secret"}
        )

    assert sched_ok.status_code == 200
    assert sched_denied.status_code == 403
    assert data_ok.status_code == 200
    assert data_denied.status_code == 403


def test_bearer_header_accepted_for_scoped_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app_scoped(monkeypatch=monkeypatch, email_token="email-secret")

    with app.test_client() as client:
        response = client.post(
            "/api/send-email",
            headers={"Authorization": "Bearer email-secret"},
        )

    assert response.status_code == 200


def test_wrong_token_returns_401_not_403(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app_scoped(monkeypatch=monkeypatch, schedule_token="sched-secret")

    with app.test_client() as client:
        response = client.get(
            "/api/schedules", headers={"X-Admin-Token": "completely-wrong"}
        )

    assert response.status_code == 401
    assert response.get_json() == {"error": "Admin API token required"}


def test_503_when_no_tokens_configured_at_all(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app_scoped(monkeypatch=monkeypatch)  # all tokens None

    with app.test_client() as client:
        response = client.get("/api/schedules")

    assert response.status_code == 503
