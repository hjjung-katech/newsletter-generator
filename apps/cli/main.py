"""CLI runtime wrapper."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from newsletter.cli import app  # noqa: E402


def main() -> None:
    app()


if __name__ == "__main__":
    main()
