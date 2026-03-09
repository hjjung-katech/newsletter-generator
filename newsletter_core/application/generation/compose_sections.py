"""Article selection and grouped-section helpers for compose."""

from __future__ import annotations

from typing import Any, Dict, List

from newsletter.date_utils import extract_source_and_date, format_date_for_display


def extract_and_prepare_top_articles(
    data: Dict[str, Any], count: int = 3
) -> List[Dict[str, Any]]:
    """Extract top articles and format them for template rendering."""
    if "top_articles" in data and data["top_articles"]:
        top_articles = data["top_articles"][:count]
    elif "sections" in data:
        top_articles = extract_top_articles_from_sections(data["sections"])[:count]
    else:
        top_articles = []

    return prepare_top_articles_for_compact(top_articles)


def create_grouped_sections(
    data: Dict[str, Any],
    top_articles: List[Dict[str, Any]],
    max_groups: int = 6,
    max_articles: int = None,
) -> List[Dict[str, Any]]:
    """Create grouped sections while keeping top articles separate."""
    if "grouped_sections" in data:
        existing_sections = data["grouped_sections"][:max_groups]
        return _hydrate_grouped_section_definitions(existing_sections, data)

    sections = data.get("sections", [])
    if not sections:
        return []

    excluded_urls = {article.get("url", "") for article in top_articles}
    grouped_sections = []
    article_count = 0
    is_compact = max_articles is not None

    for section in sections[:max_groups]:
        news_links = section.get("news_links", [])
        articles = section.get("articles", [])
        article_list = news_links if news_links else articles
        remaining_articles = [
            link for link in article_list if link.get("url", "") not in excluded_urls
        ]

        if max_articles and article_count + len(
            remaining_articles
        ) > max_articles - len(top_articles):
            remaining_articles = remaining_articles[
                : max_articles - len(top_articles) - article_count
            ]

        if not remaining_articles:
            continue

        grouped_sections.append(
            {
                "heading": add_emoji_to_section_title(section.get("title", "기타")),
                "intro": _resolve_grouped_section_intro(section, is_compact),
                "articles": remaining_articles,
                "definitions": section.get("definitions", []),
            }
        )
        article_count += len(remaining_articles)

        if max_articles and article_count >= max_articles - len(top_articles):
            break

    return grouped_sections


