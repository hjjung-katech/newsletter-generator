"""E2E smoke test fixtures — live Flask server + Playwright browser managed directly.

Uses `playwright` (not `pytest-playwright`) to avoid installing `pytest-base-url`,
which causes a fixture-scope conflict with the function-scoped `base_url` fixture
defined in tests/conftest.py.
"""
from __future__ import annotations

import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Generator

import pytest

try:
    from playwright.sync_api import Browser, Page, sync_playwright
except ImportError:  # pragma: no cover
    pytest.skip(
        "playwright package not installed — run: pip install -e '.[e2e]'",
        allow_module_level=True,
    )

_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _free_port() -> int:
    """Return an ephemeral free TCP port on 127.0.0.1."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def live_server_url() -> Generator[str, None, None]:
    """Start the Flask app on a random free port and yield its base URL.

    TESTING=True suppresses the config-warning degraded status so /health
    returns 200 even without external API keys.
    """
    from web.app import create_app  # local import — keeps fixture lazy

    app = create_app()
    app.config["TESTING"] = True

    port = _free_port()

    server_thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=port, use_reloader=False),
        daemon=True,
    )
    server_thread.start()

    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    else:
        pytest.skip("Live server did not start within 10 seconds")

    yield f"http://127.0.0.1:{port}"


@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    """Headless Chromium browser instance shared for the test session."""
    with sync_playwright() as pw:
        br = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        yield br
        br.close()


@pytest.fixture
def page(browser: Browser) -> Generator[Page, None, None]:
    """New browser page per test; closed after each test."""
    pg = browser.new_page()
    yield pg
    pg.close()
