#!/usr/bin/env python3
"""Compatibility shim for legacy build command.

Canonical entrypoint:
    python scripts/devtools/build_web_exe_enhanced.py
"""

from __future__ import annotations

from build_web_exe_enhanced import build


def main() -> int:
    print(
        "[DEPRECATED] scripts/devtools/build_web_exe.py is a compatibility shim.\n"
        "Use: python scripts/devtools/build_web_exe_enhanced.py"
    )
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
