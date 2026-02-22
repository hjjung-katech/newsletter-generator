"""Compatibility namespace for local source layout.

This keeps `newsletter_core` importable when running directly from repository root
without editable installs.
"""

from pathlib import Path

_pkg_path = Path(__file__).resolve().parent
_src_pkg = _pkg_path.parent / "packages" / "newsletter_core" / "src" / "newsletter_core"

if _src_pkg.exists():
    pkg_paths = list(globals().get("__path__", []))
    if str(_src_pkg) not in pkg_paths:
        pkg_paths.append(str(_src_pkg))
    globals()["__path__"] = pkg_paths
