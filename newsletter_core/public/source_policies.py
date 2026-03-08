"""Stable public helpers for source allow/block policy enforcement."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


def normalize_source_pattern(value: str) -> str:
    """Normalize a domain/source pattern for allow/block list matching."""
    normalized = str(value or "").strip().lower()
    normalized = re.sub(r"^https?://", "", normalized)
    normalized = normalized.split("/", 1)[0]
    normalized = re.sub(r"^www\.", "", normalized)
    return normalized


def _article_source_candidates(article: dict[str, Any]) -> set[str]:
    candidates: set[str] = set()

    source = normalize_source_pattern(str(article.get("source", "") or ""))
    if source:
        candidates.add(source)

    url = str(article.get("url", "") or "").strip()
    if url and url != "#":
        try:
            domain = normalize_source_pattern(urlparse(url).netloc or url)
        except ValueError:
            domain = normalize_source_pattern(url)
        if domain:
            candidates.add(domain)

    return candidates


def _matches_source_pattern(candidate: str, pattern: str) -> bool:
    if not candidate or not pattern:
        return False

    if "." in pattern:
        return candidate == pattern or candidate.endswith(f".{pattern}")

    return pattern in candidate


def filter_articles_by_source_policies(
    articles: list[dict[str, Any]],
    allowlist: list[str] | None = None,
    blocklist: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Filter articles according to normalized source allow/block policies."""
    normalized_allowlist = [
        normalize_source_pattern(item) for item in (allowlist or []) if item
    ]
    normalized_blocklist = [
        normalize_source_pattern(item) for item in (blocklist or []) if item
    ]

    if not normalized_allowlist and not normalized_blocklist:
        return articles

    filtered_articles: list[dict[str, Any]] = []

    for article in articles:
        candidates = _article_source_candidates(article)
        blocked = any(
            _matches_source_pattern(candidate, pattern)
            for candidate in candidates
            for pattern in normalized_blocklist
        )
        if blocked:
            continue

        if normalized_allowlist:
            allowed = any(
                _matches_source_pattern(candidate, pattern)
                for candidate in candidates
                for pattern in normalized_allowlist
            )
            if not allowed:
                continue

        filtered_articles.append(article)

    return filtered_articles
