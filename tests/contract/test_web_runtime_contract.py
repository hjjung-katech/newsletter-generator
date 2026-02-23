"""Contract tests for Flask runtime bootstrap behavior."""

from __future__ import annotations

import pytest

from web import sentry_integration

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def test_web_app_registers_core_routes() -> None:
    from web.app import app

    registered_routes = {rule.rule for rule in app.url_map.iter_rules()}
    expected_routes = {
        "/",
        "/health",
        "/api/generate",
        "/api/send-email",
        "/api/newsletter-html/<job_id>",
    }

    assert expected_routes.issubset(registered_routes)


def test_setup_sentry_returns_noop_callbacks_without_dsn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from newsletter_core.public import settings as settings_module

    class _Settings:
        sentry_dsn = None
        sentry_traces_sample_rate = 0.0
        environment = "test"
        app_version = "test"
        sentry_profiles_sample_rate = 0.0

    monkeypatch.setattr(settings_module, "get_settings", lambda: _Settings())
    monkeypatch.delenv("SENTRY_DSN", raising=False)

    set_user_context, set_tags = sentry_integration.setup_sentry()

    assert callable(set_user_context)
    assert callable(set_tags)
    assert (
        set_user_context(user_id="user-1", email="u@example.com", role="admin") is None
    )
    assert set_tags(component="web", layer="runtime") is None
