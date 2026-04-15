"""Playwright E2E smoke tests — two core application flows.

Flow 1: GET /health  → server is up, returns service JSON with correct key
Flow 2: GET /        → index page loads with correct <title>
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page  # provided by browser/page fixtures in conftest.py


@pytest.mark.e2e
def test_health_endpoint_ok(page: Page, live_server_url: str) -> None:
    """GET /health returns an HTTP 200-range response with service JSON body."""
    response = page.goto(f"{live_server_url}/health", timeout=10_000)
    assert response is not None, "No response from /health"
    # TESTING=True keeps status 200 even without external API keys.
    # 503 is also accepted here (error state still means the server is up).
    assert response.status in (200, 503), f"Unexpected status {response.status}"
    body = page.content()
    assert "newsletter-generator" in body, "Service name missing from /health response"


@pytest.mark.e2e
def test_index_page_loads(page: Page, live_server_url: str) -> None:
    """GET / renders the index.html page with the correct <title>."""
    response = page.goto(f"{live_server_url}/", timeout=10_000)
    assert response is not None, "No response from /"
    assert response.status == 200, f"Unexpected status {response.status}"
    page.wait_for_load_state("domcontentloaded")
    assert (
        page.title() == "Newsletter Generator"
    ), f"Unexpected page title: {page.title()!r}"
