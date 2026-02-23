#!/usr/bin/env python3
"""Compatibility shim for legacy root script path."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parent / "scripts" / "devtools" / "build_web_exe.py"


def main() -> int:
    if not TARGET.exists():
        print(f"[shim-error] Missing target script: {TARGET}", file=sys.stderr)
        return 2

    print(
        "[deprecated] build_web_exe.py moved to scripts/devtools/build_web_exe.py",
        file=sys.stderr,
    )
    sys.argv[0] = str(TARGET)
    runpy.run_path(str(TARGET), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
