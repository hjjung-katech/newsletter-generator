from __future__ import annotations

from newsletter_core.public.source_policies import filter_articles_by_source_policies


def test_source_policy_filtering_blocks_matching_domains() -> None:
    articles = [
        {
            "title": "Keep me",
            "url": "https://www.reuters.com/world/test-story",
            "source": "Reuters",
        },
        {
            "title": "Drop me",
            "url": "https://spam.example/news/story",
            "source": "Spam Example",
        },
    ]

    filtered = filter_articles_by_source_policies(
        articles,
        blocklist=["spam.example"],
    )

    assert [item["title"] for item in filtered] == ["Keep me"]


def test_source_policy_filtering_respects_allowlist() -> None:
    articles = [
        {
            "title": "Allowed",
            "url": "https://www.ft.com/content/test-story",
            "source": "Financial Times",
        },
        {
            "title": "Excluded",
            "url": "https://example.org/post",
            "source": "Example Org",
        },
    ]

    filtered = filter_articles_by_source_policies(
        articles,
        allowlist=["ft.com"],
    )

    assert [item["title"] for item in filtered] == ["Allowed"]
