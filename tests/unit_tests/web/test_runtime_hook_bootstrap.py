from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

LEGACY_ALIAS = "web." + "web_types"
MODULE_KEYS = ("web", "web.api_types", "web.types", LEGACY_ALIAS, "web_types")


def _snapshot_modules() -> dict[str, object | None]:
    return {key: sys.modules.get(key) for key in MODULE_KEYS}


def _restore_modules(snapshot: dict[str, object | None]) -> None:
    for key, module in snapshot.items():
        if module is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = module


def _clear_bootstrap_modules() -> None:
    for key in MODULE_KEYS:
        sys.modules.pop(key, None)


def _assert_generate_request_loaded(web_types_module: object) -> None:
    request_cls = getattr(web_types_module, "GenerateNewsletterRequest")
    payload = request_cls(keywords="AI", period=7)
    assert payload.keywords == "AI"
    assert payload.period == 7


@pytest.mark.unit
def test_setup_web_types_non_frozen_loads_generate_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_hook = importlib.import_module("web.runtime_hook")
    snapshot = _snapshot_modules()

    try:
        _clear_bootstrap_modules()
        monkeypatch.delattr(sys, "frozen", raising=False)
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)

        runtime_hook._setup_web_types()

        assert "web.api_types" in sys.modules
        web_types_module = sys.modules["web.api_types"]
        assert sys.modules[LEGACY_ALIAS] is web_types_module
        assert sys.modules["web_types"] is web_types_module
        _assert_generate_request_loaded(web_types_module)
    finally:
        _restore_modules(snapshot)


@pytest.mark.unit
def test_setup_web_types_frozen_loads_generate_request(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime_hook = importlib.import_module("web.runtime_hook")
    snapshot = _snapshot_modules()

    try:
        _clear_bootstrap_modules()
        bundle_root = tmp_path / "bundle"
        bundle_web_dir = bundle_root / "web"
        bundle_web_dir.mkdir(parents=True)

        source_types = Path(runtime_hook.__file__).with_name("api_types.py")
        target_types = bundle_web_dir / "api_types.py"
        target_types.write_text(
            source_types.read_text(encoding="utf-8"), encoding="utf-8"
        )

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(bundle_root), raising=False)

        runtime_hook._setup_web_types()

        assert "web.api_types" in sys.modules
        web_types_module = sys.modules["web.api_types"]
        assert sys.modules[LEGACY_ALIAS] is web_types_module
        assert sys.modules["web_types"] is web_types_module
        _assert_generate_request_loaded(web_types_module)
    finally:
        _restore_modules(snapshot)
