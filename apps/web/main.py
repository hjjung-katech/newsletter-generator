"""Web runtime wrapper."""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from web.app import app  # noqa: E402


def main() -> None:
    app_env = os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "production"
    app.run(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        debug=app_env == "development",
    )


if __name__ == "__main__":
    main()
