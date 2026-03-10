from __future__ import annotations

import importlib
import sys
from types import ModuleType

import pytest
from flask import Flask


def _pop_module(name: str) -> ModuleType | None:
    module = sys.modules.get(name)
    if module is not None:
        del sys.modules[name]
    return module


def _restore_module(name: str, module: ModuleType | None) -> None:
    sys.modules.pop(name, None)
    if module is not None:
        sys.modules[name] = module


@pytest.mark.unit
def test_web_app_import_does_not_bootstrap_runtime_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_state_module = importlib.import_module("web.db_state")
    newsletter_clients_module = importlib.import_module("web.newsletter_clients")
    sentry_module = importlib.import_module("web.sentry_integration")
    redis_module = importlib.import_module("redis")

    calls = {"db": 0, "cli": 0, "sentry": 0, "redis": 0}

    monkeypatch.setattr(
        db_state_module,
        "ensure_database_schema",
        lambda *_args, **_kwargs: calls.__setitem__("db", calls["db"] + 1),
    )
    monkeypatch.setattr(
        newsletter_clients_module,
        "create_newsletter_cli",
        lambda: calls.__setitem__("cli", calls["cli"] + 1),
    )
    monkeypatch.setattr(
        sentry_module,
        "setup_sentry",
        lambda: calls.__setitem__("sentry", calls["sentry"] + 1),
    )
    monkeypatch.setattr(
        redis_module,
        "from_url",
        lambda *_args, **_kwargs: calls.__setitem__("redis", calls["redis"] + 1),
    )

    previous = _pop_module("web.app")
    try:
        web_app = importlib.import_module("web.app")

        assert calls == {"db": 0, "cli": 0, "sentry": 0, "redis": 0}
        assert web_app.newsletter_cli is None
        assert web_app.redis_conn is None
        assert web_app.task_queue is None
    finally:
        _restore_module("web.app", previous)


@pytest.mark.unit
def test_create_app_registers_routes_without_eager_runtime_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous = _pop_module("web.app")
    try:
        web_app = importlib.import_module("web.app")
        calls = {"cli": 0, "queue": 0, "sentry": 0}

        def fake_create_newsletter_cli() -> object:
            calls["cli"] += 1
            return object()

        def fake_create_task_queue(_app: Flask) -> tuple[object, object]:
            calls["queue"] += 1
            return object(), object()

        def fake_setup_sentry() -> tuple[object, object]:
            calls["sentry"] += 1
            return object(), object()

        monkeypatch.setattr(
            web_app, "create_newsletter_cli", fake_create_newsletter_cli
        )
        monkeypatch.setattr(web_app, "_create_task_queue", fake_create_task_queue)
        monkeypatch.setattr(web_app, "setup_sentry", fake_setup_sentry)

        app = web_app.create_app()
        app.config["TESTING"] = True

        assert isinstance(app, Flask)
        assert "/api/generate" in {rule.rule for rule in app.url_map.iter_rules()}
        assert calls == {"cli": 0, "queue": 0, "sentry": 1}

        with app.test_client() as client:
            response = client.get("/health")

        assert response.status_code == 200
        assert calls == {"cli": 1, "queue": 0, "sentry": 1}
    finally:
        _restore_module("web.app", previous)


@pytest.mark.unit
def test_generation_facade_import_is_lazy_for_legacy_modules() -> None:
    previous_generation = _pop_module("newsletter_core.public.generation")
    previous_graph = _pop_module("newsletter.graph")
    previous_tools = _pop_module("newsletter.tools")

    try:
        importlib.import_module("newsletter_core.public.generation")

        assert "newsletter.graph" not in sys.modules
        assert "newsletter.tools" not in sys.modules
    finally:
        _restore_module("newsletter_core.public.generation", previous_generation)
        _restore_module("newsletter.graph", previous_graph)
        _restore_module("newsletter.tools", previous_tools)
