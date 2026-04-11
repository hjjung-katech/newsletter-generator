"""Platform adapter infrastructure for OS-specific behavior."""

from __future__ import annotations

from newsletter_core.infrastructure.platform._frozen import (
    get_bundle_root,
    is_frozen,
    is_frozen_any,
)
from newsletter_core.infrastructure.platform._paths import (
    resolve_database_path,
    resolve_env_file_path,
    resolve_project_root,
    resolve_static_dir,
    resolve_template_dir,
)
from newsletter_core.infrastructure.platform._resolver import get_platform_adapter

__all__ = [
    "get_platform_adapter",
    "is_frozen",
    "is_frozen_any",
    "get_bundle_root",
    "resolve_template_dir",
    "resolve_static_dir",
    "resolve_database_path",
    "resolve_project_root",
    "resolve_env_file_path",
]
