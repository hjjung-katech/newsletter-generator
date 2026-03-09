from apps.web import main as web_main


def test_apps_web_main_defaults(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)

    captured: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(web_main.app, "run", fake_run)

    web_main.main()

    assert captured == {"host": "0.0.0.0", "port": 8000, "debug": False}


def test_apps_web_main_honors_app_env_and_port(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "5001")

    captured: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(web_main.app, "run", fake_run)

    web_main.main()

    assert captured == {"host": "127.0.0.1", "port": 5001, "debug": True}


def test_apps_web_main_supports_flask_env_compat(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)

    captured: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(web_main.app, "run", fake_run)

    web_main.main()

    assert captured["debug"] is True
