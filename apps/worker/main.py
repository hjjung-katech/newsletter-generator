"""Worker runtime wrapper."""

import runpy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> None:
    runpy.run_module("web.worker", run_name="__main__")


if __name__ == "__main__":
    main()
