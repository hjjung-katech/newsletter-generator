from pathlib import Path

from newsletter.utils import file_naming


def test_ensure_debug_directory_defaults_to_hidden_local_dir(monkeypatch):
    monkeypatch.delenv("NEWSLETTER_DEBUG_DIR", raising=False)

    debug_dir = Path(file_naming.ensure_debug_directory())

    assert debug_dir.name == "debug_files"
    assert debug_dir.parent.name == ".local"
    assert debug_dir.is_dir()


def test_generate_debug_filename_uses_env_override(monkeypatch, tmp_path):
    override_dir = tmp_path / "debug"
    monkeypatch.setenv("NEWSLETTER_DEBUG_DIR", str(override_dir))

    debug_file = Path(
        file_naming.generate_debug_filename(
            prefix="template_debug",
            extension="log",
            timestamp="20260309_120000",
        )
    )

    assert debug_file == override_dir / "template_debug_20260309_120000.log"
    assert override_dir.is_dir()