def extract_definitions(
    data: Dict[str, Any], grouped_sections: List[Dict[str, Any]], config: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Extract newsletter definitions with compact limits when configured."""
    if "definitions" in data:
        definitions = data["definitions"]
        if config["max_definitions"]:
            return definitions[: config["max_definitions"]]
        return definitions

    sections = data.get("sections", [])
    return extract_key_definitions_for_compact(sections)[
        : config["max_definitions"] or 999
    ]


def extract_food_for_thought(data: Dict[str, Any]) -> Any:
    """Normalize food-for-thought payload into template-friendly form."""
    food_for_thought = data.get("food_for_thought")
    if not food_for_thought:
        return {"message": ""}
    if isinstance(food_for_thought, dict):
        return food_for_thought
    return {"message": str(food_for_thought)}


def extract_top_articles_from_sections(
    sections: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Extract one representative top article per section without duplicate URLs."""
    top_articles = []
    seen_urls = set()

    for section in sections[:3]:
        news_links = section.get("news_links", [])
        if not news_links:
            continue

        for article in news_links:
            article_url = article.get("url", "#")
            if article_url in seen_urls or article_url == "#" or not article_url:
                continue

            summary_paragraphs = section.get("summary_paragraphs", [])
            snippet = summary_paragraphs[0] if summary_paragraphs else ""
            top_articles.append(
                {
                    "title": article.get("title", ""),
                    "url": article_url,
                    "snippet": snippet[:150] + "..." if len(snippet) > 150 else snippet,
                    "source_and_date": article.get("source_and_date", ""),
                }
            )
            seen_urls.add(article_url)
            break

    return top_articles


def prepare_top_articles_for_compact(
    top_articles: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Format top articles for compact/detailed template consumption."""
    prepared_articles = []

    for article in top_articles:
        source_and_date = format_compact_source_date(article.get("source_and_date", ""))
        prepared_articles.append(
            {
                "title": article.get("title", ""),
                "url": article.get("url", "#"),
                "snippet": article.get("snippet", article.get("summary_text", "")),
                "source_and_date": source_and_date,
            }
        )

    return prepared_articles


def prepare_grouped_sections_for_compact(
    sections: List[Dict[str, Any]], exclude_articles: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Convert sections into the compact grouped-section structure."""
    grouped_sections = []
    excluded_urls = {article.get("url", "") for article in exclude_articles}

    for section in sections:
        news_links = section.get("news_links", [])
        articles = section.get("articles", [])
        article_list = news_links if news_links else articles
        remaining_articles = [
            link for link in article_list if link.get("url", "") not in excluded_urls
        ]

        if not remaining_articles:
            continue

        intro = section.get("intro", "")
        if not intro:
            summary_paragraphs = section.get("summary_paragraphs", [])
            if summary_paragraphs:
                first_paragraph = summary_paragraphs[0]
                sentences = first_paragraph.split(". ")
                intro = (
                    sentences[0] + "." if sentences else first_paragraph[:100] + "..."
                )

        grouped_sections.append(
            {
                "heading": add_emoji_to_section_title(section.get("title", "")),
                "intro": intro,
                "articles": [
                    {
                        "title": article.get("title", ""),
                        "url": article.get("url", "#"),
                        "source_and_date": format_compact_source_date(
                            article.get("source_and_date", "")
                        ),
                    }
                    for article in remaining_articles[:4]
                ],
            }
        )

    return grouped_sections


def add_emoji_to_section_title(title: str) -> str:
    """Add a section emoji based on keyword heuristics."""
    title_lower = title.lower()

    if any(word in title_lower for word in ["투자", "펀딩", "자금", "ipo", "상장"]):
        return f"🚀 {title}"
    if any(word in title_lower for word in ["정책", "규제", "법", "윤리"]):
        return f"🏛️ {title}"
    if any(word in title_lower for word in ["연구", "기술", "개발", "특허"]):
        return f"📊 {title}"
    if any(word in title_lower for word in ["시장", "수요", "트렌드", "소비"]):
        return f"🌐 {title}"
    return f"📈 {title}"


def format_compact_source_date(source_and_date: str) -> str:
    """Format source/date pairs for compact display."""
    if not source_and_date:
        return ""

    source, date_str = extract_source_and_date(source_and_date)
    if date_str:
        formatted_date = format_date_for_display(date_str=date_str)
        if formatted_date:
            return f"{source} · {formatted_date}"

    return source_and_date


def extract_key_definitions_for_compact(
    sections: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """Extract at most one definition per section, capped at three."""
    all_definitions = []

    for section in sections:
        definitions = section.get("definitions", [])
        if definitions:
            all_definitions.append(definitions[0])

    return all_definitions[:3]


def _hydrate_grouped_section_definitions(
    existing_sections: List[Dict[str, Any]], data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    for section in existing_sections:
        if "definitions" in section and section["definitions"]:
            continue

        section_title = (
            section.get("heading", "")
            .replace("🚀 ", "")
            .replace("🏛️ ", "")
            .replace("📊 ", "")
            .replace("🌐 ", "")
            .replace("📈 ", "")
        )
        original_section = next(
            (s for s in data.get("sections", []) if s.get("title") == section_title),
            None,
        )
        if original_section and "definitions" in original_section:
            section["definitions"] = original_section["definitions"]
        else:
            section["definitions"] = []

    return existing_sections


def _resolve_grouped_section_intro(section: Dict[str, Any], is_compact: bool) -> str:
    if is_compact:
        intro = section.get("intro", "")
        if not intro:
            intro = f"{section.get('title', '기타')}에 대한 주요 동향입니다."
        return intro

    if section.get("summary_paragraphs"):
        return section.get("summary_paragraphs", [""])[0]
    return ""
