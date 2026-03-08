"""Helpers for deriving searchable archive entries and reuse sections."""

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


def render_archive_reference_section(references: List[Dict[str, Any]]) -> str:
    """Render a portable HTML section summarizing selected archive references."""
    if not references:
        return ""

    items_html = "".join(
        f"""
        <li style="margin-bottom: 14px;">
            <div style="font-weight: 600; color: #1f2937;">{html.escape(str(reference.get("title") or reference.get("job_id") or "Archive Reference"))}</div>
            <div style="margin-top: 4px; color: #4b5563; font-size: 14px; line-height: 1.5;">{html.escape(str(reference.get("snippet") or ""))}</div>
            <div style="margin-top: 4px; color: #6b7280; font-size: 12px;">{html.escape(str(reference.get("source_value") or ""))}</div>
        </li>
        """
        for reference in references
    )

    return f"""
    <section style="margin: 28px 0; padding: 20px; border: 1px solid #dbeafe; border-radius: 12px; background: #eff6ff;">
        <h2 style="margin: 0 0 12px 0; color: #1d4ed8; font-size: 20px;">지난 뉴스레터 참고</h2>
        <p style="margin: 0 0 14px 0; color: #1f2937; font-size: 14px; line-height: 1.6;">
            이번 생성에는 아래 과거 뉴스레터를 참고본으로 함께 보관했습니다.
        </p>
        <ul style="margin: 0; padding-left: 20px;">
            {items_html}
        </ul>
    </section>
    """


def inject_archive_references(
    html_content: str,
    references: List[Dict[str, Any]],
) -> str:
    """Inject a reusable archive reference section before the closing body tag."""
    if not html_content or not references:
        return html_content

    reference_section = render_archive_reference_section(references)
    if not reference_section:
        return html_content

    if "</body>" in html_content:
        return html_content.replace("</body>", f"{reference_section}\n</body>", 1)
    return f"{html_content}\n{reference_section}"
