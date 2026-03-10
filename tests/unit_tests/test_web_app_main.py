from web import app as web_app


def test_web_app_main_defaults(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)

    captured: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(web_app.app, "run", fake_run)

    web_app.main()

    assert captured == {"host": "0.0.0.0", "port": 8000, "debug": False}


def test_web_app_main_honors_app_env_and_port(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "5001")

    captured: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(web_app.app, "run", fake_run)

    web_app.main()

    assert captured == {"host": "127.0.0.1", "port": 5001, "debug": True}


def test_web_app_main_supports_flask_env_compat(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)

    captured: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(web_app.app, "run", fake_run)

    web_app.main()

    assert captured["debug"] is True
