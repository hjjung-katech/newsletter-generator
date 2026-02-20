import sys

from web import runtime_paths


def test_runtime_paths_development_mode(monkeypatch, tmp_path):
    project_root = tmp_path / "project"
    web_dir = project_root / "web"
    (web_dir / "templates").mkdir(parents=True)
    (web_dir / "static").mkdir(parents=True)

    monkeypatch.setattr(runtime_paths, "__file__", str(web_dir / "runtime_paths.py"))
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    assert runtime_paths.resolve_template_dir() == str(web_dir / "templates")
    assert runtime_paths.resolve_static_dir() == str(web_dir / "static")
    assert runtime_paths.resolve_database_path() == str(web_dir / "storage.db")
    assert runtime_paths.resolve_project_root() == str(project_root)
    assert runtime_paths.resolve_env_file_path() == str(project_root / ".env")


def test_runtime_paths_frozen_prefers_external_assets(monkeypatch, tmp_path):
    exe_dir = tmp_path / "dist"
    bundle_dir = tmp_path / "bundle"
    (exe_dir / "templates").mkdir(parents=True)
    (exe_dir / "static").mkdir(parents=True)
    (bundle_dir / "templates").mkdir(parents=True)
    (bundle_dir / "static").mkdir(parents=True)

    monkeypatch.setattr(
        runtime_paths, "__file__", str(bundle_dir / "web" / "runtime_paths.py")
    )
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_dir / "newsletter_web.exe"))

    assert runtime_paths.resolve_template_dir() == str(exe_dir / "templates")
    assert runtime_paths.resolve_static_dir() == str(exe_dir / "static")
    assert runtime_paths.resolve_database_path() == str(exe_dir / "storage.db")
    assert runtime_paths.resolve_project_root() == str(bundle_dir)
    assert runtime_paths.resolve_env_file_path() == str(exe_dir / ".env")


def test_runtime_paths_frozen_uses_bundle_when_external_missing(monkeypatch, tmp_path):
    exe_dir = tmp_path / "dist"
    bundle_dir = tmp_path / "bundle"
    (bundle_dir / "templates").mkdir(parents=True)
    (bundle_dir / "static").mkdir(parents=True)

    monkeypatch.setattr(
        runtime_paths, "__file__", str(bundle_dir / "web" / "runtime_paths.py")
    )
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_dir / "newsletter_web.exe"))

    assert runtime_paths.resolve_template_dir() == str(bundle_dir / "templates")
    assert runtime_paths.resolve_static_dir() == str(bundle_dir / "static")
