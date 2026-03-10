from pathlib import Path

from scripts.devtools import setup_env


def test_render_env_content_uses_canonical_sample(monkeypatch, tmp_path):
    sample = tmp_path / ".env.example"
    sample.write_text(
        "# sample\n"
        "APP_ENV=development\n"
        "SERPER_API_KEY=default-serper\n"
        "EMAIL_SENDER=default@example.com\n"
        "# FLASK_ENV=development\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_env, "ENV_SAMPLE_PATH", sample)

    rendered = setup_env.render_env_content(
        {
            "SERPER_API_KEY": "custom-serper",
            "EMAIL_SENDER": "newsletter@example.com",
        }
    )

    assert "APP_ENV=development" in rendered
    assert "SERPER_API_KEY=custom-serper" in rendered
    assert "EMAIL_SENDER=newsletter@example.com" in rendered
    assert "# FLASK_ENV=development" in rendered
