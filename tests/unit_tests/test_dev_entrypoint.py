from pathlib import Path

import pytest

from scripts.devtools import dev_entrypoint


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return path


def test_resolve_existing_venv_python_prefers_local(tmp_path):
    paths = dev_entrypoint.repo_paths(tmp_path)
    local_python = _touch(dev_entrypoint.venv_python(paths.default_venv_dir))
    _touch(dev_entrypoint.venv_python(paths.legacy_venv_dir))

    assert dev_entrypoint.resolve_existing_venv_python(paths) == local_python


def test_build_run_command_defaults_newsletter_to_help(tmp_path, monkeypatch):
    paths = dev_entrypoint.repo_paths(tmp_path)
    python_path = _touch(dev_entrypoint.venv_python(paths.default_venv_dir))
    monkeypatch.setattr(dev_entrypoint, "REPO_ROOT", tmp_path)

    command = dev_entrypoint.build_run_command(paths, "newsletter", [])

    assert command == [str(python_path), "-m", "newsletter", "--help"]


def test_build_run_command_strips_passthrough_separator(tmp_path):
    paths = dev_entrypoint.repo_paths(tmp_path)
    python_path = _touch(dev_entrypoint.venv_python(paths.default_venv_dir))

    command = dev_entrypoint.build_run_command(
        paths,
        "newsletter",
        ["--", "run", "--keywords", "AI"],
    )

    assert command == [
        str(python_path),
        "-m",
        "newsletter",
        "run",
        "--keywords",
        "AI",
    ]


def test_check_file_for_tokens_rejects_forbidden_alias(tmp_path):
    sample = tmp_path / "sample.env"
    sample.write_text("FROM_EMAIL=test@example.com\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="FROM_EMAIL"):
        dev_entrypoint.check_file_for_tokens(sample)


def test_run_web_smoke_uses_python_source_health_harness(tmp_path, monkeypatch):
    paths = dev_entrypoint.repo_paths(tmp_path)
    python_path = _touch(dev_entrypoint.venv_python(paths.default_venv_dir))
    recorded: dict[str, object] = {}

    monkeypatch.setattr(
        dev_entrypoint, "resolve_python", lambda *_args, **_kwargs: python_path
    )

    def fake_run_checked(cmd, *, cwd=None, env=None):
        recorded["cmd"] = cmd
        recorded["cwd"] = cwd
        recorded["env"] = env

    monkeypatch.setattr(dev_entrypoint, "run_checked", fake_run_checked)

    dev_entrypoint.run_web_smoke(paths)

    assert recorded["cmd"] == [
        str(python_path),
        "scripts/devtools/web_health_smoke.py",
        "--mode",
        "source",
    ]
    assert recorded["cwd"] == paths.repo_root
    assert recorded["env"]["MOCK_MODE"] == "true"
    assert recorded["env"]["TESTING"] == "1"
