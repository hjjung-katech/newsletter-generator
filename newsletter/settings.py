"""Legacy compatibility wrapper around centralized settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from .centralized_settings import CentralizedSettings as Settings
from .centralized_settings import clear_settings_cache, get_settings


def _default_base_dir() -> Path:
    return Path(__file__).parent.parent


def _safe_setting(name: str, default: Any = None) -> Any:
    try:
        value = getattr(get_settings(), name)
    except Exception:
        return default
    return default if value is None else value


class LegacySettings:
    """Legacy attribute surface backed by centralized settings."""

    @property
    def MOCK_MODE(self) -> bool:
        return bool(_safe_setting("mock_mode", False))

    @property
    def LOG_LEVEL(self) -> str:
        return str(_safe_setting("log_level", "INFO"))

    @property
    def DEFAULT_PERIOD(self) -> int:
        return int(_safe_setting("default_period", 14))

    @property
    def VALID_PERIODS(self) -> list[int]:
        return list(_safe_setting("valid_periods", [1, 7, 14, 30]))

    @property
    def BASE_DIR(self) -> Path:
        return cast(Path, _safe_setting("base_dir", _default_base_dir()))

    @property
    def OUTPUT_DIR(self) -> Path:
        return cast(Path, _safe_setting("output_dir", _default_base_dir() / "output"))

    @property
    def CONFIG_DIR(self) -> Path:
        return cast(Path, _safe_setting("config_dir", _default_base_dir() / "config"))

    @property
    def TEMPLATES_DIR(self) -> Path:
        return cast(
            Path, _safe_setting("templates_dir", _default_base_dir() / "templates")
        )

    def get_config_summary(self) -> dict[str, Any]:
        try:
            return cast(dict[str, Any], get_settings().get_config_summary())
        except Exception:
            return {}


settings = LegacySettings()


def __getattr__(name: str) -> Any:
    if name == "APP_ENV":
        return _safe_setting("app_env", "production")
    if name == "MOCK_MODE":
        return settings.MOCK_MODE
    if name == "LOG_LEVEL":
        return settings.LOG_LEVEL
    if name == "DEFAULT_PERIOD":
        return settings.DEFAULT_PERIOD
    if name == "VALID_PERIODS":
        return settings.VALID_PERIODS
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "LegacySettings",
    "Settings",
    "clear_settings_cache",
    "get_settings",
    "settings",
]
