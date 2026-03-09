from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from db_archive import get_archive_entry, search_archive_entries  # noqa: E402
from db_state import ensure_database_schema  # noqa: E402


def _insert_history_row(
    database_path: str,
    *,
    job_id: str,
    params: dict,
    result: dict,
    created_at: str,
    status: str = "completed",
) -> None:
    ensure_database_schema(database_path)
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO history (id, params, result, created_at, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, json.dumps(params), json.dumps(result), created_at, status),
        )
        conn.commit()
    finally:
        conn.close()


def test_get_archive_entry_syncs_from_history(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    _insert_history_row(
        str(db_path),
        job_id="archive-sync-job",
        params={"keywords": ["battery", "materials"], "period": 7},
        result={
            "title": "Battery Materials Weekly",
            "html_content": "<html><body><p>Battery recycling update.</p></body></html>",
        },
        created_at="2026-03-09T08:00:00Z",
    )

    entry = get_archive_entry(str(db_path), "archive-sync-job")

    assert entry is not None
    assert entry["job_id"] == "archive-sync-job"
    assert entry["keywords"] == ["battery", "materials"]
    assert entry["params"]["period"] == 7
    assert entry["result"]["title"] == "Battery Materials Weekly"


def test_search_archive_entries_filters_search_text(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    _insert_history_row(
        str(db_path),
        job_id="archive-search-battery",
        params={"keywords": ["battery"]},
        result={
            "title": "Battery Outlook",
            "html_content": "<html><body><p>Battery supply chain update.</p></body></html>",
        },
        created_at="2026-03-09T08:00:00Z",
    )
    _insert_history_row(
        str(db_path),
        job_id="archive-search-ai",
        params={"keywords": ["ai"]},
        result={
            "title": "AI Outlook",
            "html_content": "<html><body><p>Inference accelerator roadmap.</p></body></html>",
        },
        created_at="2026-03-09T09:00:00Z",
    )

    results = search_archive_entries(str(db_path), query="battery", limit=10)

    assert [result["job_id"] for result in results] == ["archive-search-battery"]
