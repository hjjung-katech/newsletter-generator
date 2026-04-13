"""
Runtime-aware path helpers for web app bootstrap.

This module keeps filesystem decisions deterministic between development mode
and PyInstaller one-file runtime.

Path-resolution logic now lives in
``newsletter_core.infrastructure.platform._paths``; this module delegates to it
so that existing call-sites continue to work unchanged.

``__file__`` is forwarded so that test-suite monkeypatching of
``runtime_paths.__file__`` continues to control path resolution correctly.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is in sys.path so newsletter_core is importable
# when this module is loaded from the web/ directory directly
# (e.g. `python web/init_database.py`).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from newsletter_core.infrastructure.platform._paths import (  # noqa: E402
    resolve_database_path as _resolve_database_path,
)
from newsletter_core.infrastructure.platform._paths import (  # noqa: E402
    resolve_env_file_path as _resolve_env_file_path,
)
from newsletter_core.infrastructure.platform._paths import (  # noqa: E402
    resolve_project_root as _resolve_project_root,
)
from newsletter_core.infrastructure.platform._paths import (  # noqa: E402
    resolve_static_dir as _resolve_static_dir,
)
from newsletter_core.infrastructure.platform._paths import (  # noqa: E402
    resolve_template_dir as _resolve_template_dir,
)


def resolve_template_dir() -> str:
    return str(_resolve_template_dir(__file__))


def resolve_static_dir() -> str:
    return str(_resolve_static_dir(__file__))


def resolve_database_path() -> str:
    return str(_resolve_database_path(__file__))


def resolve_project_root() -> str:
    return str(_resolve_project_root(__file__))


def resolve_env_file_path() -> str:
    return str(_resolve_env_file_path(__file__))
