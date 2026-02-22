"""Compatibility facade for legacy `newsletter.api` imports."""

from __future__ import annotations

import warnings

from newsletter_core.public.generation import (
    GenerateNewsletterRequest,
    GenerationStats,
    NewsletterGenerationError,
    NewsletterResult,
    generate_newsletter,
)

warnings.warn(
    "newsletter.api is deprecated and will be removed after 2 release cycles. "
    "Use newsletter_core.public.generation instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "GenerateNewsletterRequest",
    "GenerationStats",
    "NewsletterGenerationError",
    "NewsletterResult",
    "generate_newsletter",
]
