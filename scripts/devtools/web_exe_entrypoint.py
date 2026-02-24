"""PyInstaller entrypoint for the Windows web executable.

Placing this script under ``scripts/devtools`` avoids introducing new
repository-root runtime files while preventing stdlib ``types`` shadowing
by ``web/types.py`` during PyInstaller subprocess imports.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure repository root is on sys.path before importing web.app.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web.app import app


def main() -> None:
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    print(f"Starting Flask app on port {port}, debug={debug}")
    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()
