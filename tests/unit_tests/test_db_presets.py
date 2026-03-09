from __future__ import annotations

import sys
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from db_presets import (  # noqa: E402
    create_generation_preset,
    list_generation_presets,
    update_generation_preset,
)
from db_state import ensure_database_schema  # noqa: E402


def test_create_generation_preset_lists_default_first(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    create_generation_preset(
        str(db_path),
        "preset-first",
        "First",
        None,
        {"keywords": ["ai"], "template_style": "compact", "period": 7},
        is_default=False,
    )
    create_generation_preset(
        str(db_path),
        "preset-default",
        "Default",
        "Primary preset",
        {"domain": "battery", "template_style": "modern", "period": 14},
        is_default=True,
    )

    presets = list_generation_presets(str(db_path))

    assert [preset["id"] for preset in presets] == ["preset-default", "preset-first"]
    assert presets[0]["is_default"] is True


def test_update_generation_preset_promotes_only_one_default(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    create_generation_preset(
        str(db_path),
        "preset-a",
        "Preset A",
        None,
        {"keywords": ["ai"], "template_style": "compact", "period": 7},
        is_default=True,
    )
    create_generation_preset(
        str(db_path),
        "preset-b",
        "Preset B",
        None,
        {"domain": "chips", "template_style": "detailed", "period": 14},
        is_default=False,
    )

    updated = update_generation_preset(
        str(db_path),
        "preset-b",
        "Preset B",
        "Promoted",
        {"domain": "chips", "template_style": "modern", "period": 30},
        is_default=True,
    )

    presets = {preset["id"]: preset for preset in list_generation_presets(str(db_path))}
    assert updated is not None
    assert presets["preset-a"]["is_default"] is False
    assert presets["preset-b"]["is_default"] is True
    assert presets["preset-b"]["params"]["template_style"] == "modern"
