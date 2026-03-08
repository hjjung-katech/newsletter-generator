"""Helpers for deriving searchable archive entries from completed history rows."""

from __future__ import annotations

import html
import re
from typing import Any, Dict, List

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_SNIPPET_LENGTH = 280


def normalize_keywords(raw: Any) -> List[str]:
    """Normalize stored keywords into a clean list of strings."""
    if raw is None:
        return []
    if isinstance(raw, str):
        return [item.strip() for item in raw.split(",") if item.strip()]
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return [str(raw).strip()] if str(raw).strip() else []


def strip_html_text(html_content: str) -> str:
    """Collapse HTML into plain text suitable for indexing and snippets."""
    if not html_content:
        return ""
    without_tags = _HTML_TAG_RE.sub(" ", html_content)
    unescaped = html.unescape(without_tags)
    return _WHITESPACE_RE.sub(" ", unescaped).strip()


def build_archive_entry(
    *,
    job_id: str,
    created_at: str,
    params: Dict[str, Any] | None,
    result: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    """Return a normalized archive entry or None when history is not archivable."""
    parsed_params = params or {}
    parsed_result = result or {}
    html_content = str(parsed_result.get("html_content") or "").strip()
    if not html_content:
        return None

    keywords = normalize_keywords(parsed_params.get("keywords"))
    domain = str(parsed_params.get("domain") or "").strip()
    title = str(parsed_result.get("title") or "").strip()
    if not title:
        title = (
            f"Newsletter: {domain}"
            if domain
            else f"Newsletter: {', '.join(keywords[:3]) or job_id}"
        )

    plain_text = strip_html_text(html_content)
    snippet = plain_text[:_SNIPPET_LENGTH].rstrip()
    if len(plain_text) > _SNIPPET_LENGTH:
        snippet = f"{snippet}..."

    source_kind = "domain" if domain else "keywords"
    source_value = domain or ", ".join(keywords)
    metadata = {
        "domain": domain or None,
        "keywords": keywords,
        "template_style": parsed_params.get("template_style"),
        "period": parsed_params.get("period"),
        "email_compatible": bool(parsed_params.get("email_compatible", False)),
        "approval_status": parsed_result.get("approval_status"),
        "delivery_status": parsed_result.get("delivery_status"),
    }
    search_text = "\n".join(
        segment
        for segment in (
            title,
            source_value,
            plain_text,
            str(parsed_params.get("template_style") or "").strip(),
        )
        if segment
    )

    return {
        "job_id": job_id,
        "title": title,
        "snippet": snippet or title,
        "source_kind": source_kind,
        "source_value": source_value,
        "keywords": keywords,
        "metadata": metadata,
        "search_text": search_text,
        "created_at": created_at,
        "updated_at": created_at,
    }
