"""PyInstaller entrypoint for the Windows web executable.

Using a repository-root entrypoint prevents ``web/types.py`` from shadowing
the stdlib ``types`` module during PyInstaller isolated subprocess imports.
"""

from __future__ import annotations

import os

from web.app import app


def main() -> None:
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    print(f"Starting Flask app on port {port}, debug={debug}")
    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()
