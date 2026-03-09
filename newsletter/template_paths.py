from __future__ import annotations

from pathlib import Path

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def get_newsletter_template_dir() -> str:
    return str(_TEMPLATE_DIR)


def get_newsletter_template_path(template_name: str) -> str:
    return str(_TEMPLATE_DIR / template_name)
