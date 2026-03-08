from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from db_state import ensure_database_schema  # noqa: E402
from tasks import generate_newsletter_task  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


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


def test_generate_newsletter_task_appends_selected_archive_references(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = str(tmp_path / "storage.db")
    archive_job_id = "archive-source-job"
    _insert_history_row(
        database_path,
        job_id=archive_job_id,
        params={"keywords": ["battery"], "template_style": "compact"},
        result={
            "title": "Battery Materials Weekly",
            "html_content": "<html><body><p>Legacy battery supply chain summary.</p></body></html>",
        },
        created_at="2026-03-08T08:00:00Z",
    )

    monkeypatch.setattr(
        "tasks.generate_newsletter",
        lambda request: {
            "status": "success",
            "html_content": "<html><body><h1>Fresh Newsletter</h1><p>New market update.</p></body></html>",
            "title": "Fresh Newsletter",
            "generation_stats": {},
            "input_params": {"keywords": request.keywords},
            "error": None,
        },
    )

    result = generate_newsletter_task(
        {
            "keywords": ["battery", "materials"],
            "archive_reference_ids": [archive_job_id],
        },
        "job-with-archive-reference",
        database_path=database_path,
    )

    assert result["status"] == "success"
    assert result["archive_references"] == [
        {
            "job_id": archive_job_id,
            "title": "Battery Materials Weekly",
            "snippet": "Legacy battery supply chain summary.",
            "source_value": "battery",
            "created_at": "2026-03-08T08:00:00Z",
        }
    ]
    assert result["input_params"]["archive_reference_ids"] == [archive_job_id]
    assert "지난 뉴스레터 참고" in result["html_content"]
    assert "Battery Materials Weekly" in result["html_content"]
