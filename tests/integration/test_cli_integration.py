#!/usr/bin/env python3
"""Integration tests for CLI facade wiring."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from typer.testing import CliRunner

from newsletter.cli import app


@pytest.mark.integration
@pytest.mark.mock_api
def test_cli_run_uses_public_generation_facade(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner = CliRunner()

    def fake_generate_newsletter(request):  # noqa: ANN001
        return {
            "status": "success",
            "html_content": "<html><head><title>CLI Facade</title></head><body>ok</body></html>",
            "title": "CLI Facade",
            "generation_stats": {
                "step_times": {"collect": 0.1},
                "total_time": 0.2,
            },
            "input_params": {
                "keywords": ["AI"],
                "domain": None,
                "template_style": "compact",
                "email_compatible": False,
                "period": 7,
                "suggest_count": 10,
            },
            "error": None,
        }

    captured = {}

    def fake_save_locally(  # noqa: ANN001
        html_content, filename_base, output_format="html", output_directory="output"
    ):
        captured["html_content"] = html_content
        captured["filename_base"] = filename_base
        captured["output_format"] = output_format
        captured["output_directory"] = output_directory
        return True

    monkeypatch.setattr(
        "newsletter_core.public.generation.generate_newsletter",
        fake_generate_newsletter,
    )
    monkeypatch.setattr("newsletter.deliver.save_locally", fake_save_locally)

    result = runner.invoke(
        app,
        [
            "run",
            "--keywords",
            "AI",
            "--period",
            "7",
            "--output-format",
            "html",
        ],
    )

    assert result.exit_code == 0
    assert captured["output_format"] == "html"
    assert "CLI Facade" in captured["html_content"]


@pytest.mark.integration
def test_cli_module_references_public_facade_import() -> None:
    from newsletter import cli

    source = inspect.getsource(cli.run)
    assert "newsletter_core.public.generation" in source
