from __future__ import annotations

import sys
from pathlib import Path

import pytest
from flask import Flask

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

import routes_ops  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def test_ops_routes_are_disabled_by_default(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ENABLE_DEBUG_ROUTES", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("FLASK_ENV", raising=False)

    app = Flask(__name__)
    routes_ops.register_ops_routes(app, str(tmp_path / "storage.db"))

    registered_routes = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/debug/history-table" not in registered_routes
    assert "/debug/clear-pending" not in registered_routes
    assert "/test" not in registered_routes
    assert "/manual-test" not in registered_routes


def test_ops_routes_are_enabled_for_testing_app(tmp_path: Path) -> None:
    app = Flask(__name__)
    app.config["TESTING"] = True

    routes_ops.register_ops_routes(app, str(tmp_path / "storage.db"))

    registered_routes = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/debug/history-table" in registered_routes
    assert "/debug/clear-pending" in registered_routes
    assert "/test" in registered_routes
    assert "/manual-test" in registered_routes
