"""Contract tests for newsletter_core public generation facade."""

from __future__ import annotations

import warnings
from unittest.mock import patch

import pytest

from newsletter_core.public.generation import (
    GenerateNewsletterRequest,
    NewsletterGenerationError,
    generate_newsletter,
)


@pytest.mark.unit
@pytest.mark.mock_api
def test_generation_facade_response_schema() -> None:
    """Public facade returns the stable response schema."""
    html = "<html><head><title>Facade Smoke</title></head><body>ok</body></html>"
    info = {"step_times": {"collect": 0.1}, "total_time": 0.2}

    with patch(
        "newsletter_core.public.generation.graph.generate_newsletter",
        return_value=(html, "success"),
    ), patch(
        "newsletter_core.public.generation.graph.get_last_generation_info",
        return_value=info,
    ):
        result = generate_newsletter(GenerateNewsletterRequest(keywords="AI", period=7))

    assert set(result.keys()) == {
        "status",
        "html_content",
        "title",
        "generation_stats",
        "input_params",
        "error",
    }
    assert result["status"] == "success"
    assert result["title"] == "Facade Smoke"
    assert result["html_content"] == html
    assert result["generation_stats"]["total_time"] == 0.2


@pytest.mark.unit
@pytest.mark.mock_api
def test_generation_facade_raises_on_error_status() -> None:
    with patch(
        "newsletter_core.public.generation.graph.generate_newsletter",
        return_value=("backend failed", "error"),
    ), patch(
        "newsletter_core.public.generation.graph.get_last_generation_info",
        return_value={},
    ):
        with pytest.raises(NewsletterGenerationError):
            generate_newsletter(GenerateNewsletterRequest(keywords="AI"))


@pytest.mark.unit
@pytest.mark.mock_api
def test_legacy_newsletter_api_re_exports_public_facade() -> None:
    """Legacy import path is still available with deprecation warning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        from newsletter import api as legacy_api

    assert any(issubclass(w.category, DeprecationWarning) for w in caught)
    assert legacy_api.generate_newsletter is not None
    assert legacy_api.GenerateNewsletterRequest is not None
